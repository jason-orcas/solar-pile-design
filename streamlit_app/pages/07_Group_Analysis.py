"""Page 7: Pile group analysis — efficiency, p-multipliers, block failure."""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType
from core.sections import get_section
from core.group import group_analysis, converse_labarre, p_multipliers_table

st.header("Pile Group Analysis")

# Check prerequisites
if not st.session_state.get("soil_layers"):
    st.warning("Define soil layers on the Soil Profile page first.")
    st.stop()

section = st.session_state.get("section") or get_section(st.session_state.pile_section)
embedment = st.session_state.pile_embedment
pile_width = section.depth  # Use depth as governing dimension

# --- Group geometry ---
st.subheader("Group Configuration")
col1, col2, col3 = st.columns(3)

with col1:
    st.session_state.group_n_rows = st.number_input(
        "Number of rows", min_value=1, max_value=10,
        value=st.session_state.get("group_n_rows", 1), step=1,
    )
with col2:
    st.session_state.group_n_cols = st.number_input(
        "Piles per row", min_value=1, max_value=10,
        value=st.session_state.get("group_n_cols", 1), step=1,
    )
with col3:
    st.session_state.group_spacing = st.number_input(
        "Center-to-center spacing (in)", min_value=6.0,
        value=st.session_state.get("group_spacing", 36.0), step=3.0, format="%.0f",
    )

n_rows = st.session_state.group_n_rows
n_cols = st.session_state.group_n_cols
spacing = st.session_state.group_spacing
n_piles = n_rows * n_cols
s_over_d = spacing / pile_width if pile_width > 0 else 0

# Show quick summary
c1, c2, c3 = st.columns(3)
c1.metric("Total Piles", n_piles)
c2.metric("s/d Ratio", f"{s_over_d:.1f}")
c3.metric("Spacing", f"{spacing:.0f} in ({spacing / 12:.1f} ft)")

if s_over_d < 3:
    st.error("s/d < 3 — Below minimum recommended spacing (AASHTO)")
elif s_over_d >= 8:
    st.info("s/d >= 8 — Group effects are negligible. Piles act independently.")

if n_piles <= 1:
    st.info("Single pile — no group analysis needed.")
    st.stop()

st.markdown("---")

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

# --- Run group analysis ---
if st.button("Run Group Analysis", type="primary"):
    # Use axial result if available
    Q_single = 0
    if "axial_result" in st.session_state:
        Q_single = st.session_state.axial_result.Q_ult_compression
    else:
        st.warning("Run axial analysis first for accurate group capacity. Using placeholder value.")
        Q_single = 10000  # placeholder

    result = group_analysis(
        profile=profile,
        n_rows=n_rows,
        n_cols=n_cols,
        pile_width=pile_width,
        spacing=spacing,
        embedment=embedment,
        Q_single_compression=Q_single,
    )
    st.session_state["group_result"] = result

if "group_result" in st.session_state:
    result = st.session_state["group_result"]

    st.subheader("Axial Group Efficiency")
    c1, c2, c3 = st.columns(3)
    c1.metric("Converse-Labarre eta", f"{result.eta_axial:.3f}")
    c2.metric("Group Capacity (individual)", f"{result.Q_group_individual:,.0f} lbs")
    if result.Q_block:
        c3.metric("Block Failure Capacity", f"{result.Q_block:,.0f} lbs")
    else:
        c3.metric("Block Failure", "N/A (no cohesive layers)")

    st.metric("Governing Group Capacity", f"{result.Q_group_governing:,.0f} lbs")

    st.markdown("---")

    # --- Lateral p-multipliers ---
    st.subheader("Lateral Group Effects — p-Multipliers")

    pm_df = pd.DataFrame(result.p_multipliers)
    st.dataframe(pm_df, width="stretch", hide_index=True)

    st.metric("Average Lateral Group Efficiency", f"{result.eta_lateral:.3f}")

    # p-multiplier chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"Row {r['row']}\n({r['position']})" for r in result.p_multipliers],
        y=[r["f_m"] for r in result.p_multipliers],
        marker_color=["#2ecc71" if r["row"] == 1 else "#e74c3c" for r in result.p_multipliers],
        text=[f"{r['f_m']:.2f}" for r in result.p_multipliers],
        textposition="outside",
    ))
    fig.add_hline(y=1.0, line=dict(dash="dash", color="gray"), annotation_text="No reduction")
    fig.update_layout(
        title="p-Multipliers by Row",
        yaxis_title="f_m",
        yaxis=dict(range=[0, 1.15]),
        height=400,
    )
    st.plotly_chart(fig, width="stretch")

    # --- Pile group layout visualization ---
    st.subheader("Group Layout")

    fig_layout = go.Figure()
    for row in range(n_rows):
        for col in range(n_cols):
            x = col * spacing / 12.0
            y = row * spacing / 12.0
            fig_layout.add_trace(go.Scatter(
                x=[x], y=[y],
                mode="markers+text",
                marker=dict(size=20, color="#3498db", symbol="square"),
                text=[f"R{row + 1}C{col + 1}"],
                textposition="top center",
                showlegend=False,
            ))

    fig_layout.update_layout(
        title="Pile Group Plan View",
        xaxis_title="Distance (ft)",
        yaxis_title="Distance (ft)",
        xaxis=dict(scaleanchor="y"),
        height=400,
    )
    # Add wind direction arrow annotation
    fig_layout.add_annotation(
        x=-1, y=(n_rows - 1) * spacing / 12 / 2,
        ax=-3, ay=(n_rows - 1) * spacing / 12 / 2,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowsize=2,
        arrowcolor="red",
    )
    fig_layout.add_annotation(
        x=-2, y=(n_rows - 1) * spacing / 12 / 2 + 0.5,
        text="Wind / Lateral Load",
        showarrow=False, font=dict(color="red"),
    )
    st.plotly_chart(fig_layout, width="stretch")

    # Notes
    st.markdown("### Notes")
    for note in result.notes:
        st.markdown(f"- {note}")
