"""Page 2: Soil profile input — layers, SPT data, parameter derivation."""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType, correct_N_overburden

st.header("Soil Profile")

# --- Water table ---
col_wt1, col_wt2 = st.columns([1, 3])
with col_wt1:
    has_wt = st.checkbox("Water table present?", value=st.session_state.water_table_depth is not None)
with col_wt2:
    if has_wt:
        st.session_state.water_table_depth = st.number_input(
            "Water table depth (ft)", min_value=0.0, value=st.session_state.water_table_depth or 10.0, step=0.5,
        )
    else:
        st.session_state.water_table_depth = None

st.markdown("---")

# --- Layer input ---
st.subheader("Soil Layers")
st.caption("Define layers from top down. At minimum, provide soil type and SPT N-value.")

if "soil_layers" not in st.session_state or not st.session_state.soil_layers:
    st.session_state.soil_layers = []

# Add layer form
with st.expander("Add New Layer", expanded=len(st.session_state.soil_layers) == 0):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        new_top = st.number_input("Top Depth (ft)", min_value=0.0, value=0.0, step=0.5, key="new_top")
        new_bot = st.number_input("Bottom Depth (ft)", min_value=0.5, value=5.0, step=0.5, key="new_bot")
    with c2:
        new_type = st.selectbox("Soil Type", [t.value for t in SoilType], key="new_type")
        new_desc = st.text_input("Description", value="", key="new_desc", placeholder="e.g., Brown silty sand")
    with c3:
        new_N = st.number_input("SPT N-value (raw)", min_value=0, value=15, step=1, key="new_N")
        new_gamma = st.number_input("Unit weight (pcf, 0=auto)", min_value=0.0, value=0.0, step=5.0, key="new_gamma")
    with c4:
        new_phi = st.number_input("Friction angle (deg, 0=auto)", min_value=0.0, value=0.0, step=1.0, key="new_phi")
        new_cu = st.number_input("c_u (psf, 0=auto)", min_value=0.0, value=0.0, step=100.0, key="new_cu")

    if st.button("Add Layer", type="primary"):
        if new_bot <= new_top:
            st.error("Bottom depth must be greater than top depth.")
        else:
            layer_data = {
                "top_depth": new_top,
                "thickness": new_bot - new_top,
                "soil_type": new_type,
                "description": new_desc,
                "N_spt": new_N,
                "gamma": new_gamma if new_gamma > 0 else None,
                "phi": new_phi if new_phi > 0 else None,
                "c_u": new_cu if new_cu > 0 else None,
            }
            st.session_state.soil_layers.append(layer_data)
            st.success(f"Added layer: {new_desc or new_type} at {new_top}-{new_bot} ft")
            st.rerun()

# Display existing layers
if st.session_state.soil_layers:
    st.subheader("Current Layers")

    # Build SoilProfile for computed properties
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

    # Table display
    table_data = []
    for i, (ld, lo) in enumerate(zip(st.session_state.soil_layers, layers_obj)):
        sigma_v = profile.effective_stress_at(lo.mid_depth)
        N1_60 = correct_N_overburden(lo.N_60 or 0, sigma_v)
        table_data.append({
            "#": i + 1,
            "Depth (ft)": f"{lo.top_depth:.1f} - {lo.bottom_depth:.1f}",
            "Type": ld["soil_type"],
            "Description": ld.get("description", ""),
            "N_spt": ld.get("N_spt", "-"),
            "N_60": f"{lo.N_60:.1f}" if lo.N_60 else "-",
            "(N1)_60": f"{N1_60:.1f}" if N1_60 else "-",
            "gamma (pcf)": f"{lo.gamma or lo._estimate_gamma():.0f}",
            "phi' (deg)": f"{lo.get_phi(sigma_v):.1f}" if lo.get_phi(sigma_v) > 0 else "-",
            "c_u (psf)": f"{lo.get_cu():.0f}" if lo.get_cu() > 0 else "-",
            "sigma'_v mid (psf)": f"{sigma_v:.0f}",
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Delete layer
    col_del1, col_del2 = st.columns([1, 3])
    with col_del1:
        del_idx = st.number_input("Layer # to delete", min_value=1, max_value=len(st.session_state.soil_layers), value=1)
    with col_del2:
        if st.button("Delete Layer"):
            st.session_state.soil_layers.pop(del_idx - 1)
            st.rerun()

    # --- Soil profile visualization ---
    st.subheader("Soil Profile Visualization")

    fig = go.Figure()

    color_map = {
        "Sand": "#F4D03F",
        "Gravel": "#D5D8DC",
        "Silt": "#A9CCE3",
        "Clay": "#A0522D",
        "Organic": "#2ECC71",
    }

    for lo in layers_obj:
        color = color_map.get(lo.soil_type.value, "#999999")
        fig.add_shape(
            type="rect",
            x0=0, x1=1,
            y0=-lo.bottom_depth, y1=-lo.top_depth,
            fillcolor=color, opacity=0.6,
            line=dict(width=1, color="black"),
        )
        label = f"{lo.description or lo.soil_type.value} (N={lo.N_spt})"
        fig.add_annotation(
            x=0.5, y=-(lo.top_depth + lo.thickness / 2),
            text=label, showarrow=False, font=dict(size=12),
        )

    # Water table line
    if st.session_state.water_table_depth is not None:
        fig.add_hline(
            y=-st.session_state.water_table_depth,
            line=dict(color="blue", width=2, dash="dash"),
            annotation_text="GWT",
        )

    max_d = max(lo.bottom_depth for lo in layers_obj)
    fig.update_layout(
        title="Soil Profile",
        yaxis_title="Depth (ft)",
        yaxis=dict(range=[-(max_d + 2), 1]),
        xaxis=dict(visible=False),
        height=400,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Effective stress plot
    st.subheader("Effective Stress Profile")
    depths_plot = [d * 0.5 for d in range(int(max_d * 2) + 1)]
    stresses = [profile.effective_stress_at(d) for d in depths_plot]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=stresses, y=[-d for d in depths_plot],
        mode="lines", name="sigma'_v",
        line=dict(color="red", width=2),
    ))
    fig2.update_layout(
        title="Effective Vertical Stress vs Depth",
        xaxis_title="sigma'_v (psf)",
        yaxis_title="Depth (ft)",
        height=400,
    )
    st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("No layers defined yet. Add at least one soil layer to proceed.")
