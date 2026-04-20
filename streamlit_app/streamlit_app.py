"""SPORK — Solar Pile Optimization & Report Kit."""

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="SPORK - Solar Pile Optimization & Report Kit",
    page_icon=":material/anchor:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Initialize all session state defaults."""
    defaults = {
        # Project
        "project_name": "",
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
        "adfreeze_uplift": 0.0,
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
        "group_x_spacing": 36.0,
        "group_y_spacing": 36.0,
        "group_head_condition": "Free",
        # Structural check
        "above_grade": 4.0,
        "K_factor": 2.1,
        # Frost
        "frost_region": "Southern states",
        "frost_depth_in": 0.0,
        "frost_method": "Regional lookup",
        # Liquefaction
        "liq_a_max": 0.2,
        "liq_Mw": 7.5,
        "liq_fines_content": 15.0,
        # Service deflection
        "service_defl_limit": 0.50,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            # If a page-level shadow exists ("_" + key), prefer it so values
            # preserved across page-nav by the shadow-key pattern are not
            # clobbered back to defaults when init runs on every page switch.
            shadow_key = "_" + key
            st.session_state[key] = st.session_state.get(shadow_key, val)


init_session_state()

_PAGES = Path(__file__).parent / "pages"


def _home():
    _LOGO = Path(__file__).parent / "assets" / "bowman_logo.png"
    if _LOGO.exists():
        st.image(str(_LOGO), width=280)

    st.title("Solar Pile Optimization & Report Kit")
    st.caption(
        "Axial capacity \u00b7 Lateral analysis \u00b7 p-y curves \u00b7 "
        "Group effects \u00b7 FEM (BNWF) \u00b7 ASCE 7 load combinations"
    )

    st.markdown("---")
    st.markdown(
        "Use the **sidebar** to navigate. "
        "Start with the **Inputs** section, then review results in **Analysis**."
    )


# -- Build page objects -------------------------------------------------------
_home_page = st.Page(_home, title="Home", icon=":material/anchor:", default=True)

_nav = {
    "": [_home_page],
    "Inputs": [
        st.Page(str(_PAGES / "01_Project_Setup.py"), title="Project Setup", icon=":material/folder_open:"),
        st.Page(str(_PAGES / "02_Soil_Profile.py"), title="Soil Profile", icon=":material/layers:"),
        st.Page(str(_PAGES / "03_Pile_Properties.py"), title="Pile Properties", icon=":material/construction:"),
        st.Page(str(_PAGES / "04_Loading.py"), title="Loading", icon=":material/fitness_center:"),
    ],
    "Design": [
        st.Page(str(_PAGES / "05_Pile_Optimization.py"), title="Pile Optimization", icon=":material/target:"),
    ],
    "Analysis": [
        st.Page(str(_PAGES / "06_Axial_Capacity.py"), title="Axial Capacity", icon=":material/arrow_downward:"),
        st.Page(str(_PAGES / "07_Lateral_Analysis.py"), title="Lateral Analysis", icon=":material/swap_horiz:"),
        st.Page(str(_PAGES / "08_Group_Analysis.py"), title="Group Analysis", icon=":material/grid_view:"),
        st.Page(str(_PAGES / "09_FEM_Analysis.py"), title="FEM Analysis", icon=":material/bar_chart:"),
        st.Page(str(_PAGES / "10_Cable_Management.py"), title="Cable Management", icon=":material/electrical_services:"),
    ],
    "Checks": [
        st.Page(str(_PAGES / "11_Structural_Check.py"), title="Structural Check", icon=":material/verified:"),
        st.Page(str(_PAGES / "12_Liquefaction.py"), title="Liquefaction", icon=":material/water:"),
        st.Page(str(_PAGES / "13_Installation_QC.py"), title="Installation QC", icon=":material/handyman:"),
    ],
    "Output": [
        st.Page(str(_PAGES / "14_Export_Report.py"), title="Export Report", icon=":material/description:"),
    ],
}

pg = st.navigation(_nav, expanded=True)
pg.run()
