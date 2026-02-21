"""Page 7: Lateral load analysis — p-y curves, deflection, moment profiles."""

import sys
from pathlib import Path

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType, build_soil_layer_from_dict
from core.sections import get_section
from core.lateral import solve_lateral, broms_cohesionless, broms_cohesive, generate_py_curve, minimum_embedment_broms

st.header("Lateral Load Analysis")

# Check prerequisites
if not st.session_state.get("soil_layers"):
    st.warning("Define soil layers on the Soil Profile page first.")
    st.stop()

# --- Build profile ---
layers_obj = [build_soil_layer_from_dict(ld) for ld in st.session_state.soil_layers]
profile = SoilProfile(layers=layers_obj, water_table_depth=st.session_state.water_table_depth)

# --- Pile prerequisites ---
pile_section_name = st.session_state.get("pile_section", None)
if not pile_section_name:
    st.warning("Select a pile section on the **Pile Properties** page first.")
    st.stop()

# --- Pile ---
section = st.session_state.get("section") or get_section(pile_section_name)
embedment = st.session_state.get("pile_embedment", 10.0)
axis = st.session_state.get("bending_axis", "strong")
EI = section.EI_strong if axis == "strong" else section.EI_weak
My = section.My_strong if axis == "strong" else section.My_weak
B = section.depth if axis == "strong" else section.width

# --- Load inputs ---
col1, col2, col3 = st.columns(3)
with col1:
    H_applied = st.number_input(
        "Lateral load H (lbs)", min_value=0.0,
        value=st.session_state.get("wind_lateral", 1500.0), step=100.0, format="%.0f",
    )
    if H_applied is None:
        H_applied = 0.0
with col2:
    M_applied = st.number_input(
        "Moment at ground (ft-lbs)", min_value=0.0,
        value=H_applied * st.session_state.get("lever_arm", 4.0), step=500.0, format="%.0f",
    )
    if M_applied is None:
        M_applied = 0.0
with col3:
    st.session_state.cyclic_loading = st.checkbox(
        "Cyclic loading (wind)", value=st.session_state.get("cyclic_loading", False),
    )

st.markdown("---")

# --- Run FDM Analysis ---
if st.button("Run Lateral Analysis (FDM)", type="primary"):
    with st.spinner("Solving nonlinear p-y analysis..."):
        result = solve_lateral(
            profile=profile,
            pile_width=B,
            EI=EI,
            embedment=embedment,
            H=H_applied,
            M_ground=M_applied,
            head_condition=st.session_state.head_condition,
            cyclic=st.session_state.cyclic_loading,
            n_elements=100,
        )
    st.session_state["lateral_result"] = result

