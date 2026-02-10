"""Page 8: BNWF Finite Element Analysis — combined axial+lateral, pushover, stiffness matrix."""

import sys
from pathlib import Path

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType
from core.sections import get_section
from core.bnwf import run_bnwf_analysis, BNWFLoadInput, BNWFOptions

st.header("FEM Analysis (BNWF)")
st.caption("Beam on Nonlinear Winkler Foundation — combined axial + lateral loading")

# Check prerequisites
if not st.session_state.get("soil_layers"):
    st.warning("Define soil layers on the Soil Profile page first.")
    st.stop()

# --- Build soil profile ---
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

# --- Analysis configuration ---
st.subheader("Analysis Configuration")

col_type, col_solver = st.columns(2)
with col_type:
    analysis_type = st.selectbox(
        "Analysis type",
        ["static", "pushover_lateral", "pushover_axial"],
        format_func=lambda x: {"static": "Static", "pushover_lateral": "Pushover (Lateral)",
                                "pushover_axial": "Pushover (Axial)"}[x],
    )
with col_solver:
    solver_choice = st.selectbox(
        "Solver",
        ["auto", "python", "opensees"],
        format_func=lambda x: {"auto": "Auto (best available)", "python": "Python (always available)",
                                "opensees": "OpenSeesPy (if installed)"}[x],
    )

# --- Load inputs ---
st.subheader("Applied Loads")
c1, c2, c3 = st.columns(3)
with c1:
    V_axial = st.number_input(
        "Axial load V (lbs, + compression)",
        value=st.session_state.get("axial_compression", 5000.0), step=500.0, format="%.0f",
    )
with c2:
    H_lateral = st.number_input(
        "Lateral load H (lbs)",
        min_value=0.0,
        value=st.session_state.get("wind_lateral", 1500.0), step=100.0, format="%.0f",
    )
with c3:
    M_ground = st.number_input(
        "Moment at ground M (ft-lbs)",
        min_value=0.0,
        value=H_lateral * st.session_state.get("lever_arm", 4.0), step=500.0, format="%.0f",
    )

# --- Options ---
st.subheader("Options")
opt1, opt2, opt3, opt4 = st.columns(4)
with opt1:
    include_p_delta = st.checkbox("Include P-delta effects", value=True)
with opt2:
    cyclic = st.checkbox("Cyclic loading", value=st.session_state.get("cyclic_loading", False))
with opt3:
    pile_type = st.selectbox("Pile type", ["driven", "drilled", "helical"])
with opt4:
    head_cond = st.selectbox("Head condition", ["free", "fixed"])

# Pushover options (conditional)
pushover_steps = 20
pushover_max_mult = 3.0
if analysis_type.startswith("pushover"):
    st.markdown("**Pushover Settings**")
    pc1, pc2 = st.columns(2)
    with pc1:
        pushover_steps = st.number_input("Number of load steps", min_value=5, max_value=100, value=20)
    with pc2:
        pushover_max_mult = st.number_input("Max load multiplier", min_value=1.0, max_value=10.0, value=3.0, step=0.5, format="%.1f")

# OpenSees-only options
use_fiber = False
run_eigen = False
n_modes = 3
if solver_choice in ("auto", "opensees"):
    st.markdown("**Advanced (OpenSeesPy only)**")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        use_fiber = st.checkbox("Fiber section (nonlinear M-phi)", value=False)
    with ac2:
        run_eigen = st.checkbox("Eigenvalue analysis", value=False)
    with ac3:
        if run_eigen:
            n_modes = st.number_input("Number of modes", min_value=1, max_value=10, value=3)

st.markdown("---")

# --- Run Analysis ---
if st.button("Run BNWF Analysis", type="primary"):
    loads = BNWFLoadInput(
        V_axial=V_axial,
        H_lateral=H_lateral,
        M_ground=M_ground,
        load_type=analysis_type,
        pushover_steps=pushover_steps,
        pushover_max_mult=pushover_max_mult,
    )
    options = BNWFOptions(
        n_elements=50,
        bending_axis=axis,
        head_condition=head_cond,
        cyclic=cyclic,
        include_p_delta=include_p_delta,
        solver=solver_choice,
        use_fiber_section=use_fiber,
        run_eigenvalue=run_eigen,
        n_modes=n_modes,
        pile_type=pile_type,
    )

    with st.spinner("Running BNWF finite element analysis..."):
        result = run_bnwf_analysis(profile, section, embedment, loads, options)
    st.session_state["bnwf_result"] = result

