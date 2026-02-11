"""Frost depth calculation and embedment check (IBC 1809.5)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


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


def frost_check(
    frost_depth_in: float,
    embedment_ft: float,
    pile_perimeter_in: float = 0.0,
    tau_af_psi: float = 10.0,
    method: str = "",
    region: str = "",
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
    adfreeze = None
    if pile_perimeter_in > 0 and frost_depth_in > 0:
        A_s_frost = pile_perimeter_in * frost_depth_in  # in^2
        adfreeze = tau_af_psi * A_s_frost  # lbs
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
        notes=notes,
    )
