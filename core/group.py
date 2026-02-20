"""Pile group efficiency, p-multipliers, and block failure analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

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


# ---------------------------------------------------------------------------
# Enercalc-style individual pile placement dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PileLocation:
    """A single pile with its coordinates."""
    id: int          # 1-based pile number
    x: float         # ft, from origin
    y: float         # ft, from origin
    label: str = ""


@dataclass
class LoadPoint:
    """A single load application point."""
    id: int
    x: float          # ft
    y: float          # ft
    V: float           # lbs (+ = compression, - = tension)
    H_x: float = 0.0  # lbs, lateral in X
    H_y: float = 0.0  # lbs, lateral in Y
    M_x: float = 0.0  # ft-lbs, moment about X-axis
    M_y: float = 0.0  # ft-lbs, moment about Y-axis


@dataclass
class PileReaction:
    """Computed reaction at a single pile."""
    pile_id: int
    x: float           # ft
    y: float           # ft
    label: str
    P_axial: float     # lbs (+ = compression)
    utilization: float  # demand / capacity (0–1+)
    governs: bool


@dataclass
class RigidCapResult:
    """Results from rigid-cap load distribution analysis."""
    piles: list[PileLocation]
    n_piles: int

    # Centroids and eccentricity
    pile_centroid_x: float      # ft
    pile_centroid_y: float      # ft
    load_centroid_x: float      # ft
    load_centroid_y: float      # ft
    eccentricity_x: float      # ft (load_cx - pile_cx)
    eccentricity_y: float      # ft

    # Load resultants at pile group centroid
    V_total: float              # lbs
    M_x_total: float            # ft-lbs (includes V * e_y)
    M_y_total: float            # ft-lbs (includes V * e_x)

    # Individual pile reactions
    reactions: list[PileReaction]
    P_max: float                # lbs, max compression
    P_min: float                # lbs, max tension (most negative)
    governing_pile_id: int

    # Utilization
    max_utilization: float
    all_piles_ok: bool

    # Legacy compatibility
    eta_axial: float
    p_multipliers: list[dict]
    eta_lateral: float

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


# ---------------------------------------------------------------------------
# Enercalc-style rigid cap load distribution
# ---------------------------------------------------------------------------

def generate_pile_grid(
    n_rows: int,
    n_cols: int,
    x_spacing_ft: float,
    y_spacing_ft: float,
) -> list[PileLocation]:
    """Generate a rectangular grid of pile positions.

    Origin (0, 0) at bottom-left. X = columns (along tracker),
    Y = rows (perpendicular).  Piles numbered left-to-right,
    bottom-to-top.
    """
    piles: list[PileLocation] = []
    pid = 1
    for row in range(n_rows):
        for col in range(n_cols):
            piles.append(PileLocation(
                id=pid,
                x=round(col * x_spacing_ft, 4),
                y=round(row * y_spacing_ft, 4),
                label=f"R{row + 1}C{col + 1}",
            ))
            pid += 1
    return piles


def compute_pile_group_centroid(
    piles: list[PileLocation],
) -> tuple[float, float]:
    """Geometric centroid of the pile group (ft)."""
    n = len(piles)
    if n == 0:
        return 0.0, 0.0
    cx = sum(p.x for p in piles) / n
    cy = sum(p.y for p in piles) / n
    return cx, cy


def compute_load_resultant(
    loads: list[LoadPoint],
    pile_centroid: tuple[float, float],
) -> tuple[float, float, float, float, float]:
    """Compute load resultant transferred to the pile group centroid.

    Returns:
        (V_total, M_x_total, M_y_total, load_centroid_x, load_centroid_y)

    Sign convention:
        M_x about X-axis (causes bending in Y direction).
        M_y about Y-axis (causes bending in X direction).
    """
    V_total = sum(L.V for L in loads)
    pcx, pcy = pile_centroid

    # Load centroid — weighted by absolute vertical force
    abs_sum = sum(abs(L.V) for L in loads)
    if abs_sum > 0:
        load_cx = sum(L.V * L.x for L in loads) / V_total if V_total != 0 else (
            sum(L.x for L in loads) / len(loads)
        )
        load_cy = sum(L.V * L.y for L in loads) / V_total if V_total != 0 else (
            sum(L.y for L in loads) / len(loads)
        )
    else:
        load_cx = sum(L.x for L in loads) / len(loads) if loads else pcx
        load_cy = sum(L.y for L in loads) / len(loads) if loads else pcy

    ex = load_cx - pcx
    ey = load_cy - pcy

    # Transfer moments to pile centroid
    M_x_total = sum(L.M_x for L in loads) + V_total * ey
    M_y_total = sum(L.M_y for L in loads) + V_total * ex

    return V_total, M_x_total, M_y_total, load_cx, load_cy


def _infer_grid_dims(piles: list[PileLocation]) -> tuple[int, int, float]:
    """Infer n_rows, n_cols, and average spacing from pile layout.

    Used for Converse-Labarre and p-multiplier calculations.
    Returns (n_rows, n_cols, avg_spacing_in).
    """
    if len(piles) <= 1:
        return 1, 1, 0.0

    xs = sorted(set(round(p.x, 2) for p in piles))
    ys = sorted(set(round(p.y, 2) for p in piles))
    n_cols = len(xs)
    n_rows = len(ys)

    spacings: list[float] = []
    for i in range(1, len(xs)):
        spacings.append(abs(xs[i] - xs[i - 1]))
    for i in range(1, len(ys)):
        spacings.append(abs(ys[i] - ys[i - 1]))

    avg_spacing_ft = sum(spacings) / len(spacings) if spacings else 0.0
    return n_rows, n_cols, avg_spacing_ft * 12.0  # convert to inches


def rigid_cap_distribution(
    piles: list[PileLocation],
    loads: list[LoadPoint],
    Q_capacity_compression: float = 0.0,
    Q_capacity_tension: float = 0.0,
    profile: SoilProfile | None = None,
    pile_width: float = 0.0,
    embedment: float = 0.0,
) -> RigidCapResult:
    """Rigid-cap load distribution to individual piles.

    Implements:  P_i = V/n + M_x * y_i / sum(y_j^2) + M_y * x_i / sum(x_j^2)

    Coordinates are shifted to pile group centroid before applying the formula.
    """
    n = len(piles)
    notes: list[str] = []

    if n == 0:
        raise ValueError("No piles defined.")

    # Centroid
    pcx, pcy = compute_pile_group_centroid(piles)

    # Centroid-relative coordinates
    xi = [p.x - pcx for p in piles]
    yi = [p.y - pcy for p in piles]

    sum_x2 = sum(x ** 2 for x in xi)
    sum_y2 = sum(y ** 2 for y in yi)

    # Load resultant at centroid
    V_total, M_x_total, M_y_total, load_cx, load_cy = compute_load_resultant(
        loads, (pcx, pcy),
    )
    ex = load_cx - pcx
    ey = load_cy - pcy

    notes.append(f"Pile group centroid: ({pcx:.2f}, {pcy:.2f}) ft")
    notes.append(f"Load centroid: ({load_cx:.2f}, {load_cy:.2f}) ft")
    if abs(ex) > 0.001 or abs(ey) > 0.001:
        notes.append(f"Eccentricity: e_x = {ex:.3f} ft, e_y = {ey:.3f} ft")

    # Distribute to each pile
    reactions: list[PileReaction] = []
    for i, p in enumerate(piles):
        P_i = V_total / n
        if sum_y2 > 1e-9:
            P_i += M_x_total * yi[i] / sum_y2
        if sum_x2 > 1e-9:
            P_i += M_y_total * xi[i] / sum_x2

        # Utilization
        if P_i >= 0 and Q_capacity_compression > 0:
            util = P_i / Q_capacity_compression
        elif P_i < 0 and Q_capacity_tension > 0:
            util = abs(P_i) / Q_capacity_tension
        else:
            util = 0.0

        reactions.append(PileReaction(
            pile_id=p.id,
            x=p.x,
            y=p.y,
            label=p.label,
            P_axial=round(P_i, 1),
            utilization=round(util, 4),
            governs=False,
        ))

    # Identify governing pile
    if reactions:
        max_idx = max(range(len(reactions)), key=lambda j: abs(reactions[j].P_axial))
        reactions[max_idx] = PileReaction(
            pile_id=reactions[max_idx].pile_id,
            x=reactions[max_idx].x,
            y=reactions[max_idx].y,
            label=reactions[max_idx].label,
            P_axial=reactions[max_idx].P_axial,
            utilization=reactions[max_idx].utilization,
            governs=True,
        )
        P_max = max(r.P_axial for r in reactions)
        P_min = min(r.P_axial for r in reactions)
        governing_id = reactions[max_idx].pile_id
        max_util = max(r.utilization for r in reactions)
    else:
        P_max = P_min = 0.0
        governing_id = 0
        max_util = 0.0

    all_ok = all(r.utilization <= 1.0 for r in reactions)

    if P_max > 0:
        notes.append(f"Max compression: {P_max:,.0f} lbs (Pile {governing_id})")
    if P_min < 0:
        min_pile = min(reactions, key=lambda r: r.P_axial)
        notes.append(f"Max tension: {abs(P_min):,.0f} lbs (Pile {min_pile.pile_id})")

    # Legacy: Converse-Labarre and p-multipliers from inferred grid
    n_rows_inf, n_cols_inf, avg_spacing_in = _infer_grid_dims(piles)
    s_over_d = avg_spacing_in / pile_width if pile_width > 0 else 999
    eta_axial = converse_labarre(n_rows_inf, n_cols_inf, pile_width, avg_spacing_in)
    pm = p_multipliers_table(n_rows_inf, s_over_d)
    fm_sum = sum(r["f_m"] * n_cols_inf for r in pm)
    eta_lat = fm_sum / n if n > 0 else 1.0

    notes.append(f"Converse-Labarre eta = {eta_axial:.3f} (inferred {n_rows_inf}x{n_cols_inf} grid)")
    notes.append(f"Average lateral p-multiplier = {eta_lat:.3f}")

    return RigidCapResult(
        piles=piles,
        n_piles=n,
        pile_centroid_x=round(pcx, 4),
        pile_centroid_y=round(pcy, 4),
        load_centroid_x=round(load_cx, 4),
        load_centroid_y=round(load_cy, 4),
        eccentricity_x=round(ex, 4),
        eccentricity_y=round(ey, 4),
        V_total=round(V_total, 1),
        M_x_total=round(M_x_total, 1),
        M_y_total=round(M_y_total, 1),
        reactions=reactions,
        P_max=round(P_max, 1),
        P_min=round(P_min, 1),
        governing_pile_id=governing_id,
        max_utilization=round(max_util, 4),
        all_piles_ok=all_ok,
        eta_axial=round(eta_axial, 3),
        p_multipliers=pm,
        eta_lateral=round(eta_lat, 3),
        method="Rigid cap distribution (P_i = V/n + M_x*y_i/sum(y_j^2) + M_y*x_i/sum(x_j^2))",
        notes=notes,
    )
