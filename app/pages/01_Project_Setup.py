"""Page 1: Project setup and save/load."""

import json
import os
from pathlib import Path

import streamlit as st

PROJECTS_DIR = Path(__file__).parent.parent / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)

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

# --- Save / Load ---
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


def save_project():
    data = {}
    for key in SAVEABLE_KEYS:
        val = st.session_state.get(key)
        # Convert soil layers (list of dicts) for JSON
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

    filename = st.session_state.project_name.replace(" ", "_") + ".json"
    filepath = PROJECTS_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def load_project(filepath):
    with open(filepath) as f:
        data = json.load(f)
    for key in SAVEABLE_KEYS:
        if key in data:
            st.session_state[key] = data[key]


col_save, col_load = st.columns(2)

with col_save:
    st.subheader("Save Project")
    if st.button("Save Current Project", type="primary"):
        path = save_project()
        st.success(f"Saved to {path.name}")

with col_load:
    st.subheader("Load Project")
    project_files = sorted(PROJECTS_DIR.glob("*.json"))
    if project_files:
        selected = st.selectbox(
            "Select project file",
            project_files,
            format_func=lambda p: p.stem.replace("_", " "),
        )
        if st.button("Load Selected Project"):
            load_project(selected)
            st.success(f"Loaded {selected.stem}")
            st.rerun()
    else:
        st.info("No saved projects found.")
