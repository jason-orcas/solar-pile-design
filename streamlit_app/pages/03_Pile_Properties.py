"""Page 3: Pile section and properties input."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.sections import (
    SECTIONS, get_section, list_sections,
    CORROSION_RATES, COATING_REDUCTION,
    compute_corrosion_params, corroded_section,
)

st.header("Pile Properties")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Section Selection")
    section_name = st.selectbox(
        "Steel Section",
        list_sections(),
        index=list_sections().index(st.session_state.get("pile_section", "W6x9")),
    )
    st.session_state.pile_section = section_name

    nominal = get_section(section_name)
    st.session_state["nominal_section"] = nominal

    # Display nominal section properties
    st.markdown("**Section Properties:**")
    props = {
        "Depth (in)": f"{nominal.depth:.2f}",
        "Flange Width (in)": f"{nominal.width:.2f}",
        "Area (in\u00b2)": f"{nominal.area:.2f}",
        "Weight (plf)": f"{nominal.weight:.1f}",
        "I_x (in\u2074)": f"{nominal.Ix:.1f}",
        "I_y (in\u2074)": f"{nominal.Iy:.2f}",
        "S_x (in\u00b3)": f"{nominal.Sx:.2f}",
        "S_y (in\u00b3)": f"{nominal.Sy:.3f}",
        "Z_x (in\u00b3)": f"{nominal.Zx:.2f}",
        "Z_y (in\u00b3)": f"{nominal.Zy:.2f}",
        "Perimeter (in)": f"{nominal.perimeter:.1f}",
        "Tip Area (in\u00b2)": f"{nominal.tip_area:.1f}",
    }
    for k, v in props.items():
        st.text(f"  {k}: {v}")

with col2:
    st.subheader("Installation & Geometry")

    st.session_state.pile_embedment = st.number_input(
        "Embedment Depth (ft)",
        min_value=1.0, max_value=50.0,
        value=st.session_state.get("pile_embedment", 10.0),
        step=0.5, format="%.1f",
    )
    if st.session_state.pile_embedment is None:
        st.session_state.pile_embedment = 10.0

    st.session_state.pile_type = st.selectbox(
        "Installation Method",
        ["driven", "drilled", "helical"],
        index=["driven", "drilled", "helical"].index(
            st.session_state.get("pile_type", "driven")
        ),
    )

    st.session_state.head_condition = st.selectbox(
        "Pile Head Condition",
        ["free", "fixed"],
        index=["free", "fixed"].index(
            st.session_state.get("head_condition", "free")
        ),
    )

    st.session_state.bending_axis = st.selectbox(
        "Bending Axis for Lateral Analysis",
        ["strong", "weak"],
        index=["strong", "weak"].index(
            st.session_state.get("bending_axis", "strong")
        ),
    )

st.markdown("---")

# ============================================================================
# Corrosion Allowance
# ============================================================================
st.subheader("Corrosion Allowance")

corrosion_enabled = st.checkbox(
    "Enable corrosion analysis",
    value=st.session_state.get("corrosion_enabled", False),
)
st.session_state["corrosion_enabled"] = corrosion_enabled

# Resolve the active section (corroded or nominal)
active_section = nominal

if corrosion_enabled:
    cc1, cc2, cc3 = st.columns(3)

    with cc1:
        design_life = st.number_input(
            "Design Life (years)",
            min_value=5.0, max_value=100.0,
            value=st.session_state.get("corrosion_design_life", 35.0),
            step=5.0, format="%.0f",
        )
        st.session_state["corrosion_design_life"] = design_life

    with cc2:
        env_options = list(CORROSION_RATES.keys())
        env_idx = env_options.index(
            st.session_state.get("corrosion_environment", "Buried (disturbed)")
        ) if st.session_state.get("corrosion_environment") in env_options else 2
        environment = st.selectbox("Environment", env_options, index=env_idx)
        st.session_state["corrosion_environment"] = environment

    with cc3:
        coat_options = list(COATING_REDUCTION.keys())
        coat_idx = coat_options.index(
            st.session_state.get("corrosion_coating", "None")
        ) if st.session_state.get("corrosion_coating") in coat_options else 0
        coating = st.selectbox("Coating", coat_options, index=coat_idx)
        st.session_state["corrosion_coating"] = coating

    # Compute corrosion parameters
    cp = compute_corrosion_params(design_life if design_life is not None else 35.0, environment, coating)
    st.session_state["corrosion_rate"] = cp.corrosion_rate
    st.session_state["corrosion_t_loss"] = cp.t_loss_per_side

    # Show computed values
    m1, m2, m3 = st.columns(3)
    m1.metric("Corrosion Rate", f"{cp.corrosion_rate:.2f} mils/yr")
    m2.metric("Loss per Side", f"{cp.t_loss_per_side:.4f} in")
    m3.metric("Total Loss (both sides)", f"{2 * cp.t_loss_per_side:.4f} in")

    # Apply corrosion
    try:
        cor = corroded_section(nominal, cp.t_loss_per_side)
        active_section = cor

        # Comparison table
        def pct_red(a, b):
            return f"{100 * (a - b) / a:.1f}%" if a > 0 else "-"

        comparison = pd.DataFrame({
            "Property": [
                "Flange tf (in)", "Web tw (in)", "Area (in\u00b2)",
                "Ix (in\u2074)", "Iy (in\u2074)",
                "Sx (in\u00b3)", "Sy (in\u00b3)",
                "Mp strong (kip-in)", "Mp weak (kip-in)",
            ],
            "Nominal": [
                f"{nominal.tf:.3f}", f"{nominal.tw:.3f}", f"{nominal.area:.2f}",
                f"{nominal.Ix:.2f}", f"{nominal.Iy:.2f}",
                f"{nominal.Sx:.2f}", f"{nominal.Sy:.3f}",
                f"{nominal.Mp_strong:.1f}", f"{nominal.Mp_weak:.1f}",
            ],
            "Corroded": [
                f"{cor.tf:.3f}", f"{cor.tw:.3f}", f"{cor.area:.2f}",
                f"{cor.Ix:.2f}", f"{cor.Iy:.2f}",
                f"{cor.Sx:.2f}", f"{cor.Sy:.3f}",
                f"{cor.Mp_strong:.1f}", f"{cor.Mp_weak:.1f}",
            ],
            "Reduction": [
                pct_red(nominal.tf, cor.tf), pct_red(nominal.tw, cor.tw),
                pct_red(nominal.area, cor.area),
                pct_red(nominal.Ix, cor.Ix), pct_red(nominal.Iy, cor.Iy),
                pct_red(nominal.Sx, cor.Sx), pct_red(nominal.Sy, cor.Sy),
                pct_red(nominal.Mp_strong, cor.Mp_strong),
                pct_red(nominal.Mp_weak, cor.Mp_weak),
            ],
        })
        st.dataframe(comparison, width="stretch", hide_index=True)

    except ValueError as e:
        st.error(str(e))

# Store the active section for downstream pages
st.session_state["section"] = active_section

st.markdown("---")

# Computed properties summary (uses active section)
st.subheader("Computed Design Properties")

axis = st.session_state.bending_axis
EI = active_section.EI_strong if axis == "strong" else active_section.EI_weak
My = active_section.My_strong if axis == "strong" else active_section.My_weak
Mp = active_section.Mp_strong if axis == "strong" else active_section.Mp_weak

c1, c2, c3, c4 = st.columns(4)
c1.metric("EI (lb-in\u00b2)", f"{EI:.2e}")
c2.metric("M_y (kip-in)", f"{My:.1f}")
c3.metric("M_p (kip-in)", f"{Mp:.1f}")
c4.metric("F_y (ksi)", f"{active_section.fy:.0f}")

if corrosion_enabled and active_section.name != nominal.name:
    st.caption(f"Values shown for corroded section: {active_section.name}")

st.markdown("---")

# Pile sketch
st.subheader("Pile Configuration Summary")
embed = st.session_state.pile_embedment
display_section = active_section.name if corrosion_enabled and active_section.name != nominal.name else section_name
st.markdown(f"""
| Parameter | Value |
|-----------|-------|
| Section | {display_section} |
| Embedment | {embed:.1f} ft |
| Installation | {st.session_state.pile_type} |
| Head condition | {st.session_state.head_condition} |
| Bending axis | {axis} axis |
| Pile weight in ground | {active_section.weight * embed:.0f} lbs |
""")
