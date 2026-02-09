"""Solar Pile Design Tool — Main Streamlit Application."""

import streamlit as st

st.set_page_config(
    page_title="Solar Pile Design Tool",
    page_icon="\u2693",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Initialize all session state defaults."""
    defaults = {
        # Project
        "project_name": "New Project",
        "project_location": "",
        "project_notes": "",
        # Soil layers
        "soil_layers": [],
        "water_table_depth": None,
        # Pile
        "pile_section": "W6x9",
        "pile_embedment": 10.0,
        "pile_type": "driven",
        "head_condition": "free",
        "bending_axis": "strong",
        # Loads
        "dead_load": 400.0,
        "live_load": 0.0,
        "snow_load": 0.0,
        "wind_down": 0.0,
        "wind_up": 1500.0,
        "wind_lateral": 1500.0,
        "wind_moment": 0.0,
        "lever_arm": 4.0,
        "seismic_lateral": 0.0,
        "seismic_vertical": 0.0,
        "seismic_moment": 0.0,
        "design_method": "LRFD",
        # Analysis flags
        "axial_method": "auto",
        "FS_compression": 2.5,
        "FS_tension": 3.0,
        "cyclic_loading": False,
        # Group
        "group_n_rows": 1,
        "group_n_cols": 1,
        "group_spacing": 36.0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()

st.title("Solar Pile Foundation Design Tool")
st.caption("Axial capacity \u00b7 Lateral analysis \u00b7 p-y curves \u00b7 Group effects \u00b7 ASCE 7 load combinations")

st.markdown("---")
st.markdown(
    "Use the **sidebar pages** to input project data and run analyses. "
    "Start with **Project Setup**, then work through each page sequentially."
)

st.sidebar.success("Select a page above to begin.")
