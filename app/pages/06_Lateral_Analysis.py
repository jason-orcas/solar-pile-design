"""Page 6: Lateral load analysis — p-y curves, deflection, moment profiles."""

import sys
from pathlib import Path

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType
from core.sections import get_section
from core.lateral import solve_lateral, broms_cohesionless, broms_cohesive, generate_py_curve

st.header("Lateral Load Analysis")

# Check prerequisites
if not st.session_state.get("soil_layers"):
    st.warning("Define soil layers on the Soil Profile page first.")
    st.stop()

# --- Build profile ---
layers_obj = []
for ld in st.session_state.soil_layers:
    layers_obj.append(SoilLayer(
        top_depth=ld["top_depth"],
        thickness=ld["thickness"],
        soil_type=SoilType(ld["soil_type"]),
        description=ld.get("description", ""),
        N_spt=ld.get("N_spt"),
        gamma=ld.get("gamma"),
        phi=ld.get("phi"),
        c_u=ld.get("c_u"),
    ))
profile = SoilProfile(layers=layers_obj, water_table_depth=st.session_state.water_table_depth)

# --- Pile ---
section = get_section(st.session_state.pile_section)
embedment = st.session_state.pile_embedment
axis = st.session_state.bending_axis
EI = section.EI_strong if axis == "strong" else section.EI_weak
My = section.My_strong if axis == "strong" else section.My_weak
B = section.depth if axis == "strong" else section.width

# --- Load inputs ---
col1, col2, col3 = st.columns(3)
with col1:
    H_applied = st.number_input(
        "Lateral load H (lbs)", min_value=0.0,
        value=st.session_state.get("wind_lateral", 1500.0), step=100.0,
    )
with col2:
    M_applied = st.number_input(
        "Moment at ground (ft-lbs)", min_value=0.0,
        value=H_applied * st.session_state.get("lever_arm", 4.0), step=500.0,
    )
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

    st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig_py, use_container_width=True)

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
