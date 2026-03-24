"""Cable sag and clearance calculations for solar wire management systems.

Supports two cable management systems:
- **CAB** (Cable Above Below): Self-tensioning via wire weight. Uses lookup
  tables from the HDR/CAB Installation Guide (2017) for sag, tension, and
  pier reactions across span, temperature, wire weight, and wind speed.
- **AWM** (Above-ground Wire Management): Pre-tensioned messenger wire.
  Uses parabolic catenary formula for sag and horizontal tension.

The clearance check determines the minimum pile reveal (above-grade height)
so that the lowest cable point clears the ground or flood elevation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal


# ============================================================================
# CAB Installation Guide Lookup Tables (HDR Engineering, Rev 2, March 2016)
# ============================================================================

# Span range midpoints for interpolation (ft)
CAB_SPAN_RANGES = [
    (0, 15),
    (15, 20),
    (20, 25),
    (25, 30),
]
CAB_SPAN_MIDPOINTS = [7.5, 17.5, 22.5, 27.5]

# Table 1 — Stringing Tension (bare wire, lbs) vs temperature
# Keys: span_range_index, rows = temperatures
CAB_TENSION_TEMPS = [-40, 0, 30, 60, 90, 120]  # deg F
CAB_TABLE1_TENSION = [
    # 0-15 ft
    [369, 187, 73, 30, 20, 16],
    # 15-20 ft
    [284, 117, 48, 30, 23, 20],
    # 20-25 ft
    [183, 64, 39, 30, 25, 22],
    # 25-30 ft
    [92, 47, 36, 30, 26, 23],
]

# Table 2 — Stringing Sag (bare wire, inches) vs temperature
CAB_TABLE2_SAG = [
    # 0-15 ft
    [0.12, 0.24, 0.60, 1.32, 2.04, 2.52],
    # 15-20 ft
    [0.24, 0.60, 1.56, 2.40, 3.12, 3.72],
    # 20-25 ft
    [0.60, 1.80, 2.88, 3.72, 4.56, 5.16],
    # 25-30 ft
    [1.80, 3.48, 4.56, 5.40, 6.24, 6.96],
]

# Table 3 — Loaded Sag (inches) at three temperatures
# Indexed by [span_range][wire_weight_index][temp_index]
# Wire weights: 2, 5, 10, 15, 20, 25, 30 lb/ft
# Temperatures: 0F, 60F, 120F
CAB_TABLE3_WEIGHTS = [2, 5, 10, 15, 20, 25, 30]  # lb/ft
CAB_TABLE3_TEMPS = [0, 60, 120]  # deg F
CAB_TABLE3_SAG = [
    # 0-15 ft span
    [
        [1.7, 2.5, 3.2],    # 2 lb/ft
        [2.5, 3.2, 3.8],    # 5 lb/ft
        [3.2, 4.0, 4.5],    # 10 lb/ft
        [3.8, 4.5, 5.0],    # 15 lb/ft
        [4.2, 4.9, 5.4],    # 20 lb/ft
        [4.6, 5.2, 5.7],    # 25 lb/ft
        [4.9, 5.5, 6.0],    # 30 lb/ft
    ],
    # 15-20 ft span
    [
        [2.6, 3.8, 4.8],    # 2 lb/ft
        [3.8, 4.8, 5.6],    # 5 lb/ft
        [4.9, 6.0, 6.8],    # 10 lb/ft
        [5.7, 6.8, 7.6],    # 15 lb/ft
        [6.3, 7.2, 8.0],    # 20 lb/ft
        [6.8, 7.8, 8.5],    # 25 lb/ft
        [7.2, 8.2, 8.9],    # 30 lb/ft
    ],
    # 20-25 ft span
    [
        [3.8, 5.5, 6.8],    # 2 lb/ft
        [5.3, 6.8, 7.8],    # 5 lb/ft
        [6.7, 8.0, 9.2],    # 10 lb/ft
        [7.7, 9.0, 10.2],   # 15 lb/ft
        [8.5, 9.8, 11.0],   # 20 lb/ft
        [9.2, 10.5, 11.6],  # 25 lb/ft
        [9.8, 11.2, 12.2],  # 30 lb/ft
    ],
    # 25-30 ft span
    [
        [5.2, 7.3, 8.8],    # 2 lb/ft
        [7.0, 8.8, 10.2],   # 5 lb/ft
        [8.8, 10.5, 12.0],  # 10 lb/ft
        [10.0, 11.8, 13.2], # 15 lb/ft
        [11.0, 12.7, 14.0], # 20 lb/ft
        [11.8, 13.5, 14.8], # 25 lb/ft
        [12.5, 14.3, 15.5], # 30 lb/ft
    ],
]

# Table 4 — Dead End Pier Reactions (ASD, lbs)
# Indexed by [span_range][wind_speed_index][wire_weight_index]
# Each entry is (Transverse, Longitudinal, Vertical)
CAB_TABLE4_WIND_SPEEDS = [105, 110, 115, 120, 130, 140, 150, 170]  # mph
CAB_TABLE4_WEIGHTS = [2, 5, 10, 15, 20, 25, 30]  # lb/ft

# Table 4 data: [span_range][wind_speed_idx][weight_idx] -> (T, L, V)
# Extracted from CAB Installation Guide Table 4
CAB_TABLE4_REACTIONS: list[list[list[tuple[float, float, float]]]] = [
    # 0-15 ft span
    [
        # 105 mph
        [(37, 250, 15), (38, 300, 38), (40, 400, 75), (43, 490, 113), (45, 570, 150), (48, 640, 188), (50, 710, 225)],
        # 110 mph
        [(40, 250, 15), (42, 300, 38), (44, 400, 75), (46, 490, 113), (49, 570, 150), (51, 640, 188), (54, 710, 225)],
        # 115 mph
        [(44, 250, 15), (45, 300, 38), (48, 400, 75), (50, 490, 113), (53, 570, 150), (55, 640, 188), (58, 710, 225)],
        # 120 mph
        [(48, 250, 15), (49, 300, 38), (52, 400, 75), (54, 490, 113), (57, 570, 150), (59, 640, 188), (62, 710, 225)],
        # 130 mph
        [(56, 250, 15), (57, 300, 38), (60, 400, 75), (63, 490, 113), (65, 570, 150), (68, 640, 188), (70, 710, 225)],
        # 140 mph
        [(65, 250, 15), (67, 300, 38), (69, 400, 75), (72, 490, 113), (75, 570, 150), (77, 640, 188), (80, 710, 225)],
        # 150 mph
        [(75, 250, 15), (77, 300, 38), (79, 400, 75), (82, 490, 113), (85, 570, 150), (87, 640, 188), (90, 710, 225)],
        # 170 mph
        [(96, 250, 15), (98, 300, 38), (101, 400, 75), (103, 490, 113), (106, 570, 150), (109, 640, 188), (111, 710, 225)],
    ],
    # 15-20 ft span
    [
        [(50, 420, 20), (52, 510, 50), (55, 650, 100), (58, 780, 150), (60, 900, 200), (63, 1010, 250), (66, 1110, 300)],
        [(54, 420, 20), (56, 510, 50), (59, 650, 100), (62, 780, 150), (65, 900, 200), (67, 1010, 250), (70, 1110, 300)],
        [(59, 420, 20), (61, 510, 50), (64, 650, 100), (67, 780, 150), (69, 900, 200), (72, 1010, 250), (75, 1110, 300)],
        [(64, 420, 20), (66, 510, 50), (69, 650, 100), (72, 780, 150), (75, 900, 200), (77, 1010, 250), (80, 1110, 300)],
        [(74, 420, 20), (76, 510, 50), (79, 650, 100), (82, 780, 150), (85, 900, 200), (88, 1010, 250), (90, 1110, 300)],
        [(86, 420, 20), (88, 510, 50), (91, 650, 100), (94, 780, 150), (97, 900, 200), (99, 1010, 250), (102, 1110, 300)],
        [(99, 420, 20), (101, 510, 50), (104, 650, 100), (107, 780, 150), (110, 900, 200), (112, 1010, 250), (115, 1110, 300)],
        [(127, 420, 20), (129, 510, 50), (132, 650, 100), (135, 780, 150), (138, 900, 200), (141, 1010, 250), (143, 1110, 300)],
    ],
    # 20-25 ft span
    [
        [(62, 620, 25), (65, 750, 63), (69, 970, 125), (72, 1170, 188), (76, 1350, 250), (79, 1520, 313), (82, 1680, 375)],
        [(67, 620, 25), (70, 750, 63), (74, 970, 125), (77, 1170, 188), (81, 1350, 250), (84, 1520, 313), (87, 1680, 375)],
        [(73, 620, 25), (76, 750, 63), (80, 970, 125), (83, 1170, 188), (87, 1350, 250), (90, 1520, 313), (93, 1680, 375)],
        [(79, 620, 25), (82, 750, 63), (86, 970, 125), (90, 1170, 188), (93, 1350, 250), (97, 1520, 313), (100, 1680, 375)],
        [(93, 620, 25), (96, 750, 63), (100, 970, 125), (103, 1170, 188), (107, 1350, 250), (110, 1520, 313), (113, 1680, 375)],
        [(108, 620, 25), (111, 750, 63), (115, 970, 125), (118, 1170, 188), (122, 1350, 250), (125, 1520, 313), (128, 1680, 375)],
        [(124, 620, 25), (127, 750, 63), (131, 970, 125), (134, 1170, 188), (138, 1350, 250), (141, 1520, 313), (144, 1680, 375)],
        [(159, 620, 25), (162, 750, 63), (166, 970, 125), (169, 1170, 188), (173, 1350, 250), (176, 1520, 313), (179, 1680, 375)],
    ],
    # 25-30 ft span
    [
        [(75, 860, 30), (78, 1030, 75), (83, 1330, 150), (87, 1600, 225), (91, 1850, 300), (95, 2080, 375), (99, 2300, 450)],
        [(81, 860, 30), (84, 1030, 75), (89, 1330, 150), (93, 1600, 225), (97, 1850, 300), (101, 2080, 375), (105, 2300, 450)],
        [(88, 860, 30), (91, 1030, 75), (96, 1330, 150), (100, 1600, 225), (104, 1850, 300), (108, 2080, 375), (112, 2300, 450)],
        [(95, 860, 30), (99, 1030, 75), (103, 1330, 150), (107, 1600, 225), (111, 1850, 300), (115, 2080, 375), (119, 2300, 450)],
        [(111, 860, 30), (114, 1030, 75), (119, 1330, 150), (123, 1600, 225), (127, 1850, 300), (131, 2080, 375), (135, 2300, 450)],
        [(129, 860, 30), (132, 1030, 75), (137, 1330, 150), (141, 1600, 225), (145, 1850, 300), (149, 2080, 375), (153, 2300, 450)],
        [(148, 860, 30), (151, 1030, 75), (156, 1330, 150), (160, 1600, 225), (164, 1850, 300), (168, 2080, 375), (172, 2300, 450)],
        [(190, 860, 30), (193, 1030, 75), (198, 1330, 150), (202, 1600, 225), (206, 1850, 300), (210, 2080, 375), (214, 2300, 450)],
    ],
]


# ============================================================================
# Interpolation Helpers
# ============================================================================

def _interp1d(x: float, xs: list[float], ys: list[float]) -> float:
    """Linear interpolation / extrapolation on 1-D arrays."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def _span_range_index(span_ft: float) -> tuple[int, float]:
    """Return the bounding span range index and interpolation fraction.

    Returns (index, fraction) where fraction is 0.0 at the lower bound
    midpoint and 1.0 at the upper bound midpoint.
    """
    if span_ft <= CAB_SPAN_MIDPOINTS[0]:
        return 0, 0.0
    if span_ft >= CAB_SPAN_MIDPOINTS[-1]:
        return len(CAB_SPAN_MIDPOINTS) - 2, 1.0
    for i in range(len(CAB_SPAN_MIDPOINTS) - 1):
        if CAB_SPAN_MIDPOINTS[i] <= span_ft <= CAB_SPAN_MIDPOINTS[i + 1]:
            t = (span_ft - CAB_SPAN_MIDPOINTS[i]) / (
                CAB_SPAN_MIDPOINTS[i + 1] - CAB_SPAN_MIDPOINTS[i]
            )
            return i, t
    return len(CAB_SPAN_MIDPOINTS) - 2, 1.0


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CableSagResult:
    """Results of a cable sag and clearance analysis."""

    system: str                          # "CAB" or "AWM"
    span_ft: float
    wire_weight_plf: float               # lb/ft

    # Sag
    sag_in: float                        # design sag at mid-span (inches)
    sag_ft: float                        # sag in feet

    # Clearance check
    mounting_height_in: float            # pile mounting point height (in)
    bracket_drop_in: float               # bracket offset (positive = drops)
    hanger_height_in: float              # messenger to bottom of cables
    pile_top_clearance_in: float         # clearance above bracket on pile
    ground_clearance_req_in: float       # required ground clearance
    flood_freeboard_in: float            # flood freeboard (0 if N/A)

    min_reveal_in: float                 # minimum pile height above grade
    min_reveal_ft: float                 # min reveal in feet
    actual_reveal_in: float              # actual above-grade height
    actual_reveal_ft: float              # actual in feet
    clearance_at_midspan_in: float       # actual clearance at lowest point
    passes: bool                         # clearance check pass/fail

    # Pier loads (ASD, per dead-end pier)
    V_vertical_lbs: float = 0.0          # vertical reaction
    H_longitudinal_lbs: float = 0.0      # longitudinal (along messenger)
    H_transverse_lbs: float = 0.0        # transverse (wind on wire)

    # Temperature
    temp_min_f: float = 0.0
    temp_max_f: float = 120.0

    notes: list[str] = field(default_factory=list)


