"""Liquefaction screening: SPT-based simplified procedure (Boulanger & Idriss 2014)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .soil import SoilProfile, SoilLayer, SoilType, correct_N_overburden


@dataclass
class LiquefactionLayerResult:
    """Screening result for a single evaluation point."""

    depth_ft: float
    layer_description: str
    soil_type: str
    N_spt: float
    N1_60: float
    N1_60cs: float
    sigma_v_psf: float
    sigma_v_eff_psf: float
    r_d: float
    CSR: float
    CRR: float
    FS_liq: float
    susceptible: bool
    status: str  # "Liquefiable", "Marginal", "Non-liquefiable", "N/A (cohesive)"


@dataclass
class LiquefactionResult:
    """Complete liquefaction screening results."""

    a_max_g: float
    M_w: float
    MSF: float
    layer_results: list[LiquefactionLayerResult] = field(default_factory=list)
    any_liquefiable: bool = False
    summary: str = ""
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Component functions
# ---------------------------------------------------------------------------

def stress_reduction_factor(depth_ft: float) -> float:
    """Depth-dependent stress reduction factor r_d (Boulanger & Idriss)."""
    z_m = depth_ft * 0.3048
    if z_m <= 9.15:
        return 1.0 - 0.00765 * z_m
    elif z_m <= 23.0:
        return 1.174 - 0.0267 * z_m
    else:
        return max(0.5, 0.744 - 0.008 * z_m)


def magnitude_scaling_factor(M_w: float) -> float:
    """MSF per Boulanger & Idriss 2014, capped at 2.0."""
    if M_w <= 0:
        return 2.0
    return min(10**2.24 / M_w**2.56, 2.0)


def clean_sand_correction(N1_60: float, fines_content: float) -> float:
    """Compute (N1)_60cs from (N1)_60 and fines content (%)."""
    if fines_content <= 5.0:
        return N1_60
    FC = max(fines_content, 0.01)
    delta_N = math.exp(1.63 + 9.7 / (FC + 0.01) - (15.7 / (FC + 0.01)) ** 2)
    return N1_60 + delta_N


def crr_boulanger_idriss(N1_60cs: float) -> float:
    """CRR_7.5 from Boulanger & Idriss (2014) SPT correlation."""
    n = min(max(N1_60cs, 0.0), 46.0)  # cap to avoid numerical overflow
    exponent = (
        n / 14.1
        + (n / 126.0) ** 2
        - (n / 23.6) ** 3
        + (n / 25.4) ** 4
        - 2.8
    )
    return math.exp(exponent)


# ---------------------------------------------------------------------------
# Main screening function
# ---------------------------------------------------------------------------

def liquefaction_screening(
    profile: SoilProfile,
    a_max_g: float,
    M_w: float = 7.5,
    fines_content_default: float = 15.0,
    max_depth_ft: float = 65.0,
) -> LiquefactionResult:
    """Screen each soil layer for liquefaction potential.

    Evaluates at the mid-depth of each layer. Cohesive layers are skipped
    (reported as N/A).

    Args:
        profile: SoilProfile with layers and water table.
        a_max_g: Peak ground acceleration (g). Approximate as SDS / 2.5.
        M_w: Earthquake moment magnitude (default 7.5).
        fines_content_default: Default fines content (%) when unknown.
        max_depth_ft: Maximum screening depth (ft).

    Returns:
        LiquefactionResult with per-layer factors of safety.
    """
    MSF = magnitude_scaling_factor(M_w)
    notes: list[str] = [
        f"Method: Boulanger & Idriss (2014) SPT-based simplified procedure",
        f"PGA = {a_max_g:.3f}g, M_w = {M_w:.1f}, MSF = {MSF:.2f}",
    ]

    wt = profile.water_table_depth
    if wt is None:
        notes.append("No water table defined — assuming dry (no liquefaction below WT)")
        return LiquefactionResult(
            a_max_g=a_max_g, M_w=M_w, MSF=MSF,
            summary="No water table defined. Liquefaction requires saturated conditions.",
            notes=notes,
        )

    layer_results: list[LiquefactionLayerResult] = []

    for layer in profile.layers:
        depth = layer.mid_depth
        if depth > max_depth_ft:
            continue

        # Skip cohesive layers
        is_cohesive = layer.soil_type in (SoilType.CLAY, SoilType.ORGANIC)
        if is_cohesive:
            layer_results.append(LiquefactionLayerResult(
                depth_ft=depth,
                layer_description=layer.description or layer.soil_type.value,
                soil_type=layer.soil_type.value,
                N_spt=layer.N_spt or 0,
                N1_60=0, N1_60cs=0,
                sigma_v_psf=0, sigma_v_eff_psf=0,
                r_d=0, CSR=0, CRR=0, FS_liq=0,
                susceptible=False,
                status="N/A (cohesive)",
            ))
            continue

        # Must be below water table to liquefy
        if depth < wt:
            layer_results.append(LiquefactionLayerResult(
                depth_ft=depth,
                layer_description=layer.description or layer.soil_type.value,
                soil_type=layer.soil_type.value,
                N_spt=layer.N_spt or 0,
                N1_60=0, N1_60cs=0,
                sigma_v_psf=0, sigma_v_eff_psf=0,
                r_d=0, CSR=0, CRR=0, FS_liq=0,
                susceptible=False,
                status="Above water table",
            ))
            continue

        # Need SPT data
        N_60 = layer.N_60
        if N_60 is None or N_60 <= 0:
            layer_results.append(LiquefactionLayerResult(
                depth_ft=depth,
                layer_description=layer.description or layer.soil_type.value,
                soil_type=layer.soil_type.value,
                N_spt=layer.N_spt or 0,
                N1_60=0, N1_60cs=0,
                sigma_v_psf=0, sigma_v_eff_psf=0,
                r_d=0, CSR=0, CRR=0, FS_liq=0,
                susceptible=False,
                status="No SPT data",
            ))
            continue

        # Stresses
        sigma_v = profile.total_stress_at(depth)
        sigma_v_eff = profile.effective_stress_at(depth)
        if sigma_v_eff <= 0:
            sigma_v_eff = 1.0  # avoid division by zero

        # Corrected N-value
        N1_60 = correct_N_overburden(N_60, sigma_v_eff)

        # Clean sand correction
        N1_60cs = clean_sand_correction(N1_60, fines_content_default)

        # CSR
        r_d = stress_reduction_factor(depth)
        CSR = 0.65 * (sigma_v / sigma_v_eff) * a_max_g * r_d / MSF

        # CRR
        CRR = crr_boulanger_idriss(N1_60cs)

        # Factor of safety
        FS_liq = CRR / CSR if CSR > 0 else 999.0

        if FS_liq < 1.0:
            status = "Liquefiable"
            susceptible = True
        elif FS_liq < 1.3:
            status = "Marginal"
            susceptible = False
        else:
            status = "Non-liquefiable"
            susceptible = False

        layer_results.append(LiquefactionLayerResult(
            depth_ft=depth,
            layer_description=layer.description or layer.soil_type.value,
            soil_type=layer.soil_type.value,
            N_spt=layer.N_spt or 0,
            N1_60=round(N1_60, 1),
            N1_60cs=round(N1_60cs, 1),
            sigma_v_psf=round(sigma_v, 0),
            sigma_v_eff_psf=round(sigma_v_eff, 0),
            r_d=round(r_d, 3),
            CSR=round(CSR, 3),
            CRR=round(CRR, 3),
            FS_liq=round(FS_liq, 2),
            susceptible=susceptible,
            status=status,
        ))

    any_liq = any(lr.susceptible for lr in layer_results)
    n_liq = sum(1 for lr in layer_results if lr.susceptible)
    n_marginal = sum(1 for lr in layer_results if lr.status == "Marginal")
    n_total = len(layer_results)

    if any_liq:
        summary = f"LIQUEFIABLE: {n_liq} of {n_total} layers have FS < 1.0"
    elif n_marginal > 0:
        summary = f"MARGINAL: {n_marginal} of {n_total} layers have FS between 1.0 and 1.3"
    else:
        summary = f"NON-LIQUEFIABLE: All {n_total} layers have FS >= 1.3"

    return LiquefactionResult(
        a_max_g=a_max_g,
        M_w=M_w,
        MSF=MSF,
        layer_results=layer_results,
        any_liquefiable=any_liq,
        summary=summary,
        notes=notes,
    )
