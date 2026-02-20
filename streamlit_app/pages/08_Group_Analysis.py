"""Page 8: Pile group analysis — Enercalc-style rigid cap load distribution."""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType, build_soil_layer_from_dict
from core.sections import get_section
from core.group import (
    group_analysis,
    converse_labarre,
    p_multipliers_table,
    generate_pile_grid,
    compute_pile_group_centroid,
    rigid_cap_distribution,
    PileLocation,
    LoadPoint,
    RigidCapResult,
)

st.header("Pile Group Analysis")

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
if not st.session_state.get("soil_layers"):
    st.warning("Define soil layers on the Soil Profile page first.")
    st.stop()

section = st.session_state.get("section") or get_section(st.session_state.pile_section)
embedment = st.session_state.pile_embedment
pile_width = section.depth  # governing dimension (in)

# ---------------------------------------------------------------------------
# Session state migration (old uniform spacing -> new X/Y spacing)
# ---------------------------------------------------------------------------
if "group_spacing" in st.session_state and "group_x_spacing" not in st.session_state:
    st.session_state["group_x_spacing"] = st.session_state["group_spacing"]
    st.session_state["group_y_spacing"] = st.session_state["group_spacing"]

# ---------------------------------------------------------------------------
# Section A: Grid Generator
# ---------------------------------------------------------------------------
has_piles = bool(st.session_state.get("group_piles"))

with st.expander("Grid Generator", expanded=not has_piles):
    gc1, gc2, gc3, gc4 = st.columns(4)
    with gc1:
        st.number_input(
            "Number of rows", min_value=1, max_value=30,
            step=1, key="group_n_rows",
        )
    with gc2:
        st.number_input(
            "Piles per row", min_value=1, max_value=30,
            step=1, key="group_n_cols",
        )
    with gc3:
        st.number_input(
            "X spacing — along tracker (in)", min_value=6.0,
            step=6.0, format="%.1f", key="group_x_spacing",
        )
    with gc4:
        st.number_input(
            "Y spacing — perpendicular (in)", min_value=6.0,
            step=6.0, format="%.1f", key="group_y_spacing",
        )

    if st.button("Generate Grid", type="primary"):
        n_rows = st.session_state.group_n_rows
        n_cols = st.session_state.group_n_cols
        x_sp_ft = st.session_state.group_x_spacing / 12.0
        y_sp_ft = st.session_state.group_y_spacing / 12.0
        piles = generate_pile_grid(n_rows, n_cols, x_sp_ft, y_sp_ft)
        st.session_state["group_piles"] = [
            {"id": p.id, "x": p.x, "y": p.y, "label": p.label} for p in piles
        ]
        # Auto-populate default load at centroid
        cx, cy = compute_pile_group_centroid(piles)
        default_V = st.session_state.get("dead_load", 0) * (n_rows * n_cols)
        default_Hx = st.session_state.get("wind_lateral", 0)
        default_My = st.session_state.get("wind_moment", 0)
        st.session_state["group_loads"] = [
            {"id": 1, "x": round(cx, 2), "y": round(cy, 2),
             "V": default_V, "H_x": default_Hx, "H_y": 0.0,
             "M_x": 0.0, "M_y": default_My},
        ]
        st.rerun()

# ---------------------------------------------------------------------------
# Section B: Editable Pile Table
# ---------------------------------------------------------------------------
st.subheader("Pile Coordinates")

if not st.session_state.get("group_piles"):
    st.info("Use the Grid Generator above to create an initial pile layout, or add piles manually below.")
    st.session_state["group_piles"] = [
        {"id": 1, "x": 0.0, "y": 0.0, "label": "P1"},
    ]

pile_df = pd.DataFrame(st.session_state["group_piles"])
pile_df = pile_df[["id", "x", "y", "label"]]

edited_piles = st.data_editor(
    pile_df,
    column_config={
        "id": st.column_config.NumberColumn("Pile #", disabled=True, width="small"),
        "x": st.column_config.NumberColumn("X (ft)", format="%.2f", step=0.5),
        "y": st.column_config.NumberColumn("Y (ft)", format="%.2f", step=0.5),
        "label": st.column_config.TextColumn("Label", width="small"),
    },
    num_rows="dynamic",
    width="stretch",
    key="pile_editor",
)

# NOTE: Do NOT sync edited_piles back to group_piles here — writing on every
# rerun causes Streamlit to detect a data change and reset the editor's delta,
# which forces users to enter values twice.  Instead, group_piles is synced
# when "Run Group Analysis" is clicked.

