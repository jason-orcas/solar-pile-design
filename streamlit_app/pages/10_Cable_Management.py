"""Page 10 — Cable Management & Sag Analysis.

Calculates messenger wire sag, checks ground clearance, and computes
pier loads for CAB and AWM cable management systems.
"""

import streamlit as st

st.set_page_config(page_title="Cable Management", layout="wide")
st.title("Cable Management & Sag Analysis")
st.caption(
    "Verify that the pile reveal provides adequate ground clearance after "
    "accounting for messenger wire sag, bracket geometry, and cable hangers."
)

from core.cable_sag import (
    cable_clearance_check,
    cab_loaded_sag,
    cab_bare_sag,
    CAB_SPAN_RANGES,
    CAB_TABLE3_WEIGHTS,
    CAB_TABLE3_TEMPS,
)

# ============================================================================
# Section A: System Selection
# ============================================================================
st.markdown("---")
st.subheader("Cable Management System")

system = st.radio(
    "System type",
    ["CAB", "AWM"],
    horizontal=True,
    help="**CAB**: Self-tensioning via wire weight (HDR/CAB tables). "
         "**AWM**: Pre-tensioned messenger wire (catenary formula).",
    key="cable_system",
)

# ============================================================================
# Section B: Span & Wire
# ============================================================================
st.markdown("---")
st.subheader("Span & Wire Properties")

c1, c2 = st.columns(2)
with c1:
    span_ft = st.number_input(
        "Span between piles (ft)", min_value=1.0, value=21.5,
        step=0.5, format="%.1f", key="cable_span_ft",
    )
with c2:
    wire_weight = st.number_input(
        "Wire weight incl. cables (lb/ft)", min_value=0.1, value=8.85,
        step=0.5, format="%.2f", key="cable_wire_weight",
        help="Total distributed load on the messenger wire: wire self-weight "
             "plus all supported cables. Typical: 5–15 lb/ft.",
    )

# ============================================================================
# Section C: Temperature
# ============================================================================
st.subheader("Temperature Range")

tc1, tc2 = st.columns(2)
with tc1:
    temp_min = st.number_input(
        "Annual minimum temp (°F)", value=0.0, step=5.0,
        format="%.0f", key="cable_temp_min",
    )
with tc2:
    temp_max = st.number_input(
        "Annual maximum temp (°F)", value=120.0, step=5.0,
        format="%.0f", key="cable_temp_max",
    )

# ============================================================================
# Section D: Bracket & Hanger Geometry
# ============================================================================
st.markdown("---")
st.subheader("Bracket & Hanger Geometry")

if system == "CAB":
    default_bracket = 5.5
    bracket_help = "CAB L-bracket drops the messenger ~5.5 in below the mounting point."
else:
    default_bracket = -1.0
    bracket_help = "AWM straight bracket typically raises the wire ~1 in above mounting (enter negative value)."

gc1, gc2, gc3 = st.columns(3)
with gc1:
    bracket_drop = st.number_input(
        "Bracket drop (in)", value=default_bracket, step=0.5,
        format="%.1f", key="cable_bracket_drop",
        help=bracket_help,
    )
with gc2:
    hanger_height = st.number_input(
        "Hanger height (in)", value=8.0, step=0.5,
        format="%.1f", key="cable_hanger_height",
        help="Distance from center of messenger wire to the bottom of the "
             "lowest cable resting in the hanger.",
    )
with gc3:
    pile_top_clr = st.number_input(
        "Pile-top clearance (in)", value=1.0, step=0.5,
        format="%.1f", key="cable_pile_top_clr",
        help="Minimum clearance from the top of the pile to the bracket.",
    )

# ============================================================================
# Section E: Clearance Requirements
# ============================================================================
st.subheader("Clearance Requirements")

cr1, cr2 = st.columns(2)
with cr1:
    ground_clearance = st.number_input(
        "Required ground clearance (in)", min_value=0.0,
        value=18.0, step=1.0, format="%.0f", key="cable_ground_clr",
        help="Minimum distance from the lowest cable point to grade. "
             "Client or code requirement (commonly 18 in).",
    )
with cr2:
    flood_freeboard = st.number_input(
        "Flood freeboard (in)", min_value=0.0,
        value=0.0, step=1.0, format="%.0f", key="cable_flood_freeboard",
        help="Required clearance above flood elevation. Enter 0 if not applicable. "
             "Governs over ground clearance when greater.",
    )

# ============================================================================
# Section F: Pile Reveal
# ============================================================================
st.subheader("Pile Above-Grade Height")

above_grade = st.session_state.get("above_grade")
default_reveal = above_grade if above_grade and above_grade > 0 else 4.5

reveal_ft = st.number_input(
    "Actual pile reveal (ft)", min_value=0.5,
    value=default_reveal, step=0.5, format="%.1f",
    key="cable_reveal_ft",
    help="Height of pile above grade (from Page 03 or site layout).",
)

# ============================================================================
# Section G: AWM-Specific Inputs
# ============================================================================
awm_tension = None
awm_sag_limit = None
temp_sag_manual = None

