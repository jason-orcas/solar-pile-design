"""Page 5: Pile design optimization — sweep sections and embedments."""

import sys
import time
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType
from core.sections import (
    get_section, get_sections_by_family, list_section_families, corroded_section,
)
from core.loads import LoadInput, generate_lrfd_combinations, generate_asd_combinations
from core.optimization import run_optimization_sweep

st.header("Pile Design Optimization")
st.caption("Sweep section families across embedment depths to find the lightest passing design.")

# --- Prerequisites check ---
if not st.session_state.get("soil_layers"):
    st.warning("Define soil layers on the **Soil Profile** page first.")
    st.stop()

has_loads = (
    st.session_state.get("wind_lateral", 0) > 0
    or st.session_state.get("wind_up", 0) > 0
)
if not has_loads:
    st.warning("Configure loads on the **Loading** page first (wind lateral and/or uplift).")
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
profile = SoilProfile(
    layers=layers_obj,
    water_table_depth=st.session_state.get("water_table_depth"),
)

# ============================================================================
# Configuration
# ============================================================================
st.subheader("Optimization Settings")

col1, col2, col3 = st.columns(3)

with col1:
    section_family = st.selectbox(
        "Section Family",
        list_section_families(),
        index=0,
        help="Select which sections to include in the sweep.",
    )

with col2:
    embed_min = st.number_input(
        "Min Embedment (ft)", min_value=3.0, max_value=40.0,
        value=5.0, step=1.0, format="%.1f",
    )
    embed_max = st.number_input(
        "Max Embedment (ft)", min_value=5.0, max_value=50.0,
        value=25.0, step=1.0, format="%.1f",
    )
    embed_step = st.number_input(
        "Embedment Step (ft)", min_value=0.5, max_value=5.0,
        value=1.0, step=0.5, format="%.1f",
    )

with col3:
    deflection_limit = st.number_input(
        "Deflection Limit (in)", min_value=0.1, max_value=5.0,
        value=1.0, step=0.25, format="%.2f",
    )

# Show inherited settings
with st.expander("Inherited Design Settings (from prior pages)", expanded=False):
    ic1, ic2, ic3, ic4 = st.columns(4)
    ic1.text(f"Pile type: {st.session_state.get('pile_type', 'driven')}")
    ic2.text(f"Head: {st.session_state.get('head_condition', 'free')}")
    ic3.text(f"Axis: {st.session_state.get('bending_axis', 'strong')}")
    ic4.text(f"Method: {st.session_state.get('design_method', 'LRFD')}")
    ic5, ic6, ic7, ic8 = st.columns(4)
    ic5.text(f"Axial method: {st.session_state.get('axial_method', 'auto')}")
    ic6.text(f"FS comp: {st.session_state.get('FS_compression', 2.5)}")
    ic7.text(f"FS tens: {st.session_state.get('FS_tension', 3.0)}")
    corr_on = st.session_state.get("corrosion_enabled", False)
    ic8.text(f"Corrosion: {'ON' if corr_on else 'OFF'}")

# Sweep preview
sections = get_sections_by_family(section_family)
n_embedments = len(list(np.arange(embed_min, embed_max + embed_step * 0.01, embed_step)))
total_combos = len(sections) * n_embedments
est_time = total_combos * 0.75  # ~0.75s per lateral solve with n_elements=50

st.info(
    f"**Sweep:** {len(sections)} sections "
    f"({', '.join(s.name for s in sections)}) "
    f"x {n_embedments} embedments = **{total_combos} combinations**. "
    f"Estimated time: ~{est_time:.0f} seconds."
)

st.markdown("---")

# ============================================================================
# Run Optimization
# ============================================================================
if st.button("Run Optimization Sweep", type="primary"):
    # Build load input from session state
    load_input = LoadInput(
        dead=st.session_state.get("dead_load", 400.0),
        live=st.session_state.get("live_load", 0.0),
        snow=st.session_state.get("snow_load", 0.0),
        wind_down=st.session_state.get("wind_down", 0.0),
        wind_up=st.session_state.get("wind_up", 1500.0),
        wind_lateral=st.session_state.get("wind_lateral", 1500.0),
        wind_moment=st.session_state.get("wind_moment", 0.0),
        seismic_vertical=st.session_state.get("seismic_vertical", 0.0),
        seismic_lateral=st.session_state.get("seismic_lateral", 0.0),
        seismic_moment=st.session_state.get("seismic_moment", 0.0),
        lever_arm=st.session_state.get("lever_arm", 4.0),
    )

    design_method = st.session_state.get("design_method", "LRFD")
    if design_method == "ASD":
        load_cases = generate_asd_combinations(load_input)
    else:
        load_cases = generate_lrfd_combinations(load_input)

    # Corrosion
    t_loss = 0.0
    if st.session_state.get("corrosion_enabled"):
        t_loss = st.session_state.get("corrosion_t_loss", 0.0)

    # Progress bar
    progress_bar = st.progress(0, text="Starting optimization sweep...")

    def update_progress(current, total, section_name):
        pct = current / total
        progress_bar.progress(pct, text=f"Analyzing {section_name} ({current}/{total})")

    opt_result = run_optimization_sweep(
        profile=profile,
        section_family=section_family,
        embedment_range=(embed_min, embed_max, embed_step),
        load_cases=load_cases,
        pile_type=st.session_state.get("pile_type", "driven"),
        head_condition=st.session_state.get("head_condition", "free"),
        bending_axis=st.session_state.get("bending_axis", "strong"),
        cyclic=st.session_state.get("cyclic_loading", False),
        axial_method=st.session_state.get("axial_method", "auto"),
        FS_compression=st.session_state.get("FS_compression", 2.5),
        FS_tension=st.session_state.get("FS_tension", 3.0),
        deflection_limit=deflection_limit,
        design_method=design_method,
        corrosion_t_loss=t_loss,
        n_elements=50,
        progress_callback=update_progress,
    )

    progress_bar.progress(1.0, text=f"Complete! ({opt_result.sweep_time_seconds:.1f}s)")
    st.session_state["optimization_result"] = opt_result