n_piles = len(edited_piles)
if n_piles > 0:
    xs = edited_piles["x"].fillna(0.0).tolist()
    ys = edited_piles["y"].fillna(0.0).tolist()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Piles", n_piles)
    c2.metric("Group Width (X)", f"{max(xs) - min(xs):.1f} ft")
    c3.metric("Group Length (Y)", f"{max(ys) - min(ys):.1f} ft")

if n_piles < 1:
    st.warning("Add at least one pile.")
    st.stop()

st.markdown("---")

# ---------------------------------------------------------------------------
# Section C: Load Application Points
# ---------------------------------------------------------------------------
st.subheader("Load Application Points")
st.caption("Each load has a position (X, Y) and full force components.")

if not st.session_state.get("group_loads"):
    pile_objs = [PileLocation(**p) for p in updated_piles]
    cx, cy = compute_pile_group_centroid(pile_objs)
    st.session_state["group_loads"] = [
        {"id": 1, "x": round(cx, 2), "y": round(cy, 2),
         "V": 0.0, "H_x": 0.0, "H_y": 0.0, "M_x": 0.0, "M_y": 0.0},
    ]

load_df = pd.DataFrame(st.session_state["group_loads"])
load_df = load_df[["id", "x", "y", "V", "H_x", "H_y", "M_x", "M_y"]]

edited_loads = st.data_editor(
    load_df,
    column_config={
        "id": st.column_config.NumberColumn("Load #", disabled=True, width="small"),
        "x": st.column_config.NumberColumn("X (ft)", format="%.2f", step=0.5),
        "y": st.column_config.NumberColumn("Y (ft)", format="%.2f", step=0.5),
        "V": st.column_config.NumberColumn("V (lbs)", format="%.0f", step=100),
        "H_x": st.column_config.NumberColumn("H_x (lbs)", format="%.0f", step=100),
        "H_y": st.column_config.NumberColumn("H_y (lbs)", format="%.0f", step=100),
        "M_x": st.column_config.NumberColumn("M_x (ft-lbs)", format="%.0f", step=100),
        "M_y": st.column_config.NumberColumn("M_y (ft-lbs)", format="%.0f", step=100),
    },
    num_rows="dynamic",
    width="stretch",
    key="load_editor",
)

# NOTE: Do NOT sync edited_loads back to group_loads here (same delta-reset
# issue as the pile table).  Synced when "Run Group Analysis" is clicked.

st.markdown("---")

# ---------------------------------------------------------------------------
# Section C2: Capacity Inputs (with manual override)
# ---------------------------------------------------------------------------
st.subheader("Single Pile Capacity")

axial_res = st.session_state.get("axial_result")
default_comp = axial_res.Q_ult_compression if axial_res else 0.0
default_tens = axial_res.Q_ult_tension if axial_res else 0.0

if not axial_res:
    st.warning("Run axial analysis (Page 06) first for accurate capacity. Using manual values.")

cap_c1, cap_c2 = st.columns(2)
with cap_c1:
    Q_comp = st.number_input(
        "Compression capacity (lbs)", min_value=0.0,
        value=st.session_state.get("group_Q_comp", default_comp),
        step=500.0, format="%.0f", key="group_Q_comp_input",
    )
with cap_c2:
    Q_tens = st.number_input(
        "Tension capacity (lbs)", min_value=0.0,
        value=st.session_state.get("group_Q_tens", default_tens),
        step=500.0, format="%.0f", key="group_Q_tens_input",
    )
st.session_state["group_Q_comp"] = Q_comp
st.session_state["group_Q_tens"] = Q_tens

