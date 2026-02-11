"""Page 14: Export PDF Report - professional report generation."""

import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.pdf_export import generate_report, ReportData
from core.sections import get_section
from core.soil import SoilLayer, SoilProfile, SoilType
from core.loads import LoadInput

st.header("Export PDF Report")
st.caption("Generate a professional PDF report of your pile design analysis.")

# ============================================================================
# Check what analyses have been completed
# ============================================================================
has_soil = bool(st.session_state.get("soil_layers"))
has_section = bool(st.session_state.get("pile_section"))
has_axial = "axial_result" in st.session_state
has_lateral = "lateral_result" in st.session_state
has_bnwf = "bnwf_result" in st.session_state
has_group = "group_result" in st.session_state
has_optimization = "optimization_result" in st.session_state
has_topl = "_topl_result" in st.session_state
has_frost = "frost_result" in st.session_state
has_structural = "structural_result" in st.session_state
has_service_defl = "service_defl_result" in st.session_state
has_min_embed = "min_embed_result" in st.session_state
has_liquefaction = "liq_result" in st.session_state
has_install_qc = "installation_qc_driven" in st.session_state or "installation_qc_helical" in st.session_state

st.subheader("Analysis Status")
status_items = [
    ("Soil Profile", has_soil),
    ("Pile Section", has_section),
    ("TOPL Import", has_topl),
    ("Pile Optimization", has_optimization),
    ("Axial Capacity", has_axial),
    ("Lateral Analysis", has_lateral),
    ("FEM Analysis (BNWF)", has_bnwf),
    ("Frost Depth Check", has_frost),
    ("AISC Structural", has_structural),
    ("Service Deflection", has_service_defl),
    ("Min Embedment", has_min_embed),
    ("Liquefaction", has_liquefaction),
    ("Installation QC", has_install_qc),
    ("Group Analysis", has_group),
]
cols = st.columns(4)
for i, (name, available) in enumerate(status_items):
    with cols[i % 4]:
        if available:
            st.success(name)
        else:
            st.info(f"{name} (skipped)")

if not has_soil or not has_section:
    st.warning("At minimum, define a soil profile and select a pile section before exporting.")
    st.stop()

st.markdown("---")

# ============================================================================
# Report Options
# ============================================================================
st.subheader("Report Settings")

col1, col2 = st.columns(2)
with col1:
    project_number = st.text_input("Project Number", value="")
    engineer_name = st.text_input("Engineer of Record", value="")
with col2:
    report_date = st.date_input("Report Date", value=datetime.now())
    above_grade = st.number_input(
        "Above-grade pile length (ft)",
        min_value=0.0,
        value=st.session_state.get("lever_arm", 4.0),
        step=0.5, format="%.1f",
        help="Pile length above the ground surface (reveal height)."
    )

st.markdown("**Design Limits**")
lim1, lim2, lim3 = st.columns(3)
with lim1:
    top_defl_limit = st.number_input("Top Deflection Limit (in)", value=4.0, step=0.5, format="%.1f")
with lim2:
    grade_defl_limit = st.number_input("Grade Deflection Limit (in)", value=1.0, step=0.25, format="%.2f")
with lim3:
    bottom_defl_limit = st.number_input("Bottom Deflection Limit (in)", value=0.1, step=0.05, format="%.2f")

st.markdown("---")

# ============================================================================
# Build ReportData from session state
# ============================================================================
def _extract_topl_manufacturer() -> str:
    key = st.session_state.get("_topl_cache_key", "")
    if ":" in key:
        return key.split(":")[0]
    return ""

def _extract_topl_filename() -> str:
    key = st.session_state.get("_topl_cache_key", "")
    parts = key.split(":")
    if len(parts) >= 2:
        return parts[1]
    return ""

