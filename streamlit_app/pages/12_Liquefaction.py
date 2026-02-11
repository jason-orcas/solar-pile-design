"""Page 12: Liquefaction screening — Boulanger & Idriss (2014) SPT method."""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType
from core.liquefaction import liquefaction_screening

st.header("Liquefaction Screening")
st.caption("Boulanger & Idriss (2014) — SPT-based simplified procedure")

# --- Prerequisites ---
if not st.session_state.get("soil_layers"):
    st.warning("Define soil layers on the Soil Profile page first.")
    st.stop()

# --- Inputs ---
st.subheader("Seismic Parameters")
col1, col2, col3 = st.columns(3)

# Default PGA from SDS if available
sds_hint = ""
if st.session_state.get("seismic_lateral", 0) > 0 or st.session_state.get("liq_a_max", 0) > 0:
    sds_hint = " (Approximate: SDS / 2.5)"

with col1:
    a_max = st.number_input(
        f"PGA, a_max (g){sds_hint}",
        min_value=0.0, max_value=2.0, step=0.01, format="%.3f",
        key="liq_a_max",
    )

with col2:
    M_w = st.number_input(
        "Earthquake magnitude (M_w)",
        min_value=4.0, max_value=9.5, step=0.1, format="%.1f",
        key="liq_Mw",
    )

with col3:
    FC = st.number_input(
        "Default fines content (%)",
        min_value=0.0, max_value=100.0, step=5.0, format="%.0f",
        key="liq_fines_content",
    )

max_depth = st.slider("Maximum screening depth (ft)", 10, 100, 65)

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

# --- Run ---
if st.button("Run Liquefaction Screening", type="primary"):
    result = liquefaction_screening(
        profile=profile,
        a_max_g=a_max,
        M_w=M_w,
        fines_content_default=FC,
        max_depth_ft=max_depth,
    )
    st.session_state["liq_result"] = result

if "liq_result" in st.session_state:
    result = st.session_state["liq_result"]

    # Summary banner
    if result.any_liquefiable:
        st.error(result.summary)
    elif "MARGINAL" in result.summary:
        st.warning(result.summary)
    else:
        st.success(result.summary)

    st.caption(f"MSF = {result.MSF:.2f}")

    # Notes
    for n in result.notes:
        st.caption(n)

    # Layer results table
    if result.layer_results:
        rows = []
        for lr in result.layer_results:
            rows.append({
                "Depth (ft)": lr.depth_ft,
                "Layer": lr.layer_description,
                "Soil": lr.soil_type,
                "N_SPT": lr.N_spt,
                "(N1)_60": lr.N1_60,
                "(N1)_60cs": lr.N1_60cs,
                "CSR": lr.CSR,
                "CRR": lr.CRR,
                "FS_liq": lr.FS_liq,
                "Status": lr.status,
            })
        df = pd.DataFrame(rows)

        def _color_status(val):
            if val == "Liquefiable":
                return "background-color: #ffcccc"
            elif val == "Marginal":
                return "background-color: #fff3cd"
            elif val == "Non-liquefiable":
                return "background-color: #d4edda"
            return ""

        st.dataframe(
            df.style.map(_color_status, subset=["Status"]),
            width="stretch",
            hide_index=True,
        )

        # FS vs depth plot
        evaluated = [lr for lr in result.layer_results
                     if lr.status not in ("N/A (cohesive)", "Above water table", "No SPT data")]
        if evaluated:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[lr.FS_liq for lr in evaluated],
                y=[-lr.depth_ft for lr in evaluated],
                mode="markers+lines",
                marker=dict(
                    size=10,
                    color=["red" if lr.FS_liq < 1.0 else "orange" if lr.FS_liq < 1.3 else "green"
                           for lr in evaluated],
                ),
                name="FS_liq",
            ))
            fig.add_vline(x=1.0, line=dict(dash="dash", color="red"),
                          annotation_text="FS = 1.0")
            fig.add_vline(x=1.3, line=dict(dash="dot", color="orange"),
                          annotation_text="FS = 1.3")
            fig.update_layout(
                title="Factor of Safety vs Depth",
                xaxis_title="FS against Liquefaction",
                yaxis_title="Depth (ft)",
                xaxis=dict(range=[0, max(3.0, max(lr.FS_liq for lr in evaluated) + 0.5)]),
                height=450,
            )
            st.plotly_chart(fig, width="stretch")