# --- Display results ---
if "lateral_result" in st.session_state:
    result = st.session_state["lateral_result"]

    # Key metrics
    st.subheader("Key Results")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ground Deflection", f"{result.y_ground:.3f} in")
    c2.metric("Max Moment", f"{result.M_max:,.0f} ft-lbs")
    c3.metric("Depth of M_max", f"{result.depth_M_max:.1f} ft")
    c4.metric("Depth of Zero Deflection", f"{result.depth_zero_defl:.1f} ft")

    # Convergence
    if result.converged:
        st.success(f"Converged in {result.iterations} iterations")
    else:
        st.warning(f"Did not converge after {result.iterations} iterations")

    # Structural check
    My_ft_lbs = My * 1000 / 12  # kip-in -> ft-lbs
    dcr = abs(result.M_max) / My_ft_lbs if My_ft_lbs > 0 else 999
    if dcr <= 1.0:
        st.success(f"Structural DCR = {dcr:.2f} (M_max / M_y = {abs(result.M_max):,.0f} / {My_ft_lbs:,.0f} ft-lbs) -- OK")
    else:
        st.error(f"Structural DCR = {dcr:.2f} -- EXCEEDS YIELD MOMENT")

    st.markdown("---")

    # --- Depth profile plots ---
    st.subheader("Depth Profiles")

    fig = make_subplots(
        rows=1, cols=4,
        subplot_titles=("Deflection (in)", "Moment (ft-lbs)", "Shear (lbs)", "Soil Reaction (lb/in)"),
        shared_yaxes=True,
    )

    depth = -result.depth_ft

    fig.add_trace(go.Scatter(
        x=result.deflection_in, y=depth, mode="lines", name="Deflection",
        line=dict(color="blue", width=2),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=result.moment_ft_lbs, y=depth, mode="lines", name="Moment",
        line=dict(color="red", width=2),
    ), row=1, col=2)

    fig.add_trace(go.Scatter(
        x=result.shear_lbs, y=depth, mode="lines", name="Shear",
        line=dict(color="green", width=2),
    ), row=1, col=3)

    fig.add_trace(go.Scatter(
        x=result.soil_reaction_lb_in, y=depth, mode="lines", name="Soil p",
        line=dict(color="orange", width=2),
    ), row=1, col=4)

    fig.update_layout(
        height=550,
        showlegend=False,
        title_text="Pile Response vs Depth",
    )
    for i in range(1, 5):
        fig.update_yaxes(title_text="Depth (ft)" if i == 1 else "", row=1, col=i)

    st.plotly_chart(fig, width="stretch")

    # --- p-y Curves ---
    st.subheader("p-y Curves at Selected Depths")

    if result.py_curves:
        fig_py = go.Figure()
        colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
        for i, py in enumerate(result.py_curves):
            color = colors[i % len(colors)]
            fig_py.add_trace(go.Scatter(
                x=py.y, y=py.p,
                mode="lines",
                name=f"z = {py.depth_ft:.0f} ft ({py.method})",
                line=dict(color=color, width=2),
            ))

        fig_py.update_layout(
            title="p-y Curves",
            xaxis_title="Deflection y (in)",
            yaxis_title="Soil Resistance p (lb/in)",
            height=450,
        )
        st.plotly_chart(fig_py, width="stretch")

    # Notes
    if result.notes:
        st.markdown("### Analysis Notes")
        for note in result.notes:
            st.markdown(f"- {note}")

st.markdown("---")

# --- Broms Simplified Check ---
st.subheader("Broms Simplified Lateral Capacity Check")