# ============================================================================
# Results Display
# ============================================================================
if "optimization_result" in st.session_state:
    opt = st.session_state["optimization_result"]

    st.markdown("---")
    st.subheader("Optimization Results")

    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Combinations", f"{opt.total_combinations}")
    m2.metric("Passing", f"{opt.passing_count}")
    m3.metric("Failing", f"{opt.total_combinations - opt.passing_count}")
    m4.metric("Sweep Time", f"{opt.sweep_time_seconds:.1f}s")

    # Optimal design highlight
    if opt.optimal:
        st.success(
            f"**Optimal Design:** {opt.optimal.section_name} at "
            f"{opt.optimal.embedment_ft:.1f} ft embedment "
            f"({opt.optimal.total_weight_lbs:.0f} lbs total pile weight)"
        )
    else:
        st.error(
            "No passing designs found in the swept range. "
            "Try expanding the embedment range or using heavier sections."
        )

    # --- Pass/Fail Heatmap ---
    st.subheader("Pass/Fail Matrix")

    section_names = opt.section_names
    embedments = sorted(set(c.embedment_ft for c in opt.candidates))

    # Build 2D matrix: 1=pass, 0=fail
    pass_matrix = []
    for emb in embedments:
        row = []
        for sec in section_names:
            cand = next(
                (c for c in opt.candidates
                 if c.section_name == sec and c.embedment_ft == emb),
                None,
            )
            row.append(1 if cand and cand.passes_all else 0)
        pass_matrix.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=pass_matrix,
        x=section_names,
        y=[f"{e:.1f}" for e in embedments],
        colorscale=[[0, "#e74c3c"], [1, "#2ecc71"]],
        showscale=False,
        text=[[("PASS" if v == 1 else "FAIL") for v in row] for row in pass_matrix],
        texttemplate="%{text}",
        hovertemplate="Section: %{x}<br>Embedment: %{y} ft<br>%{text}<extra></extra>",
    ))

    if opt.optimal:
        fig.add_annotation(
            x=opt.optimal.section_name,
            y=f"{opt.optimal.embedment_ft:.1f}",
            text="OPTIMAL",
            showarrow=True, arrowhead=2,
            font=dict(size=11, color="white"),
            bgcolor="black",
        )

    fig.update_layout(
        xaxis_title="Section",
        yaxis_title="Embedment Depth (ft)",
        height=max(400, len(embedments) * 25 + 100),
    )
    st.plotly_chart(fig, width="stretch")

    # --- Detailed Results Table ---
    st.subheader("Detailed Results")

    table_data = []
    for c in opt.candidates:
        table_data.append({
            "Section": c.section_name,
            "Embed (ft)": f"{c.embedment_ft:.1f}",
            "Weight (lbs)": f"{c.total_weight_lbs:.0f}",
            "Comp DCR": f"{c.axial_comp_dcr:.2f}" if c.axial_comp_dcr < 100 else ">100",
            "Tens DCR": f"{c.axial_tens_dcr:.2f}" if c.axial_tens_dcr < 100 else ">100",
            "Lateral DCR": f"{c.lateral_struct_dcr:.2f}" if c.lateral_struct_dcr < 100 else ">100",
            "Defl (in)": f"{c.deflection_in:.3f}" if c.deflection_in < 100 else ">100",
            "Status": "PASS" if c.passes_all else "FAIL",
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, width="stretch", hide_index=True)

    # --- Apply Optimal Design ---
    if opt.optimal:
        st.markdown("---")
        st.subheader("Apply Optimal Design")
        st.markdown(
            f"Apply **{opt.optimal.section_name}** at "
            f"**{opt.optimal.embedment_ft:.1f} ft** embedment to the project. "
            f"Downstream analysis pages will automatically use this selection."
        )
        if st.button("Apply Optimal Design to Project", type="primary"):
            st.session_state.pile_section = opt.optimal.section_name
            st.session_state.pile_embedment = opt.optimal.embedment_ft
            nominal = get_section(opt.optimal.section_name)
            st.session_state["nominal_section"] = nominal
            t_loss = 0.0
            if st.session_state.get("corrosion_enabled"):
                t_loss = st.session_state.get("corrosion_t_loss", 0.0)
            if t_loss > 0:
                st.session_state["section"] = corroded_section(nominal, t_loss)
            else:
                st.session_state["section"] = nominal
            st.success(
                f"Applied **{opt.optimal.section_name}** at "
                f"**{opt.optimal.embedment_ft:.1f} ft**. "
                f"Proceed to Axial Capacity and Lateral Analysis pages for detailed results."
            )