# ============================================================================
# CAB System — Table Lookup
# ============================================================================

def cab_loaded_sag(
    span_ft: float,
    wire_weight_plf: float,
    temp_f: float,
) -> float:
    """Interpolate loaded sag (inches) from CAB Table 3.

    Args:
        span_ft: Support-to-support span (ft).
        wire_weight_plf: Vertical wire weight (lb/ft).
        temp_f: Temperature (deg F).

    Returns:
        Mid-span sag in inches.
    """
    idx, span_frac = _span_range_index(span_ft)

    def _sag_at_range(ri: int) -> float:
        # Interpolate across wire weight, then temperature
        weights = CAB_TABLE3_WEIGHTS
        temps = CAB_TABLE3_TEMPS
        # For each weight, interpolate across temperature
        sag_at_weight = []
        for wi in range(len(weights)):
            s = _interp1d(temp_f, temps, CAB_TABLE3_SAG[ri][wi])
            sag_at_weight.append(s)
        # Interpolate across weight
        return _interp1d(wire_weight_plf, weights, sag_at_weight)

    s_lo = _sag_at_range(idx)
    s_hi = _sag_at_range(min(idx + 1, len(CAB_SPAN_MIDPOINTS) - 1))
    return s_lo + span_frac * (s_hi - s_lo)