# --- Display Results ---
if "bnwf_result" in st.session_state:
    result = st.session_state["bnwf_result"]

    # Solver banner
    st.info(f"Solver: **{result.solver_used}** | Analysis: **{result.analysis_type}**")

    # Convergence
    if result.converged:
        st.success(f"Converged in {result.iterations} iterations")
    else:
        st.warning(f"Did not converge after {result.iterations} iterations")

    # Key metrics
    st.subheader("Key Results")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Lateral Defl. (ground)", f"{result.y_ground_lateral:.3f} in")
    m2.metric("Axial Defl. (ground)", f"{result.y_ground_axial:.4f} in")
    m3.metric("Max Moment", f"{result.M_max:,.0f} ft-lbs")
    m4.metric("Depth of M_max", f"{result.depth_M_max:.1f} ft")
    if result.P_critical is not None:
        m5.metric("P_critical (buckling)", f"{result.P_critical:,.0f} lbs")
    else:
        m5.metric("Tip Reaction", f"{result.soil_reaction_q_lbs:,.0f} lbs")

    st.markdown("---")

    # --- Pile Head Stiffness Matrix ---
    st.subheader("Pile Head Stiffness Matrix")
    K = result.K_head
    labels = ["Axial (lb/in)", "Lateral (lb/in)", "Rotational (ft-lb/rad)"]
    st.markdown("| | " + " | ".join(labels) + " |")
    st.markdown("|---|---|---|---|")
    for i, row_label in enumerate(labels):
        vals = " | ".join(f"{K[i, j]:,.1f}" for j in range(3))
        st.markdown(f"| **{row_label}** | {vals} |")

    st.markdown("---")

    # --- Depth Profile Plots ---
    st.subheader("Depth Profiles")

    depth = -result.depth_ft  # negative for plotting (depth below ground)

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=(
            "Lateral Deflection (in)", "Axial Deflection (in)", "Moment (ft-lbs)",
            "Shear (lbs)", "Axial Force (lbs)", "Lateral Soil Reaction (lb/in)",
        ),
        shared_yaxes=True,
        vertical_spacing=0.12,
    )

    traces = [
        (result.deflection_lateral_in, "Lateral Defl.", "blue", 1, 1),
        (result.deflection_axial_in, "Axial Defl.", "purple", 1, 2),
        (result.moment_ft_lbs, "Moment", "red", 1, 3),
        (result.shear_lbs, "Shear", "green", 2, 1),
        (result.axial_force_lbs, "Axial Force", "brown", 2, 2),
        (result.soil_reaction_p_lb_in, "Soil p", "orange", 2, 3),
    ]

    for x_data, name, color, row, col in traces:
        fig.add_trace(go.Scatter(
            x=x_data, y=depth, mode="lines", name=name,
            line=dict(color=color, width=2),
        ), row=row, col=col)

    fig.update_layout(height=800, showlegend=False, title_text="Pile Response vs Depth")
    for r in range(1, 3):
        fig.update_yaxes(title_text="Depth (ft)", row=r, col=1)

    st.plotly_chart(fig, width="stretch")

    # --- Pushover Curve ---
    if result.pushover_load is not None and result.pushover_disp is not None:
        st.subheader(f"Pushover Curve ({result.pushover_axis})")

        fig_po = go.Figure()
        fig_po.add_trace(go.Scatter(
            x=result.pushover_disp, y=result.pushover_load,
            mode="lines+markers", name="Pushover",
            line=dict(color="red", width=2),
            marker=dict(size=4),
        ))
        axis_label = "Lateral" if result.pushover_axis == "lateral" else "Axial"
        fig_po.update_layout(
            xaxis_title=f"{axis_label} Displacement at Ground (in)",
            yaxis_title=f"{axis_label} Load (lbs)",
            height=400,
        )
        st.plotly_chart(fig_po, width="stretch")

    # --- Eigenvalue Results ---
    if result.frequencies_hz:
        st.subheader("Natural Frequencies")
        for i, f_hz in enumerate(result.frequencies_hz):
            st.write(f"Mode {i + 1}: **{f_hz:.2f} Hz** (T = {1.0 / f_hz:.3f} s)" if f_hz > 0
                     else f"Mode {i + 1}: —")

    # --- t-z Curves ---
    if result.tz_curves:
        st.subheader("t-z Curves at Selected Depths")
        fig_tz = go.Figure()
        colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
        for i, tz in enumerate(result.tz_curves):
            fig_tz.add_trace(go.Scatter(
                x=tz.z, y=tz.t, mode="lines",
                name=f"z = {tz.depth_ft:.0f} ft ({tz.method})",
                line=dict(color=colors[i % len(colors)], width=2),
            ))
        fig_tz.update_layout(
            title="t-z Curves (Skin Friction Transfer)",
            xaxis_title="Axial Displacement z (in)",
            yaxis_title="Skin Friction t (lb/in)",
            height=400,
        )
        st.plotly_chart(fig_tz, width="stretch")

    # --- q-z Curve ---
    if result.qz_curve:
        st.subheader("q-z Curve at Pile Tip")
        fig_qz = go.Figure()
        fig_qz.add_trace(go.Scatter(
            x=result.qz_curve.z, y=result.qz_curve.q,
            mode="lines", name=result.qz_curve.method,
            line=dict(color="#2c3e50", width=2),
        ))
        fig_qz.update_layout(
            title=f"q-z Curve ({result.qz_curve.method}) — q_ult = {result.qz_curve.q_ult:,.0f} lbs",
            xaxis_title="Tip Displacement z (in)",
            yaxis_title="Tip Resistance q (lbs)",
            height=400,
        )
        st.plotly_chart(fig_qz, width="stretch")

    # --- p-y Curves ---
    if result.py_curves:
        st.subheader("p-y Curves at Selected Depths")
        fig_py = go.Figure()
        colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
        for i, py in enumerate(result.py_curves):
            fig_py.add_trace(go.Scatter(
                x=py.y, y=py.p, mode="lines",
                name=f"z = {py.depth_ft:.0f} ft ({py.method})",
                line=dict(color=colors[i % len(colors)], width=2),
            ))
        fig_py.update_layout(
            title="p-y Curves (Lateral Soil Resistance)",
            xaxis_title="Lateral Deflection y (in)",
            yaxis_title="Soil Resistance p (lb/in)",
            height=400,
        )
        st.plotly_chart(fig_py, width="stretch")

    # --- Notes ---
    if result.notes:
        st.markdown("### Analysis Notes")
        for note in result.notes:
            st.markdown(f"- {note}")