if st.button("Run Broms Analysis"):
    # Use top layer properties
    top_layer = layers_obj[0]
    is_cohesive = top_layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC)
    e_ft = st.session_state.lever_arm

    if is_cohesive:
        c_u = top_layer.get_cu()
        broms_result = broms_cohesive(
            c_u=c_u, B=B, L=embedment, e=e_ft, EI=EI, My=My,
        )
    else:
        phi = top_layer.get_phi()
        gamma = top_layer.gamma_effective
        broms_result = broms_cohesive(
            c_u=0, B=B, L=embedment, e=e_ft, EI=EI, My=My,
        ) if is_cohesive else broms_cohesionless(
            phi=phi, gamma=gamma, B=B, L=embedment, e=e_ft, EI=EI, My=My,
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("H_ult (Broms)", f"{broms_result.H_ult:,.0f} lbs")
    c2.metric("H_allow (Broms)", f"{broms_result.H_allow:,.0f} lbs")
    c3.metric("Failure Mode", broms_result.failure_mode)

    for note in broms_result.notes:
        st.markdown(f"- {note}")

# ============================================================================
# Service Load Deflection Check
# ============================================================================
st.markdown("---")
st.subheader("Service Load Deflection Check")
st.caption(
    "Unfactored (ASD-level) lateral load to verify pile head deflection stays "
    "within an acceptable limit. Default applies 0.6 wind factor per ASCE 7 ASD."
)

svc_c1, svc_c2, svc_c3 = st.columns(3)
with svc_c1:
    wind_asd_factor = st.number_input(
        "Wind ASD factor", min_value=0.1, max_value=1.0,
        value=0.6, step=0.05, format="%.2f",
        help="Service-level factor on wind lateral load (0.6 for ASD wind).",
    )
with svc_c2:
    svc_H = st.number_input(
        "Service lateral load (lbs)",
        min_value=0.0,
        value=round(st.session_state.get("wind_lateral", 1500.0) * 0.6, 0),
        step=50.0, format="%.0f",
    )
with svc_c3:
    defl_limit = st.number_input(
        "Deflection limit (in)",
        min_value=0.05, max_value=5.0, step=0.05, format="%.2f",
        key="service_defl_limit",
        help="Maximum allowable ground-line deflection under service loads.",
    )

if st.button("Check Service Deflection", key="btn_svc_defl"):
    _svc_H = svc_H if svc_H is not None else 0.0
    svc_M = _svc_H * st.session_state.get("lever_arm", 4.0)
    with st.spinner("Running service-level lateral analysis..."):
        svc_result = solve_lateral(
            profile=profile,
            pile_width=B,
            EI=EI,
            embedment=embedment,
            H=_svc_H,
            M_ground=svc_M,
            head_condition=st.session_state.get("head_condition", "free"),
            cyclic=False,  # service loads are not cyclic-degraded
            n_elements=100,
        )
    st.session_state["service_defl_result"] = svc_result

if "service_defl_result" in st.session_state:
    svc_r = st.session_state["service_defl_result"]
    # Read from session state key in case the widget returned None (cleared field)
    _defl_limit = st.session_state.get("service_defl_limit", None)
    if _defl_limit is None or not isinstance(_defl_limit, (int, float)):
        _defl_limit = 0.50
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Service Deflection", f"{svc_r.y_ground:.3f} in")
    sc2.metric("Limit", f"{_defl_limit:.2f} in")
    margin = _defl_limit - abs(svc_r.y_ground)
    sc3.metric("Margin", f"{margin:.3f} in")

    if abs(svc_r.y_ground) <= _defl_limit:
        st.success(
            f"PASS -- Service deflection {abs(svc_r.y_ground):.3f} in <= "
            f"limit {_defl_limit:.2f} in"
        )
    else:
        st.error(
            f"FAIL -- Service deflection {abs(svc_r.y_ground):.3f} in > "
            f"limit {_defl_limit:.2f} in"
        )

# ============================================================================
# Minimum Embedment for Lateral Stability
# ============================================================================
st.markdown("---")
st.subheader("Minimum Embedment for Lateral Stability")
st.caption(
    "Broms-based bisection: finds the shortest embedment where ultimate lateral "
    "capacity meets the required demand."
)

me_c1, me_c2 = st.columns(2)
with me_c1:
    FS_lateral = st.number_input(
        "Factor of safety for lateral",
        min_value=1.0, max_value=5.0, value=2.0, step=0.5, format="%.1f",
        help="H_required = H_applied * FS",
    )
    if FS_lateral is None:
        FS_lateral = 2.0
with me_c2:
    H_req = st.number_input(
        "H required (lbs)",
        value=round(st.session_state.get("wind_lateral", 1500.0) * FS_lateral, 0),
        step=100.0, format="%.0f",
        help="Lateral capacity that must be achieved (default = H * FS).",
    )

if st.button("Find Minimum Embedment", key="btn_min_embed"):
    e_arm = st.session_state.get("lever_arm", 4.0)
    min_embed = minimum_embedment_broms(
        profile=profile,
        B=B,
        EI=EI,
        My=My,
        H_required=H_req if H_req is not None else 0.0,
        e=e_arm,
    )
    st.session_state["min_embed_result"] = min_embed

if "min_embed_result" in st.session_state:
    me_r = st.session_state["min_embed_result"]

    if me_r.get("L_min_ft") is not None:
        me1, me2, me3 = st.columns(3)
        me1.metric("Min Embedment", f"{me_r['L_min_ft']:.1f} ft")
        me2.metric("H_ult at L_min", f"{me_r['H_ult_at_L_min']:,.0f} lbs")
        me3.metric("Failure Mode", me_r["failure_mode"])

        embed_margin = embedment - me_r["L_min_ft"]
        if embed_margin >= 0:
            st.success(
                f"PASS — Current embedment {embedment:.1f} ft >= "
                f"minimum required {me_r['L_min_ft']:.1f} ft "
                f"(margin = {embed_margin:.1f} ft)"
            )
        else:
            st.error(
                f"FAIL — Current embedment {embedment:.1f} ft < "
                f"minimum required {me_r['L_min_ft']:.1f} ft "
                f"(shortfall = {abs(embed_margin):.1f} ft)"
            )
    else:
        st.error("Could not find a sufficient embedment within the search range.")

    for note in me_r.get("notes", []):
        st.caption(note)
