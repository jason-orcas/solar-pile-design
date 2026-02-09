"""Pile group efficiency, p-multipliers, and block failure analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .soil import SoilProfile, SoilType


@dataclass
class GroupResult:
    """Results from a pile group analysis."""
    n_piles: int
    n_rows: int
    n_cols: int
    spacing: float          # center-to-center (in)
    s_over_d: float         # spacing / pile width ratio

    # Axial
    eta_axial: float        # Converse-Labarre efficiency
    Q_group_individual: float  # eta * n * Q_single (lbs)
    Q_block: float | None   # Block failure capacity (lbs)
    Q_group_governing: float  # min of individual and block

    # Lateral
    p_multipliers: list[dict]  # Per-row multipliers
    eta_lateral: float       # Average lateral group efficiency

    method: str
    notes: list[str]


def converse_labarre(
    n_rows: int,
    n_cols: int,
    pile_width: float,
    spacing: float,
) -> float:
    """Converse-Labarre group efficiency factor.

    Args:
        n_rows: Number of rows
        n_cols: Number of columns (piles per row)
        pile_width: Pile width or diameter (in)
        spacing: Center-to-center spacing (in)

    Returns:
        Efficiency factor eta (0 to 1)
    """
    if spacing <= 0 or n_rows <= 0 or n_cols <= 0:
        return 1.0
    theta = math.degrees(math.atan(pile_width / spacing))
    n1 = n_cols
    n2 = n_rows
    numerator = theta * ((n1 - 1) * n2 + (n2 - 1) * n1)
    denominator = 90.0 * n1 * n2
    eta = 1.0 - numerator / denominator
    return max(0.0, min(1.0, eta))


def p_multipliers_table(
    n_rows: int,
    s_over_d: float,
) -> list[dict]:
    """Get p-multipliers for each row in a lateral pile group.

    Based on AASHTO/FHWA (Brown et al., NCHRP 461).

    Returns:
        List of dicts with row_number, position, and f_m.
    """
    # Interpolation table: s/d -> [lead, 2nd, 3rd, 4th+]
    table = {
        3.0: [0.80, 0.40, 0.30, 0.30],
        4.0: [0.85, 0.55, 0.45, 0.40],
        5.0: [0.90, 0.65, 0.55, 0.50],
        6.0: [0.95, 0.75, 0.65, 0.60],
        8.0: [1.00, 1.00, 1.00, 1.00],
    }

    # Interpolate
    sd = max(3.0, min(8.0, s_over_d))
    keys = sorted(table.keys())

    if sd >= 8.0:
        multipliers = [1.0, 1.0, 1.0, 1.0]
    else:
        # Find bounding keys
        for i in range(len(keys) - 1):
            if keys[i] <= sd <= keys[i + 1]:
                f = (sd - keys[i]) / (keys[i + 1] - keys[i])
                low = table[keys[i]]
                high = table[keys[i + 1]]
                multipliers = [low[j] + f * (high[j] - low[j]) for j in range(4)]
                break
        else:
            multipliers = table[3.0]

    results = []
    for row in range(1, n_rows + 1):
        if row == 1:
            pos = "Lead (front)"
            fm = multipliers[0]
        elif row == 2:
            pos = "2nd row"
            fm = multipliers[1]
        elif row == 3:
            pos = "3rd row"
            fm = multipliers[2]
        else:
            pos = f"{row}th row"
            fm = multipliers[3]
        results.append({
            "row": row,
            "position": pos,
            "f_m": round(fm, 3),
        })

    return results


def block_failure_cohesive(
    n_rows: int,
    n_cols: int,
    spacing: float,
    pile_width: float,
    embedment: float,
    c_u_avg: float,
    c_u_base: float,
) -> float:
    """Block failure capacity for pile group in cohesive soil.

    Args:
        n_rows, n_cols: Group layout
        spacing: Center-to-center (in)
        pile_width: Pile width (in)
        embedment: Embedded depth (ft)
        c_u_avg: Average undrained shear strength along sides (psf)
        c_u_base: Undrained shear strength at base (psf)

    Returns:
        Block failure capacity (lbs)
    """
    s_ft = spacing / 12.0
    d_ft = pile_width / 12.0

    B_g = (n_cols - 1) * s_ft + d_ft  # ft
    L_g = (n_rows - 1) * s_ft + d_ft  # ft
    D = embedment

    # Side friction
    Q_side = 2.0 * (B_g + L_g) * D * c_u_avg  # lbs

    # Base bearing
    N_c = 5.0 * (1.0 + 0.2 * (B_g / L_g)) * (1.0 + 0.2 * (D / B_g))
    N_c = min(N_c, 9.0)
    Q_base = B_g * L_g * N_c * c_u_base  # lbs

    return Q_side + Q_base


def group_analysis(
    profile: SoilProfile,
    n_rows: int,
    n_cols: int,
    pile_width: float,
    spacing: float,
    embedment: float,
    Q_single_compression: float,
    Q_single_tension: float = 0,
) -> GroupResult:
    """Complete pile group analysis.

    Args:
        profile: SoilProfile
        n_rows, n_cols: Group geometry
        pile_width: Pile width (in)
        spacing: Center-to-center spacing (in)
        embedment: Embedded depth (ft)
        Q_single_compression: Single pile ultimate compression capacity (lbs)
        Q_single_tension: Single pile ultimate tension capacity (lbs)
    """
    n_piles = n_rows * n_cols
    s_over_d = spacing / pile_width if pile_width > 0 else 999
    notes = []

    # Axial efficiency
    eta = converse_labarre(n_rows, n_cols, pile_width, spacing)
    Q_individual = eta * n_piles * Q_single_compression
    notes.append(f"Converse-Labarre eta = {eta:.3f}")

    # Block failure (check if any cohesive layers)
    Q_block = None
    has_cohesive = False
    cu_values = []
    for layer in profile.layers:
        if layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC):
            has_cohesive = True
            cu_values.append(layer.get_cu())

    if has_cohesive and cu_values:
        c_u_avg = sum(cu_values) / len(cu_values)
        tip_layer = profile.layer_at_depth(embedment - 0.1)
        c_u_base = tip_layer.get_cu() if tip_layer else c_u_avg
        Q_block = block_failure_cohesive(
            n_rows, n_cols, spacing, pile_width, embedment, c_u_avg, c_u_base,
        )
        notes.append(f"Block failure capacity = {Q_block:.0f} lbs")

    Q_governing = Q_individual
    if Q_block is not None:
        Q_governing = min(Q_individual, Q_block)
        if Q_block < Q_individual:
            notes.append("Block failure GOVERNS")
        else:
            notes.append("Individual pile failure governs")

    # Lateral p-multipliers
    pm = p_multipliers_table(n_rows, s_over_d)
    fm_sum = sum(r["f_m"] * n_cols for r in pm)
    eta_lateral = fm_sum / n_piles if n_piles > 0 else 1.0
    notes.append(f"Average lateral p-multiplier = {eta_lateral:.3f}")

    if s_over_d < 3:
        notes.append("WARNING: s/d < 3 — below minimum recommended spacing")
    elif s_over_d >= 8:
        notes.append("s/d >= 8 — group effects are negligible")

    return GroupResult(
        n_piles=n_piles,
        n_rows=n_rows,
        n_cols=n_cols,
        spacing=spacing,
        s_over_d=round(s_over_d, 1),
        eta_axial=round(eta, 3),
        Q_group_individual=round(Q_individual, 0),
        Q_block=round(Q_block, 0) if Q_block else None,
        Q_group_governing=round(Q_governing, 0),
        p_multipliers=pm,
        eta_lateral=round(eta_lateral, 3),
        method="Converse-Labarre + AASHTO p-multipliers",
        notes=notes,
    )