def cab_bare_sag(span_ft: float, temp_f: float) -> float:
    """Interpolate bare-wire sag (inches) from CAB Table 2."""
    idx, span_frac = _span_range_index(span_ft)
    temps = CAB_TENSION_TEMPS

    s_lo = _interp1d(temp_f, temps, CAB_TABLE2_SAG[idx])
    s_hi = _interp1d(temp_f, temps, CAB_TABLE2_SAG[min(idx + 1, len(CAB_SPAN_MIDPOINTS) - 1)])
    return s_lo + span_frac * (s_hi - s_lo)


def cab_pier_reactions(
    span_ft: float,
    wire_weight_plf: float,
    wind_speed_mph: float,
) -> tuple[float, float, float]:
    """Interpolate dead-end pier reactions (T, L, V) from CAB Table 4.

    Returns:
        (Transverse, Longitudinal, Vertical) in lbs (ASD).
    """
    idx, span_frac = _span_range_index(span_ft)
    winds = CAB_TABLE4_WIND_SPEEDS
    weights = CAB_TABLE4_WEIGHTS

    def _reactions_at_range(ri: int) -> tuple[float, float, float]:
        # For each wind speed, interpolate across wire weight
        t_at_wind, l_at_wind, v_at_wind = [], [], []
        for wi_speed in range(len(winds)):
            ts = [CAB_TABLE4_REACTIONS[ri][wi_speed][ww][0] for ww in range(len(weights))]
            ls = [CAB_TABLE4_REACTIONS[ri][wi_speed][ww][1] for ww in range(len(weights))]
            vs = [CAB_TABLE4_REACTIONS[ri][wi_speed][ww][2] for ww in range(len(weights))]
            t_at_wind.append(_interp1d(wire_weight_plf, weights, ts))
            l_at_wind.append(_interp1d(wire_weight_plf, weights, ls))
            v_at_wind.append(_interp1d(wire_weight_plf, weights, vs))
        T = _interp1d(wind_speed_mph, winds, t_at_wind)
        L = _interp1d(wind_speed_mph, winds, l_at_wind)
        V = _interp1d(wind_speed_mph, winds, v_at_wind)
        return T, L, V

    t_lo, l_lo, v_lo = _reactions_at_range(idx)
    t_hi, l_hi, v_hi = _reactions_at_range(min(idx + 1, len(CAB_SPAN_MIDPOINTS) - 1))
    T = t_lo + span_frac * (t_hi - t_lo)
    L = l_lo + span_frac * (l_hi - l_lo)
    V = v_lo + span_frac * (v_hi - v_lo)
    return T, L, V


