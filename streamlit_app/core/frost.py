"""Frost depth, adfreeze uplift, and embedment check (IBC 1809.5)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .soil import SoilProfile, AxialSoilZone


# Regional frost depth lookup — approximate US ranges (inches)
FROST_DEPTH_TABLE: dict[str, tuple[float, float]] = {
    "Southern states": (0.0, 12.0),
    "Mid-Atlantic": (24.0, 36.0),
    "Midwest": (36.0, 48.0),
    "Northern states": (48.0, 72.0),
    "Alaska": (72.0, 120.0),
}

# Stefan equation C coefficient by soil type
STEFAN_C: dict[str, float] = {
    "Clay": 0.75,
    "Silt": 0.90,
    "Sand": 1.05,
    "Gravel": 1.15,
}


@dataclass
class FrostCheckResult:
    """Frost depth check results."""

    frost_depth_in: float
    frost_depth_ft: float
    min_embedment_ft: float      # frost depth + 12 in (IBC 1809.5)
    actual_embedment_ft: float
    passes: bool
    margin_ft: float             # actual - required (positive = safe)
    method: str                  # "Regional lookup" | "Stefan equation" | "Manual"
    region: str = ""
    adfreeze_force_lbs: float | None = None
    adfreeze_source: str = ""    # "tau_af manual" | "f_s_uplift (profile)" | "f_s_uplift (axial zones)"
    notes: list[str] = field(default_factory=list)


@dataclass
class AdfreezeServiceCheck:
    """Service-level adfreeze uplift check.

    Mirrors the spreadsheet-style check:
        skin_friction_below_frost + dead_load_per_pile - adfreeze_uplift >= 0

    Uses service-level loads (no LRFD/ASD factors) per industry practice
    for frost-heave checks. The LRFD load case LC8 (0.9D + A_f) is a
    separate, stricter check that factors both sides.
    """
    adfreeze_force_lbs: float
    skin_resistance_below_frost_lbs: float
    dead_load_per_pile_lbs: float
    total_resistance_lbs: float  # skin + dead
    margin_lbs: float            # total_resistance - adfreeze_force (positive = safe)
    passes: bool
    frost_depth_ft: float
    resistance_depth_ft: float   # embedment - frost_depth
    notes: list[str] = field(default_factory=list)


def frost_depth_regional(region: str) -> float:
    """Return typical frost depth (inches) for a US region (midpoint of range)."""
    if region in FROST_DEPTH_TABLE:
        lo, hi = FROST_DEPTH_TABLE[region]
        return (lo + hi) / 2.0
    return 36.0  # conservative default


def frost_depth_stefan(
    freezing_index_deg_days: float,
    soil_type: str = "Sand",
) -> float:
    """Stefan equation frost penetration depth (inches).

    d_f = C * sqrt(F_I)

    Args:
        freezing_index_deg_days: Cumulative freezing index (degree-days F).
        soil_type: One of Clay, Silt, Sand, Gravel.

    Returns:
        Frost depth in inches.
    """
    C = STEFAN_C.get(soil_type, 1.0)
    return C * math.sqrt(max(freezing_index_deg_days, 0))


def adfreeze_from_profile(
    profile,
    pile_perimeter_in: float,
    frost_depth_ft: float,
    axial_zones=None,
    dz: float = 0.5,
) -> tuple[float, str, list[str]]:
    """Compute adfreeze uplift force by integrating f_s_uplift over the frost depth.

    Uses the geotech-stated uplift skin friction values from the soil profile
    (per-layer ``f_s_uplift``) or explicit axial zones (``f_s_uplift_psf``) that
    cover the frost zone. This matches the industry approach: the adfreeze
    bond in the frost zone IS the uplift skin friction for that soil-pile
    interface, just in a frozen state.

    Args:
        profile: SoilProfile object (for fallback layer lookup).
        pile_perimeter_in: Pile perimeter (in).
        frost_depth_ft: Frost depth (ft).
        axial_zones: Optional list of AxialSoilZone objects — preferred if present.
        dz: Depth increment for integration (ft).

    Returns:
        (force_lbs, source_label, notes). If no f_s_uplift values are
        available within the frost depth, returns (0.0, "no data", notes).
    """
    notes: list[str] = []
    if pile_perimeter_in <= 0 or frost_depth_ft <= 0:
        return 0.0, "no data", ["Missing perimeter or frost depth"]

    # Integrate from 0 to frost_depth_ft using dz steps (midpoint rule)
    n_steps = max(1, int(math.ceil(frost_depth_ft / dz)))
    step = frost_depth_ft / n_steps
    A_s_per_step = pile_perimeter_in * step * 12.0  # in^2 per step

    force_lbs = 0.0
    used_zones = False
    used_layers = False
    missing_depths: list[float] = []

    for i in range(n_steps):
        z = (i + 0.5) * step
        f_s_up_psf: float | None = None

        # 1) Axial zone first (if present and covers this depth)
        if axial_zones:
            for zone in axial_zones:
                if zone.top_depth_ft <= z < zone.bottom_depth_ft:
                    if zone.f_s_uplift_psf > 0:
                        f_s_up_psf = zone.f_s_uplift_psf
                        used_zones = True
                    elif zone.f_s_comp_psf > 0:
                        f_s_up_psf = zone.f_s_comp_psf
                        used_zones = True
                    break

        # 2) Fallback to SoilLayer explicit f_s_uplift
        if f_s_up_psf is None and profile is not None:
            layer = profile.layer_at_depth(z)
            if layer is not None and layer.f_s_uplift is not None:
                f_s_up_psf = layer.f_s_uplift
                used_layers = True
            elif layer is not None and layer.f_s_downward is not None:
                f_s_up_psf = layer.f_s_downward
                used_layers = True

        if f_s_up_psf is None:
            missing_depths.append(round(z, 2))
            continue

        dQ = (f_s_up_psf / 144.0) * A_s_per_step  # psi * in^2 = lbs
        force_lbs += dQ

    source = "no data"
    if used_zones and used_layers:
        source = "f_s_uplift (zones + layers)"
    elif used_zones:
        source = "f_s_uplift (axial zones)"
    elif used_layers:
        source = "f_s_uplift (profile layers)"

    notes.append(
        f"Adfreeze integrated from geotech f_s_uplift over "
        f"{frost_depth_ft:.2f} ft frost depth = {force_lbs:,.0f} lbs"
    )
    if missing_depths:
        notes.append(
            f"Missing f_s_uplift at depths (ft): {missing_depths} — "
            f"those intervals contributed zero. Provide explicit uplift "
            f"values on the Soil Profile page to avoid under-estimating adfreeze."
        )

    return force_lbs, source, notes


def adfreeze_service_check(
    adfreeze_force_lbs: float,
    skin_resistance_below_frost_lbs: float,
    dead_load_per_pile_lbs: float,
    frost_depth_ft: float,
    embedment_ft: float,
) -> AdfreezeServiceCheck:
    """Service-level adfreeze uplift check (matches industry spreadsheet practice).

    Verifies:  skin_below_frost + D_per_pile - adfreeze >= 0

    No load factors applied — this is a direct service-level check per the
    FHWA / Canadian Foundation Engineering Manual approach for frost-heave.
    A separate LRFD check (LC8: 0.9D + A_f) runs in the load-combination
    framework.

    Args:
        adfreeze_force_lbs: Adfreeze uplift demand (lbs).
        skin_resistance_below_frost_lbs: Skin friction integrated from
            frost_depth to embedment (lbs, uplift direction).
        dead_load_per_pile_lbs: Dead load per pile at service level (lbs).
        frost_depth_ft: Frost depth (ft), for reporting.
        embedment_ft: Pile embedment (ft), for reporting.

    Returns:
        AdfreezeServiceCheck with margin and pass/fail.
    """
    total_resistance = skin_resistance_below_frost_lbs + dead_load_per_pile_lbs
    margin = total_resistance - adfreeze_force_lbs
    resistance_depth = max(0.0, embedment_ft - frost_depth_ft)

    notes = [
        f"Adfreeze demand: {adfreeze_force_lbs:,.0f} lbs",
        f"Skin friction below frost ({resistance_depth:.1f} ft): "
        f"{skin_resistance_below_frost_lbs:,.0f} lbs",
        f"Dead load per pile: {dead_load_per_pile_lbs:,.0f} lbs",
        f"Total resistance: {total_resistance:,.0f} lbs",
        f"Margin: {margin:+,.0f} lbs ({'PASS' if margin >= 0 else 'FAIL'})",
    ]
    if margin < 0:
        notes.append(
            "Mitigations: increase embedment, upsize pile section, add a "
            "frost sleeve, or increase reveal to reduce frost penetration."
        )

    return AdfreezeServiceCheck(
        adfreeze_force_lbs=adfreeze_force_lbs,
        skin_resistance_below_frost_lbs=skin_resistance_below_frost_lbs,
        dead_load_per_pile_lbs=dead_load_per_pile_lbs,
        total_resistance_lbs=total_resistance,
        margin_lbs=margin,
        passes=margin >= 0,
        frost_depth_ft=frost_depth_ft,
        resistance_depth_ft=resistance_depth,
        notes=notes,
    )


def frost_check(
    frost_depth_in: float,
    embedment_ft: float,
    pile_perimeter_in: float = 0.0,
    tau_af_psi: float = 10.0,
    method: str = "",
    region: str = "",
    adfreeze_force_override_lbs: float | None = None,
    adfreeze_source_override: str = "",
) -> FrostCheckResult:
    """Check embedment against frost depth and compute adfreeze forces.

    IBC 1809.5 requires embedment >= frost depth + 12 inches.

    Args:
        frost_depth_in: Design frost depth (in).
        embedment_ft: Actual pile embedment below ground (ft).
        pile_perimeter_in: Pile perimeter (in) for adfreeze calculation.
        tau_af_psi: Adfreeze bond strength (psi), typical 5-15 for steel.
        method: Method used to determine frost depth.
        region: US region (if regional lookup).

    Returns:
        FrostCheckResult with pass/fail and adfreeze force.
    """
    frost_ft = frost_depth_in / 12.0
    required_ft = frost_ft + 1.0  # 12 inches = 1 ft below frost line
    margin = embedment_ft - required_ft
    passes = margin >= 0

    notes: list[str] = []
    notes.append(f"Frost depth = {frost_depth_in:.0f} in ({frost_ft:.1f} ft)")
    notes.append(f"Min embedment per IBC 1809.5 = frost + 12 in = {required_ft:.1f} ft")

    # Adfreeze uplift force
    adfreeze: float | None = None
    adfreeze_source = ""
    if adfreeze_force_override_lbs is not None:
        # Caller provided a pre-computed adfreeze (typically from profile f_s_uplift)
        adfreeze = adfreeze_force_override_lbs
        adfreeze_source = adfreeze_source_override or "override"
        notes.append(f"Adfreeze uplift ({adfreeze_source}) = {adfreeze:,.0f} lbs")
    elif pile_perimeter_in > 0 and frost_depth_in > 0:
        A_s_frost = pile_perimeter_in * frost_depth_in  # in^2
        adfreeze = tau_af_psi * A_s_frost  # lbs
        adfreeze_source = "tau_af manual"
        notes.append(
            f"Adfreeze uplift = {tau_af_psi} psi x {A_s_frost:.0f} in^2 "
            f"= {adfreeze:,.0f} lbs"
        )

    return FrostCheckResult(
        frost_depth_in=frost_depth_in,
        frost_depth_ft=frost_ft,
        min_embedment_ft=required_ft,
        actual_embedment_ft=embedment_ft,
        passes=passes,
        margin_ft=margin,
        method=method,
        region=region,
        adfreeze_force_lbs=adfreeze,
        adfreeze_source=adfreeze_source,
        notes=notes,
    )
