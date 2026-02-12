"""Page 11: AISC 360 structural capacity check — combined axial + bending."""

import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.sections import get_section
from core.structural import aisc_h1_check
from core.lateral import depth_of_fixity

st.header("AISC 360 Structural Capacity Check")

# --- Prerequisites ---
section = st.session_state.get("section") or get_section(st.session_state.pile_section)

st.subheader("Unbraced Length & Buckling Parameters")
col1, col2, col3 = st.columns(3)

with col1:
    above_grade = st.number_input(
        "Above-grade height (ft)",
        min_value=0.0, max_value=30.0, step=0.25, format="%.2f",
        key="above_grade",
        help="Height of lateral load application above ground surface.",
    )

with col2:
    K_factor = st.number_input(
        "Effective length factor K",
        min_value=0.5, max_value=4.0, step=0.1, format="%.1f",
        key="K_factor",
        help="2.1 = cantilever with partial fixity (typical for piles). 2.0 = ideal cantilever.",
    )

# Compute depth of fixity from top soil layer
D_f = 5.0  # default
if st.session_state.get("soil_layers"):
    from core.soil import SoilLayer, SoilType, build_soil_layer_from_dict
    top = st.session_state.soil_layers[0]
    soil_type_val = top.get("soil_type", "Sand")
    if isinstance(soil_type_val, str):
        is_sand = soil_type_val in ("Sand", "Gravel", "Silt")
    else:
        is_sand = soil_type_val in (SoilType.SAND, SoilType.GRAVEL, SoilType.SILT)

    axis = st.session_state.get("bending_axis", "strong")
    EI = section.EI_strong if axis == "strong" else section.EI_weak
    layer_obj = build_soil_layer_from_dict(top)
    if is_sand:
        k_h = layer_obj.get_k_h()
        D_f = depth_of_fixity(EI, "sand", n_h=k_h)
    else:
        k_h = layer_obj.get_k_h()
        D_f = depth_of_fixity(EI, "clay", k_h=k_h)

L_b = above_grade + D_f

with col3:
    st.metric("Depth of Fixity (D_f)", f"{D_f:.2f} ft")
    st.metric("Unbraced Length (L_b)", f"{L_b:.2f} ft")

st.markdown("---")

# --- Load Source ---
st.subheader("Applied Loads")

load_source = st.radio(
    "Load source",
    ["From analysis results", "Manual entry"],
    horizontal=True,
)

if load_source == "From analysis results":
    # Auto-populate from lateral and load combination results
    lateral_result = st.session_state.get("lateral_result")
    M_ux_default = 0.0
    if lateral_result:
        M_ux_default = abs(lateral_result.M_max) * 12.0 / 1000.0  # ft-lbs -> kip-in
        st.caption(f"M_max from lateral analysis: {lateral_result.M_max:,.0f} ft-lbs = {M_ux_default:.1f} kip-in")
    else:
        st.warning("Run lateral analysis first, or use manual entry.")

    # Get governing compression from load cases
    P_u_default = st.session_state.get("dead_load", 400.0) * 1.4  # LC1 estimate
    lc_cases = st.session_state.get("lrfd_cases")
    if lc_cases:
        P_u_default = max(lc.V_comp for lc in lc_cases)

    col_p, col_mx, col_my = st.columns(3)
    with col_p:
        P_u = st.number_input("P_u — Factored axial (lbs)", value=round(P_u_default, 0),
                              step=100.0, format="%.0f")
    with col_mx:
        M_ux = st.number_input("M_ux — Strong-axis moment (kip-in)", value=round(M_ux_default, 1),
                               step=1.0, format="%.1f")
    with col_my:
        M_uy = st.number_input("M_uy — Weak-axis moment (kip-in)", value=0.0,
                               step=1.0, format="%.1f")
else:
    col_p, col_mx, col_my = st.columns(3)
    with col_p:
        P_u = st.number_input("P_u — Factored axial (lbs)", value=5000.0,
                              step=100.0, format="%.0f")
    with col_mx:
        M_ux = st.number_input("M_ux — Strong-axis moment (kip-in)", value=10.0,
                               step=1.0, format="%.1f")
    with col_my:
        M_uy = st.number_input("M_uy — Weak-axis moment (kip-in)", value=0.0,
                               step=1.0, format="%.1f")

st.markdown("---")