# ============================================================================
# AWM System — Parabolic Catenary
# ============================================================================

def awm_sag(
    span_ft: float,
    wire_weight_plf: float,
    tension_lbs: float | None = None,
    allowable_sag_in: float | None = None,
) -> tuple[float, float]:
    """Compute AWM sag and horizontal tension using parabolic approximation.

    Provide either tension_lbs (to compute sag) or allowable_sag_in (to
    compute required tension). If both are provided, tension_lbs is used.

    Formula: sag = q * L^2 / (8 * H)
    Where q = wire weight (lb/ft), L = span (ft), H = horizontal tension (lbs)

    Returns:
        (sag_in, tension_lbs)
    """
    q = wire_weight_plf
    L = span_ft

    if tension_lbs is not None and tension_lbs > 0:
        sag_ft = q * L**2 / (8 * tension_lbs)
        return sag_ft * 12, tension_lbs

    if allowable_sag_in is not None and allowable_sag_in > 0:
        sag_ft = allowable_sag_in / 12.0
        H = q * L**2 / (8 * sag_ft)
        return allowable_sag_in, H

    # Default: assume 30 lbs tension at 60F (typical stringing tension)
    H = 30.0
    sag_ft = q * L**2 / (8 * H) if H > 0 else 0
    return sag_ft * 12, H


