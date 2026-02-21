"""Page 1: Project setup, TOPL import, and download/upload."""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.topl_parser import (
    Manufacturer,
    TOPLParseResult,
    parse_topl,
    topl_loads_to_session_dict,
)

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

# ============================================================================
# Import TOPL Document
# ============================================================================
st.markdown("---")
st.subheader("Import TOPL Document")
st.caption(
    "Upload a manufacturer Top-of-Pile-Load document to auto-populate project "
    "info and design loads. Supported: ATI (PDF), Nevados (PDF), Nextpower (XLSX)."
)

_MFR_OPTIONS = ["-- Select Manufacturer --"] + [m.value for m in Manufacturer]
_MFR_EXTENSIONS = {
    Manufacturer.ATI: ["pdf"],
    Manufacturer.NEVADOS: ["pdf"],
    Manufacturer.NEXTPOWER: ["xlsx"],
}

mfr_choice = st.selectbox("Manufacturer", _MFR_OPTIONS, key="topl_mfr_select")

if mfr_choice != _MFR_OPTIONS[0]:
    mfr_enum = Manufacturer(mfr_choice)
    exts = _MFR_EXTENSIONS[mfr_enum]
    ext_label = ", ".join(f".{e}" for e in exts)

    uploaded = st.file_uploader(
        f"Upload TOPL Document ({ext_label})",
        type=exts,
        key="topl_file_uploader",
    )

    if uploaded is not None:
        # Parse on fresh upload or if file changed
        file_bytes = uploaded.getvalue()
        cache_key = f"{mfr_choice}:{uploaded.name}:{len(file_bytes)}"

        if st.session_state.get("_topl_cache_key") != cache_key:
            result = parse_topl(file_bytes, uploaded.name, mfr_enum)
            st.session_state["_topl_result"] = result
            st.session_state["_topl_cache_key"] = cache_key

        result: TOPLParseResult = st.session_state.get("_topl_result")

        if result is None:
            st.warning("No parse result available. Try re-uploading.")
        elif not result.success:
            for err in result.errors:
                st.error(err)
        else:
            # --- Warnings ---
            if result.warnings:
                with st.expander(f"Warnings ({len(result.warnings)})", expanded=False):
                    for w in result.warnings:
                        st.warning(w)

            # --- Project info ---
            pi = result.project_info
            info_parts = []
            if pi.project_name:
                info_parts.append(f"**Project:** {pi.project_name}")
            if pi.location:
                info_parts.append(f"**Location:** {pi.location}")
            params = []
            if pi.wind_speed_mph is not None:
                params.append(f"Wind: {pi.wind_speed_mph} mph")
            if pi.ground_snow_psf is not None:
                params.append(f"Snow: {pi.ground_snow_psf} psf")
            if pi.seismic_sds is not None:
                params.append(f"SDS: {pi.seismic_sds}")
            if pi.exposure:
                params.append(f"Exp: {pi.exposure}")
            if pi.risk_category:
                params.append(f"Risk: {pi.risk_category}")
            if pi.asce_version:
                params.append(f"Code: {pi.asce_version}")
            if params:
                info_parts.append(" | ".join(params))

            with st.expander("Extracted Project Info", expanded=True):
                for part in info_parts:
                    st.markdown(part)

            # --- Column selector ---
            options = result.column_options
            if not options:
                st.error("No column/post options parsed from document.")
            else:
                selected = st.selectbox(
                    "Select Column / Post Type",
                    options,
                    key="topl_column_select",
                    help="Choose which pile position to import loads for.",
                )

                loads = result.loads_by_column.get(selected)
                if loads is None:
                    st.error(f"No data for selection: {selected}")
                else:
                    # --- Editable load preview ---
                    st.markdown("#### Extracted Loads *(edit before applying)*")
                    c_grav, c_wind, c_seis = st.columns(3)

                    with c_grav:
                        st.markdown("**Gravity**")
                        ed_dead = st.number_input(
                            "Dead Load (lbs)", value=round(loads.dead_load, 1),
                            step=10.0, format="%.1f", key="topl_ed_dead",
                        )
                        ed_snow = st.number_input(
                            "Snow Load (lbs)", value=round(loads.snow_load, 1),
                            step=10.0, format="%.1f", key="topl_ed_snow",
                        )

                    with c_wind:
                        st.markdown("**Wind**")
                        ed_up = st.number_input(
                            "Uplift (lbs)", value=round(loads.wind_up, 1),
                            step=10.0, format="%.1f", key="topl_ed_up",
                        )
                        ed_down = st.number_input(
                            "Downforce (lbs)", value=round(loads.wind_down, 1),
                            step=10.0, format="%.1f", key="topl_ed_down",
                        )
                        ed_lateral = st.number_input(
                            "Lateral (lbs)", value=round(loads.wind_lateral, 1),
                            step=10.0, format="%.1f", key="topl_ed_lateral",
                        )
                        ed_moment = st.number_input(
                            "Moment (ft-lbs)", value=round(loads.wind_moment, 1),
                            step=10.0, format="%.1f", key="topl_ed_moment",
                        )

                    with c_seis:
                        st.markdown("**Seismic & Geometry**")
                        ed_slat = st.number_input(
                            "Seismic Lateral (lbs)", value=round(loads.seismic_lateral, 1),
                            step=10.0, format="%.1f", key="topl_ed_slat",
                        )
                        ed_svert = st.number_input(
                            "Seismic Vertical (lbs)", value=round(loads.seismic_vertical, 1),
                            step=10.0, format="%.1f", key="topl_ed_svert",
                        )
                        ed_smom = st.number_input(
                            "Seismic Moment (ft-lbs)", value=round(loads.seismic_moment, 1),
                            step=10.0, format="%.1f", key="topl_ed_smom",
                        )
                        ed_lever = st.number_input(
                            "Lever Arm (ft)", value=round(loads.lever_arm, 2),
                            step=0.25, format="%.2f", key="topl_ed_lever",
                        )

                    # --- Apply button ---
                    if st.button(
                        "Apply TOPL Loads to Project",
                        type="primary",
                        width="stretch",
                    ):
                        session_dict = topl_loads_to_session_dict(pi, loads)
                        # Override with user-edited values
                        # Guard against None from cleared number_input fields
                        session_dict["dead_load"] = ed_dead if ed_dead is not None else 0.0
                        session_dict["snow_load"] = ed_snow if ed_snow is not None else 0.0
                        session_dict["wind_up"] = ed_up if ed_up is not None else 0.0
                        session_dict["wind_down"] = ed_down if ed_down is not None else 0.0
                        session_dict["wind_lateral"] = ed_lateral if ed_lateral is not None else 0.0
                        session_dict["wind_moment"] = ed_moment if ed_moment is not None else 0.0
                        session_dict["seismic_lateral"] = ed_slat if ed_slat is not None else 0.0
                        session_dict["seismic_vertical"] = ed_svert if ed_svert is not None else 0.0
                        session_dict["seismic_moment"] = ed_smom if ed_smom is not None else 0.0
                        session_dict["lever_arm"] = ed_lever if ed_lever is not None else 4.0

                        for key, val in session_dict.items():
                            st.session_state[key] = val

                        st.success(
                            f"TOPL loads applied from {pi.manufacturer} — "
                            f"{selected}. Navigate to the Loading page to review."
                        )
                        st.balloons()