# ---------------------------------------------------------------------------
# Section D: Head Condition
# ---------------------------------------------------------------------------
col_head, _ = st.columns(2)
with col_head:
    st.radio(
        "Pile Head Condition", ["Free", "Fixed/Restricted"],
        key="group_head_condition", horizontal=True,
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Section E: Run Analysis
# ---------------------------------------------------------------------------
def _clean_pile_records(df: pd.DataFrame) -> list[dict]:
    """Convert data_editor DataFrame to clean list-of-dicts for session state."""
    records = df.to_dict("records")
    for i, p in enumerate(records):
        p["id"] = i + 1
        if not p.get("label") or (isinstance(p.get("label"), float) and pd.isna(p["label"])):
            p["label"] = f"P{i + 1}"
        if pd.isna(p.get("x")):
            p["x"] = 0.0
        if pd.isna(p.get("y")):
            p["y"] = 0.0
    return records


def _clean_load_records(df: pd.DataFrame) -> list[dict]:
    """Convert data_editor DataFrame to clean list-of-dicts for session state."""
    records = df.to_dict("records")
    for i, ld in enumerate(records):
        ld["id"] = i + 1
        for k in ("x", "y", "V", "H_x", "H_y", "M_x", "M_y"):
            if pd.isna(ld.get(k)):
                ld[k] = 0.0
    return records


if st.button("Run Group Analysis", type="primary"):
    # Commit editor state to session state (for save/load and PDF export)
    st.session_state["group_piles"] = _clean_pile_records(edited_piles)
    st.session_state["group_loads"] = _clean_load_records(edited_loads)

    pile_objs = [PileLocation(**p) for p in st.session_state["group_piles"]]
    load_objs = [LoadPoint(**ld) for ld in st.session_state["group_loads"]]

    layers_obj = [build_soil_layer_from_dict(ld) for ld in st.session_state.soil_layers]
    profile = SoilProfile(
        layers=layers_obj,
        water_table_depth=st.session_state.water_table_depth,
    )

    with st.spinner("Running rigid cap distribution..."):
        result = rigid_cap_distribution(
            piles=pile_objs,
            loads=load_objs,
            Q_capacity_compression=Q_comp,
            Q_capacity_tension=Q_tens,
            profile=profile,
            pile_width=pile_width,
            embedment=embedment,
        )
    st.session_state["group_result"] = result

# ---------------------------------------------------------------------------
# Section F & G: Results Display
# ---------------------------------------------------------------------------
if "group_result" in st.session_state and isinstance(
    st.session_state["group_result"], RigidCapResult
):
    result: RigidCapResult = st.session_state["group_result"]

    # F1: Centroid & Eccentricity
    st.subheader("Centroid & Eccentricity")
    ce1, ce2, ce3, ce4 = st.columns(4)
    ce1.metric("Pile Centroid",
               f"({result.pile_centroid_x:.2f}, {result.pile_centroid_y:.2f}) ft")
    ce2.metric("Load Centroid",
               f"({result.load_centroid_x:.2f}, {result.load_centroid_y:.2f}) ft")
    ce3.metric("Eccentricity e_x", f"{result.eccentricity_x:.3f} ft")
    ce4.metric("Eccentricity e_y", f"{result.eccentricity_y:.3f} ft")

    # F2: Load Resultant
    lr1, lr2, lr3 = st.columns(3)
    lr1.metric("V_total", f"{result.V_total:,.0f} lbs")
    lr2.metric("M_x (at centroid)", f"{result.M_x_total:,.0f} ft-lbs")
    lr3.metric("M_y (at centroid)", f"{result.M_y_total:,.0f} ft-lbs")

    st.markdown("---")

    # F3: Individual Pile Reactions
    st.subheader("Individual Pile Reactions")
    rxn_data = []
    for r in result.reactions:
        load_type = "Compression" if r.P_axial >= 0 else "Tension"
        status = "OK" if r.utilization <= 1.0 else "OVER"
        rxn_data.append({
            "Pile #": r.pile_id,
            "Label": r.label,
            "X (ft)": f"{r.x:.2f}",
            "Y (ft)": f"{r.y:.2f}",
            "P_axial (lbs)": f"{r.P_axial:,.0f}",
            "Type": load_type,
            "Utilization (%)": f"{r.utilization * 100:.1f}%",
            "Status": status,
        })
    rxn_df = pd.DataFrame(rxn_data)
    st.dataframe(rxn_df, width="stretch", hide_index=True)

    # F4: Governing Summary
    st.subheader("Governing Summary")
    gs1, gs2, gs3, gs4 = st.columns(4)
    gs1.metric("Max Compression", f"{result.P_max:,.0f} lbs")
    gs2.metric("Max Tension", f"{result.P_min:,.0f} lbs")
    gs3.metric("Governing Pile", f"Pile {result.governing_pile_id}")
    gs4.metric("Max Utilization", f"{result.max_utilization:.1%}")

    if result.all_piles_ok:
        st.success("All piles within capacity.")
    else:
        st.error("One or more piles exceed capacity — review design.")

    st.markdown("---")

    # F5: Efficiency & p-Multipliers (in expander)
    with st.expander("Axial Group Efficiency & p-Multipliers"):
        ef1, ef2 = st.columns(2)
        ef1.metric("Converse-Labarre eta", f"{result.eta_axial:.3f}")
        ef2.metric("Average Lateral Efficiency", f"{result.eta_lateral:.3f}")

        if result.p_multipliers:
            pm_df = pd.DataFrame(result.p_multipliers)
            st.dataframe(pm_df, width="stretch", hide_index=True)

            fig_pm = go.Figure()
            fig_pm.add_trace(go.Bar(
                x=[f"Row {r['row']}\n({r['position']})" for r in result.p_multipliers],
                y=[r["f_m"] for r in result.p_multipliers],
                marker_color=[
                    "#2ecc71" if r["row"] == 1 else "#e74c3c"
                    for r in result.p_multipliers
                ],
                text=[f"{r['f_m']:.2f}" for r in result.p_multipliers],
                textposition="outside",
            ))
            fig_pm.add_hline(y=1.0, line=dict(dash="dash", color="gray"),
                             annotation_text="No reduction")
            fig_pm.update_layout(
                title="p-Multipliers by Row",
                yaxis_title="f_m",
                yaxis=dict(range=[0, 1.15]),
                height=350,
            )
            st.plotly_chart(fig_pm, width="stretch")

    st.markdown("---")

    # G: Plan View Visualization
    st.subheader("Group Plan View")

    fig = go.Figure()

    # Pile markers — colored by utilization
    util_colors = []
    for r in result.reactions:
        if r.utilization > 1.0:
            util_colors.append("#e74c3c")      # red
        elif r.utilization > 0.9:
            util_colors.append("#f39c12")      # orange
        elif r.utilization > 0.7:
            util_colors.append("#f1c40f")      # yellow
        else:
            util_colors.append("#2ecc71")      # green

    fig.add_trace(go.Scatter(
        x=[r.x for r in result.reactions],
        y=[r.y for r in result.reactions],
        mode="markers+text",
        marker=dict(size=22, color=util_colors, symbol="square",
                    line=dict(width=1, color="black")),
        text=[f"P{r.pile_id}<br>{r.P_axial:,.0f} lb" for r in result.reactions],
        textposition="top center",
        textfont=dict(size=9),
        name="Piles",
    ))

    # Load points
    loads_data = st.session_state.get("group_loads", [])
    if loads_data:
        fig.add_trace(go.Scatter(
            x=[ld["x"] for ld in loads_data],
            y=[ld["y"] for ld in loads_data],
            mode="markers+text",
            marker=dict(size=16, color="#e74c3c", symbol="diamond",
                        line=dict(width=1, color="black")),
            text=[f"L{ld['id']}<br>V={ld['V']:,.0f}" for ld in loads_data],
            textposition="bottom center",
            textfont=dict(size=9),
            name="Load Points",
        ))

    # Pile centroid
    fig.add_trace(go.Scatter(
        x=[result.pile_centroid_x], y=[result.pile_centroid_y],
        mode="markers+text",
        marker=dict(size=14, color="#2ecc71", symbol="cross"),
        text=["Pile CG"], textposition="bottom right",
        name="Pile Centroid",
    ))

    # Load centroid
    fig.add_trace(go.Scatter(
        x=[result.load_centroid_x], y=[result.load_centroid_y],
        mode="markers+text",
        marker=dict(size=14, color="#f39c12", symbol="triangle-up"),
        text=["Load CG"], textposition="bottom right",
        name="Load Centroid",
    ))

    # Eccentricity vector
    if abs(result.eccentricity_x) > 0.001 or abs(result.eccentricity_y) > 0.001:
        fig.add_trace(go.Scatter(
            x=[result.pile_centroid_x, result.load_centroid_x],
            y=[result.pile_centroid_y, result.load_centroid_y],
            mode="lines",
            line=dict(dash="dash", color="gray", width=2),
            name=(f"Eccentricity "
                  f"({result.eccentricity_x:.2f}, {result.eccentricity_y:.2f}) ft"),
        ))

    # Layout
    all_x = [r.x for r in result.reactions] + [ld["x"] for ld in loads_data]
    all_y = [r.y for r in result.reactions] + [ld["y"] for ld in loads_data]
    pad = max(2.0, (max(all_x) - min(all_x)) * 0.15, (max(all_y) - min(all_y)) * 0.15)

    fig.update_layout(
        xaxis_title="X (ft)",
        yaxis_title="Y (ft)",
        xaxis=dict(
            scaleanchor="y",
            range=[min(all_x) - pad, max(all_x) + pad],
        ),
        yaxis=dict(
            range=[min(all_y) - pad, max(all_y) + pad],
        ),
        height=500,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig, width="stretch")

    # H: Notes
    if result.notes:
        st.markdown("### Notes")
        for note in result.notes:
            st.markdown(f"- {note}")