def awm_temperature_sag_adjustment(
    base_sag_in: float,
    temp_min_f: float,
    temp_max_f: float,
) -> float:
    """Estimate additional sag due to thermal expansion.

    Uses coefficient of thermal expansion for galvanized steel wire:
    alpha ~= 6.5e-6 per deg F.

    Returns total design sag including temperature effect (inches).
    """
    # Temperature range above the assumed installation temp (60F)
    delta_T = max(0, temp_max_f - 60.0)
    alpha = 6.5e-6  # per deg F for steel
    # Approximate sag increase: proportional to thermal strain
    # For a catenary, sag increases roughly as sag * (1 + alpha * dT * L/sag)
    # Simplified: add ~15-25% for extreme temperature range
    expansion_factor = 1.0 + alpha * delta_T * 100  # empirical scaling
    return base_sag_in * expansion_factor


# ============================================================================
# Clearance Check (common to both systems)
# ============================================================================

def cable_clearance_check(
    system: Literal["CAB", "AWM"],
    span_ft: float,
    wire_weight_plf: float,
    actual_reveal_ft: float,
    ground_clearance_in: float = 18.0,
    flood_freeboard_in: float = 0.0,
    bracket_drop_in: float = 5.5,
    hanger_height_in: float = 8.0,
    pile_top_clearance_in: float = 1.0,
    # CAB-specific
    temp_min_f: float = 0.0,
    temp_max_f: float = 120.0,
    wind_speed_mph: float = 115.0,
    # AWM-specific
    awm_tension_lbs: float | None = None,
    awm_allowable_sag_in: float | None = None,
    temp_sag_in: float | None = None,
) -> CableSagResult:
    """Run cable sag analysis and clearance check.

    Args:
        system: "CAB" or "AWM".
        span_ft: Span between supporting piles (ft).
        wire_weight_plf: Wire weight including cables (lb/ft).
        actual_reveal_ft: Actual pile height above grade (ft).
        ground_clearance_in: Minimum required ground clearance (in).
        flood_freeboard_in: Flood freeboard requirement (in), 0 if N/A.
        bracket_drop_in: Bracket offset below mounting point (in).
            CAB default ~5.5 in (L-bracket); AWM default ~-1 in (raises wire).
        hanger_height_in: Distance from messenger to bottom of lowest cable (in).
        pile_top_clearance_in: Clearance from pile top to bracket (in).
        temp_min_f: Site minimum temperature (deg F).
        temp_max_f: Site maximum temperature (deg F).
        wind_speed_mph: Design wind speed (mph), for CAB pier reactions.
        awm_tension_lbs: AWM stringing tension (lbs).
        awm_allowable_sag_in: AWM allowable sag (in) — alternative to tension.
        temp_sag_in: Manual temperature sag allowance (in). If None, auto-computed.

    Returns:
        CableSagResult with sag, clearance check, and pier loads.
    """
    notes: list[str] = []
    V_vert = 0.0
    H_long = 0.0
    H_trans = 0.0

    if system == "CAB":
        # Use Table 3 for loaded sag at worst-case temperature
        sag_at_max = cab_loaded_sag(span_ft, wire_weight_plf, temp_max_f)
        sag_at_min = cab_loaded_sag(span_ft, wire_weight_plf, temp_min_f)
        # Also get bare-wire sag for temperature component
        bare_sag_max = cab_bare_sag(span_ft, temp_max_f)

        # Design sag = worst case (usually at highest temperature)
        design_sag_in = max(sag_at_max, sag_at_min)
        notes.append(
            f"CAB Table 3 loaded sag: {sag_at_max:.1f} in at {temp_max_f:.0f}°F, "
            f"{sag_at_min:.1f} in at {temp_min_f:.0f}°F"
        )

        # Pier reactions from Table 4
        H_trans, H_long, V_vert = cab_pier_reactions(
            span_ft, wire_weight_plf, wind_speed_mph
        )
        notes.append(
            f"CAB Table 4 dead-end pier reactions (ASD): "
            f"T={H_trans:.0f}, L={H_long:.0f}, V={V_vert:.0f} lbs"
        )
        notes.append(
            f"Mid-support pier: T={2*H_trans:.0f}, V={2*V_vert:.0f} lbs; L=0"
        )

    elif system == "AWM":
        # Parabolic catenary
        base_sag_in, H_tension = awm_sag(
            span_ft, wire_weight_plf,
            tension_lbs=awm_tension_lbs,
            allowable_sag_in=awm_allowable_sag_in,
        )

        # Temperature sag
        if temp_sag_in is not None:
            t_sag = temp_sag_in
        else:
            t_sag = awm_temperature_sag_adjustment(base_sag_in, temp_min_f, temp_max_f) - base_sag_in
            t_sag = max(0, t_sag)

        design_sag_in = base_sag_in + t_sag
        notes.append(f"AWM catenary sag: {base_sag_in:.2f} in + {t_sag:.2f} in (temperature) = {design_sag_in:.2f} in")
        notes.append(f"Horizontal tension: {H_tension:.0f} lbs")

        # AWM pier loads (parabolic)
        V_vert = wire_weight_plf * span_ft / 2.0
        H_long = H_tension
        # Add freezing tension if cold climate
        if temp_min_f < 32:
            freeze_tension = 26.0  # typical AWM freezing add-on
            H_long += freeze_tension
            notes.append(f"Freezing tension added: {freeze_tension:.0f} lbs")

        notes.append(f"Dead-end pier: V={V_vert:.0f}, L={H_long:.0f} lbs")

    else:
        raise ValueError(f"Unknown system: {system}")

    # Clearance check
    actual_reveal_in = actual_reveal_ft * 12.0
    mounting_height_in = actual_reveal_in - pile_top_clearance_in
    required_clearance_in = max(ground_clearance_in, flood_freeboard_in)

    # Lowest cable point elevation above grade:
    # = mounting_height - bracket_drop - sag - hanger_height
    lowest_point_in = mounting_height_in - bracket_drop_in - design_sag_in - hanger_height_in
    clearance_at_midspan_in = lowest_point_in

    # Minimum reveal
    min_reveal_in = (
        pile_top_clearance_in
        + bracket_drop_in
        + design_sag_in
        + hanger_height_in
        + required_clearance_in
    )
    min_reveal_ft = math.ceil(min_reveal_in / 6.0) * 0.5  # round up to nearest 0.5 ft

    passes = clearance_at_midspan_in >= required_clearance_in

    notes.append(
        f"Clearance at midspan: {clearance_at_midspan_in:.1f} in "
        f"vs required {required_clearance_in:.1f} in"
    )

    return CableSagResult(
        system=system,
        span_ft=span_ft,
        wire_weight_plf=wire_weight_plf,
        sag_in=design_sag_in,
        sag_ft=design_sag_in / 12.0,
        mounting_height_in=mounting_height_in,
        bracket_drop_in=bracket_drop_in,
        hanger_height_in=hanger_height_in,
        pile_top_clearance_in=pile_top_clearance_in,
        ground_clearance_req_in=ground_clearance_in,
        flood_freeboard_in=flood_freeboard_in,
        min_reveal_in=min_reveal_in,
        min_reveal_ft=min_reveal_ft,
        actual_reveal_in=actual_reveal_in,
        actual_reveal_ft=actual_reveal_ft,
        clearance_at_midspan_in=clearance_at_midspan_in,
        passes=passes,
        V_vertical_lbs=V_vert,
        H_longitudinal_lbs=H_long,
        H_transverse_lbs=H_trans,
        temp_min_f=temp_min_f,
        temp_max_f=temp_max_f,
        notes=notes,
    )