def build_report_data() -> ReportData:
    """Assemble ReportData from Streamlit session state."""
    section = st.session_state.get("section") or get_section(st.session_state.pile_section)
    nominal_section = st.session_state.get("nominal_section") or section

    # Build SoilProfile
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

    # Build LoadInput
    load_input = LoadInput(
        dead=st.session_state.get("dead_load", 0),
        live=st.session_state.get("live_load", 0),
        snow=st.session_state.get("snow_load", 0),
        wind_down=st.session_state.get("wind_down", 0),
        wind_up=st.session_state.get("wind_up", 0),
        wind_lateral=st.session_state.get("wind_lateral", 0),
        wind_moment=st.session_state.get("wind_moment", 0),
        seismic_vertical=st.session_state.get("seismic_vertical", 0),
        seismic_lateral=st.session_state.get("seismic_lateral", 0),
        seismic_moment=st.session_state.get("seismic_moment", 0),
        lever_arm=st.session_state.get("lever_arm", 4.0),
    )

    return ReportData(
        project_name=st.session_state.get("project_name", "Untitled"),
        project_number=project_number,
        project_location=st.session_state.get("project_location", ""),
        project_notes=st.session_state.get("project_notes", ""),
        engineer_of_record=engineer_name,
        report_date=report_date.strftime("%B %d, %Y"),
        top_deflection_limit=top_defl_limit,
        grade_deflection_limit=grade_defl_limit,
        bottom_deflection_limit=bottom_defl_limit,
        section=section,
        pile_embedment=st.session_state.get("pile_embedment", 10.0),
        above_grade=above_grade,
        pile_type=st.session_state.get("pile_type", "driven"),
        head_condition=st.session_state.get("head_condition", "free"),
        bending_axis=st.session_state.get("bending_axis", "strong"),
        yield_strength=section.fy,
        loading_type="Cyclic" if st.session_state.get("cyclic_loading") else "Static",
        soil_profile=profile,
        soil_layers_raw=st.session_state.soil_layers,
        water_table_depth=st.session_state.get("water_table_depth"),
        load_input=load_input,
        design_method=st.session_state.get("design_method", "LRFD"),
        axial_result=st.session_state.get("axial_result"),
        lateral_result=st.session_state.get("lateral_result"),
        group_result=st.session_state.get("group_result"),
        bnwf_result=st.session_state.get("bnwf_result"),
        group_n_rows=st.session_state.get("group_n_rows", 1),
        group_n_cols=st.session_state.get("group_n_cols", 1),
        group_spacing=st.session_state.get("group_spacing", 36.0),
        corrosion_enabled=st.session_state.get("corrosion_enabled", False),
        corrosion_design_life=st.session_state.get("corrosion_design_life", 0.0),
        corrosion_environment=st.session_state.get("corrosion_environment", ""),
        corrosion_coating=st.session_state.get("corrosion_coating", ""),
        corrosion_rate=st.session_state.get("corrosion_rate", 0.0),
        corrosion_t_loss=st.session_state.get("corrosion_t_loss", 0.0),
        nominal_section=nominal_section,
        optimization_result=st.session_state.get("optimization_result"),
        # TOPL import
        topl_result=st.session_state.get("_topl_result"),
        topl_column_selected=st.session_state.get("topl_column_select", ""),
        topl_manufacturer=_extract_topl_manufacturer(),
        topl_filename=_extract_topl_filename(),
        # New engineering checks
        frost_result=st.session_state.get("frost_result"),
        structural_result=st.session_state.get("structural_result"),
        service_defl_result=st.session_state.get("service_defl_result"),
        service_defl_limit=st.session_state.get("service_defl_limit", 0.5),
        min_embed_result=st.session_state.get("min_embed_result"),
        liq_result=st.session_state.get("liq_result"),
        installation_qc_driven=st.session_state.get("installation_qc_driven"),
        installation_qc_helical=st.session_state.get("installation_qc_helical"),
    )


# ============================================================================
# Generate and download
# ============================================================================
if st.button("Generate PDF Report", type="primary", width="stretch"):
    with st.spinner("Generating PDF report..."):
        try:
            report_data = build_report_data()
            _logo = Path(__file__).parent.parent / "assets" / "bowman_logo.png"
            pdf_bytes = generate_report(
                report_data,
                logo_path=str(_logo) if _logo.exists() else None,
            )
        except Exception as e:
            st.error(f"Error generating report: {e}")
            st.stop()

    filename = f"{st.session_state.project_name.replace(' ', '_')}_Report.pdf"
    st.success(f"Report generated successfully ({len(pdf_bytes) / 1024:.0f} KB)")

    st.download_button(
        label="Download PDF Report",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        type="primary",
        width="stretch",
    )
