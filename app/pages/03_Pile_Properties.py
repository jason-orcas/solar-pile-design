"""Page 3: Pile section and properties input."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.sections import SECTIONS, get_section, list_sections

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

    section = get_section(section_name)

    # Display section properties
    st.markdown("**Section Properties:**")
    props = {
        "Depth (in)": f"{section.depth:.2f}",
        "Flange Width (in)": f"{section.width:.2f}",
        "Area (in\u00b2)": f"{section.area:.2f}",
        "Weight (plf)": f"{section.weight:.1f}",
        "I_x (in\u2074)": f"{section.Ix:.1f}",
        "I_y (in\u2074)": f"{section.Iy:.2f}",
        "S_x (in\u00b3)": f"{section.Sx:.2f}",
        "S_y (in\u00b3)": f"{section.Sy:.3f}",
        "Z_x (in\u00b3)": f"{section.Zx:.2f}",
        "Z_y (in\u00b3)": f"{section.Zy:.2f}",
        "Perimeter (in)": f"{section.perimeter:.1f}",
        "Tip Area (in\u00b2)": f"{section.tip_area:.1f}",
    }
    for k, v in props.items():
        st.text(f"  {k}: {v}")

with col2:
    st.subheader("Installation & Geometry")

    st.session_state.pile_embedment = st.number_input(
        "Embedment Depth (ft)",
        min_value=1.0, max_value=50.0,
        value=st.session_state.get("pile_embedment", 10.0),
        step=0.5,
    )

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

# Computed properties summary
st.subheader("Computed Design Properties")

axis = st.session_state.bending_axis
EI = section.EI_strong if axis == "strong" else section.EI_weak
My = section.My_strong if axis == "strong" else section.My_weak
Mp = section.Mp_strong if axis == "strong" else section.Mp_weak

c1, c2, c3, c4 = st.columns(4)
c1.metric("EI (lb-in\u00b2)", f"{EI:.2e}")
c2.metric("M_y (kip-in)", f"{My:.1f}")
c3.metric("M_p (kip-in)", f"{Mp:.1f}")
c4.metric("F_y (ksi)", f"{section.fy:.0f}")

st.markdown("---")

# Pile sketch
st.subheader("Pile Configuration Summary")
embed = st.session_state.pile_embedment
st.markdown(f"""
| Parameter | Value |
|-----------|-------|
| Section | {section_name} |
| Embedment | {embed:.1f} ft |
| Installation | {st.session_state.pile_type} |
| Head condition | {st.session_state.head_condition} |
| Bending axis | {axis} axis |
| Pile weight in ground | {section.weight * embed:.0f} lbs |
""")
