"""Page 1: Project setup and download/upload."""

import json

import streamlit as st

st.header("Project Setup")

col1, col2 = st.columns(2)
with col1:
    st.session_state.project_name = st.text_input(
        "Project Name", value=st.session_state.get("project_name", "New Project"),
    )
    st.session_state.project_location = st.text_input(
        "Site Location", value=st.session_state.get("project_location", ""),
    )

with col2:
    st.session_state.project_notes = st.text_area(
        "Project Notes", value=st.session_state.get("project_notes", ""), height=120,
    )

st.markdown("---")

# --- Download / Upload ---
SAVEABLE_KEYS = [
    "project_name", "project_location", "project_notes",
    "soil_layers", "water_table_depth",
    "pile_section", "pile_embedment", "pile_type", "head_condition", "bending_axis",
    "dead_load", "live_load", "snow_load",
    "wind_down", "wind_up", "wind_lateral", "wind_moment", "lever_arm",
    "seismic_lateral", "seismic_vertical", "seismic_moment",
    "design_method", "axial_method", "FS_compression", "FS_tension", "cyclic_loading",
    "group_n_rows", "group_n_cols", "group_spacing",
]


def build_project_json() -> str:
    """Serialize current session state to a JSON string."""
    data = {}
    for key in SAVEABLE_KEYS:
        val = st.session_state.get(key)
        if key == "soil_layers" and val:
            serialized = []
            for layer in val:
                d = dict(layer)
                if "soil_type" in d:
                    d["soil_type"] = d["soil_type"].value if hasattr(d["soil_type"], "value") else str(d["soil_type"])
                serialized.append(d)
            data[key] = serialized
        else:
            data[key] = val
    return json.dumps(data, indent=2, default=str)


col_save, col_load = st.columns(2)

with col_save:
    st.subheader("Download Project")
    filename = st.session_state.get("project_name", "New_Project").replace(" ", "_") + ".json"
    st.download_button(
        label="Download Project File",
        data=build_project_json(),
        file_name=filename,
        mime="application/json",
        type="primary",
        use_container_width=True,
    )

with col_load:
    st.subheader("Upload Project")
    uploaded = st.file_uploader("Upload a project JSON file", type=["json"])
    if uploaded is not None:
        try:
            data = json.loads(uploaded.read().decode("utf-8"))
            for key in SAVEABLE_KEYS:
                if key in data:
                    st.session_state[key] = data[key]
            st.success(f"Loaded project: {data.get('project_name', uploaded.name)}")
            st.rerun()
        except (json.JSONDecodeError, UnicodeDecodeError):
            st.error("Invalid project file. Please upload a valid JSON file.")