if system == "AWM":
    st.markdown("---")
    st.subheader("AWM Tension Settings")

    awm_mode = st.radio(
        "Define by",
        ["Stringing tension", "Allowable sag"],
        horizontal=True,
        key="awm_input_mode",
    )
    ac1, ac2 = st.columns(2)
    if awm_mode == "Stringing tension":
        with ac1:
            awm_tension = st.number_input(
                "Stringing tension (lbs)", min_value=1.0,
                value=26.0, step=5.0, format="%.0f",
                key="awm_tension_lbs",
                help="Horizontal tension in the messenger wire at installation. "
                     "Typical: 20–30 lbs at 60°F.",
            )
    else:
        with ac1:
            awm_sag_limit = st.number_input(
                "Allowable sag (in)", min_value=0.1,
                value=6.0, step=0.5, format="%.1f",
                key="awm_sag_limit",
            )
    with ac2:
        temp_sag_manual = st.number_input(
            "Temperature sag allowance (in)", min_value=0.0,
            value=4.32, step=0.5, format="%.2f",
            key="awm_temp_sag",
            help="Additional sag due to thermal expansion. Enter 0 for auto-estimate.",
        )
        if temp_sag_manual == 0:
            temp_sag_manual = None

# ============================================================================
# Section H: Wind Speed (CAB pier reactions)
# ============================================================================
wind_speed = 115.0
if system == "CAB":
    wind_speed_state = st.session_state.get("wind_speed")
    if wind_speed_state and wind_speed_state > 0:
        wind_speed = wind_speed_state
    wind_speed = st.number_input(
        "Design wind speed (mph)", min_value=90.0,
        value=wind_speed, step=5.0, format="%.0f",
        key="cable_wind_speed",
        help="ASCE 7 basic wind speed for pier reaction lookup (Table 4).",
    )

# ============================================================================
# Run Analysis
# ============================================================================
st.markdown("---")

# Guard None values
_span = span_ft if span_ft is not None else 21.5
_ww = wire_weight if wire_weight is not None else 8.85
_reveal = reveal_ft if reveal_ft is not None else 4.5
_gc = ground_clearance if ground_clearance is not None else 18.0
_ff = flood_freeboard if flood_freeboard is not None else 0.0
_bd = bracket_drop if bracket_drop is not None else 5.5
_hh = hanger_height if hanger_height is not None else 8.0
_ptc = pile_top_clr if pile_top_clr is not None else 1.0
_tmin = temp_min if temp_min is not None else 0.0
_tmax = temp_max if temp_max is not None else 120.0
_ws = wind_speed if wind_speed is not None else 115.0

if st.button("Run Cable Sag Analysis", type="primary"):
    result = cable_clearance_check(
        system=system,
        span_ft=_span,
        wire_weight_plf=_ww,
        actual_reveal_ft=_reveal,
        ground_clearance_in=_gc,
        flood_freeboard_in=_ff,
        bracket_drop_in=_bd,
        hanger_height_in=_hh,
        pile_top_clearance_in=_ptc,
        temp_min_f=_tmin,
        temp_max_f=_tmax,
        wind_speed_mph=_ws,
        awm_tension_lbs=awm_tension,
        awm_allowable_sag_in=awm_sag_limit,
        temp_sag_in=temp_sag_manual,
    )
    st.session_state["cable_sag_result"] = result

    # --- Results ---
    st.subheader("Results")

    # Pass/fail banner
    if result.passes:
        st.success(
            f"PASS — Clearance at midspan: {result.clearance_at_midspan_in:.1f} in "
            f"≥ required {max(_gc, _ff):.0f} in"
        )
    else:
        st.error(
            f"FAIL — Clearance at midspan: {result.clearance_at_midspan_in:.1f} in "
            f"< required {max(_gc, _ff):.0f} in"
        )

    # Sag summary
    r1, r2, r3 = st.columns(3)
    r1.metric("Design Sag", f"{result.sag_in:.1f} in")
    r2.metric("Min Pile Reveal", f"{result.min_reveal_ft:.1f} ft ({result.min_reveal_in:.0f} in)")
    r3.metric("Midspan Clearance", f"{result.clearance_at_midspan_in:.1f} in")

    # Clearance breakdown
    st.markdown("#### Clearance Breakdown")
    breakdown = {
        "Pile reveal (above grade)": f"{result.actual_reveal_in:.1f} in",
        "− Pile-top clearance": f"−{result.pile_top_clearance_in:.1f} in",
        "− Bracket drop": f"−{result.bracket_drop_in:.1f} in",
        "− Design sag": f"−{result.sag_in:.1f} in",
        "− Hanger height": f"−{result.hanger_height_in:.1f} in",
        "**= Clearance at midspan**": f"**{result.clearance_at_midspan_in:.1f} in**",
    }
    for label, val in breakdown.items():
        st.markdown(f"- {label}: {val}")

    req = max(result.ground_clearance_req_in, result.flood_freeboard_in)
    st.markdown(f"- Required clearance: **{req:.0f} in**")

    # Pier loads
    st.markdown("#### Dead-End Pier Loads (ASD)")
    lc1, lc2, lc3 = st.columns(3)
    lc1.metric("Transverse", f"{result.H_transverse_lbs:.0f} lbs")
    lc2.metric("Longitudinal", f"{result.H_longitudinal_lbs:.0f} lbs")
    lc3.metric("Vertical", f"{result.V_vertical_lbs:.0f} lbs")

    if system == "CAB":
        st.caption(
            f"Mid-support pier loads: Transverse = {2*result.H_transverse_lbs:.0f} lbs, "
            f"Vertical = {2*result.V_vertical_lbs:.0f} lbs, Longitudinal = 0 lbs. "
            f"Double all values if two parallel messenger systems."
        )

    # Notes
    if result.notes:
        with st.expander("Analysis Notes", expanded=False):
            for note in result.notes:
                st.markdown(f"- {note}")