# ============================================================================
# Download / Upload Project JSON
# ============================================================================
st.markdown("---")

SAVEABLE_KEYS = [
    "project_name", "project_location", "project_notes",
    "soil_layers", "water_table_depth",
    "pile_section", "pile_embedment", "pile_type", "head_condition", "bending_axis",
    "dead_load", "live_load", "snow_load",
    "wind_down", "wind_up", "wind_lateral", "wind_moment", "lever_arm",
    "seismic_lateral", "seismic_vertical", "seismic_moment",
    "design_method", "axial_method", "FS_compression", "FS_tension", "cyclic_loading",
    "group_n_rows", "group_n_cols", "group_spacing",
    "group_x_spacing", "group_y_spacing",
    "group_piles", "group_loads", "group_head_condition",
    "group_Q_comp", "group_Q_tens",
    "above_grade", "K_factor",
    "frost_region", "frost_depth_in", "frost_method",
    "liq_a_max", "liq_Mw", "liq_fines_content",
    "service_defl_limit",
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
        width="stretch",
    )

with col_load:
    st.subheader("Upload Project")
    uploaded = st.file_uploader("Upload a project JSON file", type=["json"])
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        upload_key = f"{uploaded.name}:{len(file_bytes)}"
        if st.session_state.get("_project_upload_key") != upload_key:
            try:
                data = json.loads(file_bytes.decode("utf-8"))
                for key in SAVEABLE_KEYS:
                    if key in data:
                        st.session_state[key] = data[key]
                st.session_state["_project_upload_key"] = upload_key
                st.success(f"Loaded project: {data.get('project_name', uploaded.name)}")
                st.rerun()
            except (json.JSONDecodeError, UnicodeDecodeError):
                st.error("Invalid project file. Please upload a valid JSON file.")
        else:
            st.success(f"Project loaded: {st.session_state.get('project_name', uploaded.name)}")
