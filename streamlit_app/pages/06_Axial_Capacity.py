"""Page 6: Axial capacity analysis results."""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType, build_soil_layer_from_dict
from core.sections import get_section
from core.axial import axial_capacity

st.header("Axial Capacity Analysis")

# Check prerequisites
if not st.session_state.get("soil_layers"):
    st.warning("Define soil layers on the Soil Profile page first.")
    st.stop()

# --- Pile prerequisites ---
pile_section_name = st.session_state.get("pile_section", None)
if not pile_section_name:
    st.warning("Select a pile section on the **Pile Properties** page first.")
    st.stop()

# --- Build profile ---
layers_obj = [build_soil_layer_from_dict(ld) for ld in st.session_state.soil_layers]
profile = SoilProfile(layers=layers_obj, water_table_depth=st.session_state.water_table_depth)

# --- Pile properties ---
section = st.session_state.get("section") or get_section(pile_section_name)
embedment = st.session_state.get("pile_embedment", 10.0)

# --- Analysis settings ---
col1, col2, col3 = st.columns(3)
with col1:
    st.session_state.axial_method = st.selectbox(
        "Capacity Method",
        ["auto", "alpha", "beta", "meyerhof"],
        index=["auto", "alpha", "beta", "meyerhof"].index(
            st.session_state.get("axial_method", "auto")
        ),
    )
with col2:
    st.session_state.FS_compression = st.number_input(
        "FS Compression", value=st.session_state.get("FS_compression", 2.5), step=0.5, format="%.1f",
    )
    if st.session_state.FS_compression is None:
        st.session_state.FS_compression = 2.5
with col3:
    st.session_state.FS_tension = st.number_input(
        "FS Tension", value=st.session_state.get("FS_tension", 3.0), step=0.5, format="%.1f",
    )
    if st.session_state.FS_tension is None:
        st.session_state.FS_tension = 3.0

# --- Run analysis ---
if st.button("Run Axial Analysis", type="primary"):
    result = axial_capacity(
        profile=profile,
        pile_perimeter=section.perimeter,
        pile_tip_area=section.tip_area,
        embedment_depth=embedment,
        method=st.session_state.axial_method,
        pile_type=st.session_state.pile_type,
        FS_compression=st.session_state.FS_compression,
        FS_tension=st.session_state.FS_tension,
    )

    st.session_state["axial_result"] = result

# Display results if available
if "axial_result" in st.session_state:
    result = st.session_state["axial_result"]

    st.markdown("---")
    st.subheader("Results Summary")

    # Capacity metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Q_s (Skin Friction)", f"{result.Q_s:,.0f} lbs")
    c2.metric("Q_b (End Bearing)", f"{result.Q_b:,.0f} lbs")
    c3.metric("Q_ult (Compression)", f"{result.Q_ult_compression:,.0f} lbs")

    c4, c5, c6 = st.columns(3)
    c4.metric("Q_allow (Comp, ASD)", f"{result.Q_allow_compression:,.0f} lbs")
    c5.metric("Q_ult (Tension)", f"{result.Q_ult_tension:,.0f} lbs")
    c6.metric("Q_allow (Tens, ASD)", f"{result.Q_allow_tension:,.0f} lbs")

    st.markdown("### LRFD Factored Resistance")
    c7, c8 = st.columns(2)
    c7.metric(
        f"phi*R_n Compression (phi={result.phi_compression})",
        f"{result.Q_r_compression:,.0f} lbs",
    )
    c8.metric(
        f"phi*R_n Tension (phi={result.phi_tension})",
        f"{result.Q_r_tension:,.0f} lbs",
    )

    # Layer breakdown
    st.markdown("---")
    st.subheader("Layer-by-Layer Breakdown")
    if result.layer_contributions:
        df = pd.DataFrame(result.layer_contributions)
        st.dataframe(df, width="stretch", hide_index=True)

    # Cumulative capacity plot
    st.subheader("Cumulative Skin Friction vs Depth")
    if result.layer_contributions:
        depths = [lc["depth_ft"] for lc in result.layer_contributions]
        dQ_vals = [lc["dQ_lbs"] for lc in result.layer_contributions]

        cumulative = []
        running = 0
        for dq in dQ_vals:
            running += dq
            cumulative.append(running)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cumulative,
            y=[-d for d in depths],
            mode="lines+markers",
            name="Cumulative Q_s",
            line=dict(color="green", width=2),
        ))
        fig.add_hline(y=0, line=dict(color="brown", width=2), annotation_text="Ground")
        fig.update_layout(
            title="Cumulative Skin Friction vs Depth",
            xaxis_title="Cumulative Q_s (lbs)",
            yaxis_title="Depth (ft)",
            height=450,
        )
        st.plotly_chart(fig, width="stretch")

    # Capacity bar chart
    st.subheader("Capacity Summary")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=["Compression\n(Ultimate)", "Compression\n(Allowable)", "Compression\n(LRFD phi*Rn)",
           "Tension\n(Ultimate)", "Tension\n(Allowable)", "Tension\n(LRFD phi*Rn)"],
        y=[result.Q_ult_compression, result.Q_allow_compression, result.Q_r_compression,
           result.Q_ult_tension, result.Q_allow_tension, result.Q_r_tension],
        marker_color=["#2ecc71", "#27ae60", "#1abc9c", "#e74c3c", "#c0392b", "#e67e22"],
    ))
    fig2.update_layout(
        title="Axial Capacity Summary",
        yaxis_title="Capacity (lbs)",
        height=400,
    )
    st.plotly_chart(fig2, width="stretch")

    # Notes
    st.markdown("### Analysis Notes")
    for note in result.notes:
        st.markdown(f"- {note}")
