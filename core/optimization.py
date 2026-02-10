"""Pile design optimization: sweep sections x embedments against load cases.

Evaluates all combinations of section size (within a family) and embedment
depth. Each combination is checked for axial compression, axial tension,
lateral structural DCR, and ground-line deflection against the governing
load cases. Results include a pass/fail matrix and the lightest passing design.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .soil import SoilProfile
from .sections import SteelSection, get_sections_by_family, corroded_section
from .axial import axial_capacity
from .lateral import solve_lateral
from .loads import LoadCase


@dataclass
class OptimizationCandidate:
    """Result for a single (section, embedment) combination."""
    section_name: str
    embedment_ft: float
    total_weight_lbs: float       # weight_plf * embedment_ft

    # DCR values (demand / capacity; <= 1.0 is passing)
    axial_comp_dcr: float
    axial_tens_dcr: float
    lateral_struct_dcr: float
    deflection_in: float
    deflection_limit_in: float

    # Individual pass/fail
    passes_axial_comp: bool
    passes_axial_tens: bool
    passes_lateral_struct: bool
    passes_deflection: bool
    passes_all: bool

    # Governing load case names
    governing_comp_case: str
    governing_tens_case: str
    governing_lateral_case: str

    lateral_converged: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """Complete optimization sweep result."""
    candidates: list[OptimizationCandidate]
    section_family: str
    section_names: list[str]
    embedment_range: tuple[float, float, float]  # (min, max, step)
    optimal: OptimizationCandidate | None
    total_combinations: int
    passing_count: int
    sweep_time_seconds: float
    notes: list[str] = field(default_factory=list)


def _get_max_demands(
    load_cases: list[LoadCase],
) -> tuple[float, str, float, str]:
    """Extract max compression and tension demands across all load cases.

    Returns:
        (max_V_comp, comp_case_name, max_V_tens, tens_case_name)
    """
    max_comp = 0.0
    comp_case = ""
    max_tens = 0.0
    tens_case = ""
    for lc in load_cases:
        if lc.V_comp > max_comp:
            max_comp = lc.V_comp
            comp_case = lc.name
        if lc.V_tens > max_tens:
            max_tens = lc.V_tens
            tens_case = lc.name
    return max_comp, comp_case, max_tens, tens_case


def _get_governing_lateral_case(load_cases: list[LoadCase]) -> LoadCase:
    """Select the load case with the largest lateral demand.

    Uses max H_lat; ties broken by max M_ground.
    """
    return max(load_cases, key=lambda lc: (abs(lc.H_lat), abs(lc.M_ground)))


def _frange(start: float, stop: float, step: float) -> list[float]:
    """Generate a list of floats from start to stop (inclusive) by step."""
    vals = []
    v = start
    while v <= stop + step * 0.01:
        vals.append(round(v, 4))
        v += step
    return vals


def run_optimization_sweep(
    profile: SoilProfile,
    section_family: str,
    embedment_range: tuple[float, float, float],
    load_cases: list[LoadCase],
    pile_type: str = "driven",
    head_condition: str = "free",
    bending_axis: str = "strong",
    cyclic: bool = False,
    axial_method: str = "auto",
    FS_compression: float = 2.5,
    FS_tension: float = 3.0,
    deflection_limit: float = 1.0,
    design_method: str = "LRFD",
    corrosion_t_loss: float = 0.0,
    n_elements: int = 50,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> OptimizationResult:
    """Sweep all sections in a family across embedment depths.

    For each (section, embedment) combination, runs axial and lateral
    analyses and checks pass/fail against governing load cases.

    Args:
        profile: Soil profile with layers and water table.
        section_family: Family prefix ("W6", "W8", "C4", "All W-shapes", "All").
        embedment_range: (min_ft, max_ft, step_ft).
        load_cases: List of factored LoadCase objects (LRFD or ASD).
        pile_type: "driven", "drilled", or "helical".
        head_condition: "free" or "fixed".
        bending_axis: "strong" or "weak".
        cyclic: Cyclic loading flag for p-y curves.
        axial_method: "auto", "alpha", "beta", or "meyerhof".
        FS_compression: ASD factor of safety for compression.
        FS_tension: ASD factor of safety for tension.
        deflection_limit: Max allowable ground-line deflection (in).
        design_method: "LRFD" or "ASD".
        corrosion_t_loss: Thickness loss per side (in), 0 = no corrosion.
        n_elements: FDM mesh elements (50 for speed, 100 for accuracy).
        progress_callback: Called with (current_index, total, section_name).

    Returns:
        OptimizationResult with all candidates and the optimal design.
    """
    t_start = time.time()

    sections = get_sections_by_family(section_family)
    if not sections:
        return OptimizationResult(
            candidates=[], section_family=section_family,
            section_names=[], embedment_range=embedment_range,
            optimal=None, total_combinations=0, passing_count=0,
            sweep_time_seconds=0.0,
            notes=[f"No sections found for family '{section_family}'."],
        )

    embed_min, embed_max, embed_step = embedment_range
    embedments = _frange(embed_min, embed_max, embed_step)
    section_names = [s.name for s in sections]
    total = len(sections) * len(embedments)

    # Pre-compute governing demands from load cases
    max_V_comp, comp_case, max_V_tens, tens_case = _get_max_demands(load_cases)
    gov_lat = _get_governing_lateral_case(load_cases)

    candidates: list[OptimizationCandidate] = []
    idx = 0

    for sec in sections:
        # Apply corrosion if needed
        active_sec = sec
        if corrosion_t_loss > 0:
            try:
                active_sec = corroded_section(sec, corrosion_t_loss)
            except ValueError:
                # Section fully consumed by corrosion — mark all embedments as failing
                for emb in embedments:
                    idx += 1
                    if progress_callback:
                        progress_callback(idx, total, sec.name)
                    candidates.append(OptimizationCandidate(
                        section_name=sec.name, embedment_ft=emb,
                        total_weight_lbs=sec.weight * emb,
                        axial_comp_dcr=999.0, axial_tens_dcr=999.0,
                        lateral_struct_dcr=999.0, deflection_in=999.0,
                        deflection_limit_in=deflection_limit,
                        passes_axial_comp=False, passes_axial_tens=False,
                        passes_lateral_struct=False, passes_deflection=False,
                        passes_all=False,
                        governing_comp_case=comp_case,
                        governing_tens_case=tens_case,
                        governing_lateral_case=gov_lat.name,
                        lateral_converged=False,
                        notes=["Section consumed by corrosion"],
                    ))
                continue

        # Section properties for lateral analysis
        if bending_axis == "strong":
            EI = active_sec.EI_strong
            My_kip_in = active_sec.My_strong
        else:
            EI = active_sec.EI_weak
            My_kip_in = active_sec.My_weak
        My_ft_lbs = My_kip_in * 1000.0 / 12.0  # kip-in -> ft-lbs

        B = active_sec.width  # pile width for lateral p-y (in)

        for emb in embedments:
            idx += 1
            if progress_callback:
                progress_callback(idx, total, sec.name)

            notes: list[str] = []
            total_weight = active_sec.weight * emb

            # --- Axial analysis ---
            try:
                ax = axial_capacity(
                    profile=profile,
                    pile_perimeter=active_sec.perimeter,
                    pile_tip_area=active_sec.tip_area,
                    embedment_depth=emb,
                    method=axial_method,
                    pile_type=pile_type,
                    FS_compression=FS_compression,
                    FS_tension=FS_tension,
                )
                if design_method == "LRFD":
                    cap_comp = ax.Q_r_compression
                    cap_tens = ax.Q_r_tension
                else:
                    cap_comp = ax.Q_allow_compression
                    cap_tens = ax.Q_allow_tension

                comp_dcr = max_V_comp / cap_comp if cap_comp > 0 else 999.0
                tens_dcr = max_V_tens / cap_tens if cap_tens > 0 else (
                    0.0 if max_V_tens == 0 else 999.0
                )
            except Exception as e:
                notes.append(f"Axial error: {e}")
                comp_dcr = 999.0
                tens_dcr = 999.0

            # --- Lateral analysis ---
            lat_dcr = 999.0
            defl = 999.0
            lat_converged = False
            try:
                lat = solve_lateral(
                    profile=profile,
                    pile_width=B,
                    EI=EI,
                    embedment=emb,
                    H=gov_lat.H_lat,
                    M_ground=gov_lat.M_ground,
                    head_condition=head_condition,
                    cyclic=cyclic,
                    n_elements=n_elements,
                )
                lat_converged = lat.converged
                defl = abs(lat.y_ground)
                lat_dcr = abs(lat.M_max) / My_ft_lbs if My_ft_lbs > 0 else 999.0
                if not lat.converged:
                    notes.append("Lateral solver did not converge")
            except Exception as e:
                notes.append(f"Lateral error: {e}")

            # --- Pass/fail ---
            p_comp = comp_dcr <= 1.0
            p_tens = tens_dcr <= 1.0
            p_lat = lat_dcr <= 1.0 and lat_converged
            p_defl = defl <= deflection_limit
            p_all = p_comp and p_tens and p_lat and p_defl

            candidates.append(OptimizationCandidate(
                section_name=sec.name,
                embedment_ft=emb,
                total_weight_lbs=total_weight,
                axial_comp_dcr=comp_dcr,
                axial_tens_dcr=tens_dcr,
                lateral_struct_dcr=lat_dcr,
                deflection_in=defl,
                deflection_limit_in=deflection_limit,
                passes_axial_comp=p_comp,
                passes_axial_tens=p_tens,
                passes_lateral_struct=p_lat,
                passes_deflection=p_defl,
                passes_all=p_all,
                governing_comp_case=comp_case,
                governing_tens_case=tens_case,
                governing_lateral_case=gov_lat.name,
                lateral_converged=lat_converged,
                notes=notes,
            ))

    # Find optimal (lightest passing, then shallowest embedment)
    passing = [c for c in candidates if c.passes_all]
    optimal = None
    if passing:
        optimal = min(passing, key=lambda c: (c.total_weight_lbs, c.embedment_ft))

    elapsed = time.time() - t_start

    return OptimizationResult(
        candidates=candidates,
        section_family=section_family,
        section_names=section_names,
        embedment_range=embedment_range,
        optimal=optimal,
        total_combinations=total,
        passing_count=len(passing),
        sweep_time_seconds=elapsed,
    )