# --- Run Check ---
if st.button("Run AISC H1-1 Check", type="primary"):
    result = aisc_h1_check(
        section=section,
        P_u_lbs=P_u,
        M_ux_kip_in=M_ux,
        M_uy_kip_in=M_uy,
        L_b_ft=L_b,
        K=K_factor,
        D_f_ft=D_f,
    )
    st.session_state["structural_result"] = result

if "structural_result" in st.session_state:
    result = st.session_state["structural_result"]

    # Pass/fail banner
    if result.passes:
        st.success(f"PASS — Unity Ratio = {result.unity_ratio:.3f} (Eq. {result.equation_used})")
    else:
        st.error(f"FAIL — Unity Ratio = {result.unity_ratio:.3f} (Eq. {result.equation_used})")

    # Key metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unity Ratio", f"{result.unity_ratio:.3f}")
    c2.metric("Equation", result.equation_used)
    c3.metric("P_u / phi*P_n", f"{result.axial_ratio:.3f}")
    c4.metric("KL/r", f"{result.KL_r:.0f}")

    # Detailed breakdown
    with st.expander("Detailed Breakdown", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Compression (AISC Ch. E)**")
            st.write(f"- F_y = {section.fy:.1f} ksi")
            st.write(f"- F_cr = {result.F_cr_ksi:.2f} ksi")
            st.write(f"- A_g = {section.area:.2f} in^2")
            st.write(f"- P_n = {result.P_n:,.0f} lbs")
            st.write(f"- phi_c * P_n = {result.phi_c_Pn:,.0f} lbs")
            st.write(f"- r_x = {result.r_x:.3f} in, r_y = {result.r_y:.3f} in")
        with col_b:
            st.markdown("**Flexure (AISC Ch. F)**")
            st.write(f"- M_nx (Zx*Fy) = {result.M_nx:.1f} kip-in")
            st.write(f"- M_ny (Zy*Fy) = {result.M_ny:.1f} kip-in")
            st.write(f"- phi_b * M_nx = {result.phi_b_Mnx:.1f} kip-in")
            st.write(f"- phi_b * M_ny = {result.phi_b_Mny:.1f} kip-in")
            st.write(f"- D_f = {result.D_f_ft:.2f} ft")
            st.write(f"- L_b = {result.L_b_ft:.2f} ft")

    # Notes
    if result.notes:
        for n in result.notes:
            st.warning(n)

    # --- Interaction Diagram ---
    st.subheader("Interaction Diagram")

    # Build H1-1 envelope
    p_ratios = np.linspace(0, 1.0, 100)
    m_ratios_1a = []  # H1-1a (P/Pn >= 0.2)
    m_ratios_1b = []  # H1-1b (P/Pn < 0.2)
    for pr in p_ratios:
        if pr >= 0.2:
            m_ratios_1a.append((1.0 - pr) * 9.0 / 8.0)
            m_ratios_1b.append(None)
        else:
            m_ratios_1b.append(1.0 - pr / 2.0)
            m_ratios_1a.append(None)

    fig = go.Figure()
    # H1-1a envelope
    fig.add_trace(go.Scatter(
        x=[m for m in m_ratios_1a if m is not None],
        y=[p for p, m in zip(p_ratios, m_ratios_1a) if m is not None],
        mode="lines", name="H1-1a", line=dict(color="blue", width=2),
    ))
    # H1-1b envelope
    fig.add_trace(go.Scatter(
        x=[m for m in m_ratios_1b if m is not None],
        y=[p for p, m in zip(p_ratios, m_ratios_1b) if m is not None],
        mode="lines", name="H1-1b", line=dict(color="blue", width=2, dash="dash"),
    ))

    # Demand point
    m_demand = abs(result.M_ux) / result.phi_b_Mnx if result.phi_b_Mnx > 0 else 0
    p_demand = result.axial_ratio
    fig.add_trace(go.Scatter(
        x=[m_demand], y=[p_demand],
        mode="markers", name="Demand",
        marker=dict(size=14, color="red" if not result.passes else "green", symbol="x"),
    ))

    fig.update_layout(
        xaxis_title="M_u / (phi_b * M_n)",
        yaxis_title="P_u / (phi_c * P_n)",
        xaxis=dict(range=[0, 1.3]),
        yaxis=dict(range=[0, 1.1]),
        height=450,
        showlegend=True,
    )
    st.plotly_chart(fig, width="stretch")
