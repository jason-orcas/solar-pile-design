"""Page 5: Pile design optimization — sweep sections and embedments."""

import sys
import time
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import SoilLayer, SoilProfile, SoilType, AxialSoilZone, build_soil_layer_from_dict
from core.sections import (
    get_section, get_sections_by_family, list_section_families, corroded_section,
)
from core.loads import LoadInput, generate_lrfd_combinations, generate_asd_combinations
from core.optimization import run_optimization_sweep


def _build_axial_zones() -> list[AxialSoilZone] | None:
    """Build AxialSoilZone list from session state, or None if not used."""
    raw = st.session_state.get("axial_zones", [])
    if not raw:
        return None
    zones = []
    for z in raw:
        zones.append(AxialSoilZone(
            top_depth_ft=z.get("top_ft", 0.0),
            bottom_depth_ft=z.get("bottom_ft", 0.0),
            f_s_comp_psf=z.get("f_s_comp_psf", 0.0),
            f_s_uplift_psf=z.get("f_s_uplift_psf", 0.0),
            q_b_psf=z.get("q_b_psf", 0.0),
            description=z.get("description", ""),
        ))
    return zones if zones else None

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
layers_obj = [build_soil_layer_from_dict(ld) for ld in st.session_state.soil_layers]
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

# Guard against None from cleared number_input fields
if embed_min is None:
    embed_min = 5.0
if embed_max is None:
    embed_max = 25.0
if embed_step is None:
    embed_step = 1.0

with col3:
    deflection_limit = st.number_input(
        "Deflection Limit (in)", min_value=0.1, max_value=5.0,
        value=1.0, step=0.25, format="%.2f",
    )

adfreeze_hard_fail = st.checkbox(
    "Enforce adfreeze as pass/fail criterion",
    value=False,
    help="When unchecked, adfreeze is reported as a warning but does not fail "
         "the design. Check this to require tension capacity > adfreeze force.",
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

    # Frost parameters
    _frost_in = st.session_state.get("frost_depth_in", 0.0) or 0.0
    _tau_af = st.session_state.get("tau_af_psi", 10.0) or 10.0
    _fy_ksi = st.session_state.get("steel_grade_ksi", 50) or 50

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
        deflection_limit=deflection_limit if deflection_limit is not None else 1.0,
        design_method=design_method,
        corrosion_t_loss=t_loss,
        n_elements=50,
        frost_depth_in=_frost_in,
        tau_af_psi=_tau_af,
        fy_ksi=_fy_ksi,
        axial_zones=_build_axial_zones(),
        adfreeze_hard_fail=adfreeze_hard_fail,
        progress_callback=update_progress,
    )

    progress_bar.progress(1.0, text=f"Complete! ({opt_result.sweep_time_seconds:.1f}s)")
    st.session_state["optimization_result"] = opt_result

    # Auto-apply optimal design to project
    if opt_result.optimal:
        o = opt_result.optimal
        st.session_state.pile_section = o.section_name
        st.session_state.pile_embedment = o.embedment_ft
        nominal = get_section(o.section_name)
        st.session_state["nominal_section"] = nominal
        if t_loss > 0:
            st.session_state["section"] = corroded_section(nominal, t_loss)
        else:
            st.session_state["section"] = nominal
        # Store analysis results for downstream pages (06, 07)
        if o.axial_result is not None:
            st.session_state["axial_result"] = o.axial_result
        if o.lateral_result is not None:
            st.session_state["lateral_result"] = o.lateral_result
        # Flag so downstream pages can indicate auto-populated values
        st.session_state["optimizer_applied"] = True

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
        o = opt.optimal
        st.success(
            f"**Optimal Design:** {o.section_name} at "
            f"{o.embedment_ft:.1f} ft embedment "
            f"({o.total_weight_lbs:.0f} lbs total pile weight)"
        )

        # --- Governing Design Summary ---
        st.subheader("Governing Design Summary")
        _defl_limit = o.deflection_limit_in if o.deflection_limit_in > 0 else 1.0
        summary_rows = [
            ["Axial Compression", f"{o.axial_comp_dcr:.2f}", o.governing_comp_case,
             "PASS" if o.passes_axial_comp else "FAIL"],
            ["Axial Tension", f"{o.axial_tens_dcr:.2f}", o.governing_tens_case,
             "PASS" if o.passes_axial_tens else "FAIL"],
            ["Lateral Structural", f"{o.lateral_struct_dcr:.2f}", o.governing_lateral_case,
             "PASS" if o.passes_lateral_struct else "FAIL"],
            ["Ground Deflection", f"{o.deflection_in / _defl_limit:.2f}",
             f"{o.deflection_in:.3f} in / {_defl_limit:.2f} in",
             "PASS" if o.passes_deflection else "FAIL"],
        ]
        if _frost_in > 0:
            if o.passes_frost:
                _frost_status = "PASS"
            elif adfreeze_hard_fail:
                _frost_status = "FAIL"
            else:
                _frost_status = "WARNING"
            summary_rows.append([
                "Frost / Adfreeze",
                f"{o.frost_min_embed_ft:.1f} ft min",
                f"Adfreeze: {o.adfreeze_force_lbs:,.0f} lbs",
                _frost_status,
            ])
        summary_df = pd.DataFrame(
            summary_rows, columns=["Check", "DCR / Value", "Governing Condition", "Status"],
        )
        st.dataframe(summary_df, hide_index=True, width="stretch")
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
            "Governing": c.governing_check if not c.passes_all else "",
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, width="stretch", hide_index=True)

    # --- Applied Design Confirmation ---
    if opt.optimal:
        st.markdown("---")
        st.info(
            f"**Auto-applied:** {opt.optimal.section_name} at "
            f"{opt.optimal.embedment_ft:.1f} ft embedment has been set as the "
            f"active design. Axial and Lateral analysis results are available on "
            f"the Analysis pages."
        )
