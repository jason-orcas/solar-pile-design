"""Page 2: Soil profile input — layers, SPT data, parameter derivation."""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.soil import (
    SoilLayer, SoilProfile, SoilType, PYModel, PY_MODEL_PARAMS,
    AxialSoilZone,
    correct_N_overburden, build_soil_layer_from_dict,
)
from core.frost import (
    FROST_DEPTH_TABLE, STEFAN_C,
    frost_depth_regional, frost_depth_stefan, frost_check,
    adfreeze_from_profile, adfreeze_service_check,
)

st.header("Soil Profile")

# --- Water table ---
col_wt1, col_wt2 = st.columns([1, 3])
with col_wt1:
    has_wt = st.checkbox("Water table present?", value=st.session_state.get("water_table_depth") is not None)
with col_wt2:
    if has_wt:
        st.session_state.water_table_depth = st.number_input(
            "Water table depth (ft)", min_value=0.0, value=st.session_state.get("water_table_depth") or 10.0, step=0.5, format="%.1f",
        )
    else:
        st.session_state.water_table_depth = None

st.markdown("---")

# --- Layer input ---
st.subheader("Soil Layers")
st.caption("Define layers from top down. At minimum, provide soil type and SPT N-value.")

if "soil_layers" not in st.session_state or not st.session_state.soil_layers:
    st.session_state.soil_layers = []

# Add layer form
with st.expander("Add New Layer", expanded=len(st.session_state.soil_layers) == 0):
    # Row 1: Depths + Soil classification
    r1a, r1b, r1c = st.columns([1, 1, 2])
    with r1a:
        new_top = st.number_input("Top Depth (ft)", min_value=0.0, value=0.0, step=0.5, format="%.1f", key="new_top")
    with r1b:
        new_bot = st.number_input("Bottom Depth (ft)", min_value=0.5, value=5.0, step=0.5, format="%.1f", key="new_bot")
    with r1c:
        new_type = st.selectbox("Soil Type", [t.value for t in SoilType], key="new_type")

    # Row 2: p-y model (full width) + description
    r2a, r2b = st.columns(2)
    with r2a:
        py_model_names = [m.value for m in PYModel]
        new_py_model = st.selectbox(
            "p-y Curve Model", py_model_names, index=0, key="new_py_model",
            help="Auto uses Matlock Soft Clay for clay/silt and API Sand for sand/gravel.",
        )
    with r2b:
        new_desc = st.text_input("Description", value="", key="new_desc", placeholder="e.g., Brown silty sand")

    # Row 3: Soil parameters
    r3a, r3b, r3c, r3d = st.columns(4)
    with r3a:
        new_N = st.number_input(
            "SPT N-value", min_value=0, value=0, step=1, key="new_N",
            help="Raw SPT blow count. Optional when explicit skin friction and end bearing "
                 "are provided below. Used for parameter estimation and liquefaction screening.",
        )
    with r3b:
        new_gamma = st.number_input("gamma (pcf)", min_value=0.0, value=0.0, step=5.0, format="%.0f", key="new_gamma", help="Unit weight. 0 = auto from soil type.")
    with r3c:
        new_phi = st.number_input("phi (deg)", min_value=0.0, value=0.0, step=1.0, format="%.0f", key="new_phi", help="Friction angle. 0 = auto from N-value.")
    with r3d:
        new_cu = st.number_input("c_u (psf)", min_value=0.0, value=0.0, step=100.0, format="%.0f", key="new_cu", help="Undrained shear strength. 0 = auto from N-value.")

    # Row 4: Explicit axial design parameters (optional — override correlations)
    st.caption("Axial design parameters *(optional — leave 0 to use correlations from N-value)*")
    r4a, r4b, r4c = st.columns(3)
    with r4a:
        new_fs_down = st.number_input(
            "Skin friction, downward (psf)", min_value=0.0, value=0.0,
            step=50.0, format="%.0f", key="new_fs_down",
            help="Explicit skin friction for compression. 0 = derive from soil parameters.",
        )
    with r4b:
        new_fs_up = st.number_input(
            "Skin friction, uplift (psf)", min_value=0.0, value=0.0,
            step=50.0, format="%.0f", key="new_fs_up",
            help="Explicit skin friction for tension/uplift. 0 = derive from soil parameters.",
        )
    with r4c:
        new_qb = st.number_input(
            "End bearing (psf)", min_value=0.0, value=0.0,
            step=100.0, format="%.0f", key="new_qb",
            help="Explicit end bearing capacity. 0 = derive from soil parameters. Only used at pile tip layer.",
        )

    # --- Model-specific parameters (shown when non-Auto model selected) ---
    _sel_model = PYModel(new_py_model)
    _needed = PY_MODEL_PARAMS.get(_sel_model, [])
    # Filter to only extra params (gamma/phi/c_u already above)
    _extra = [p for p in _needed if p not in ("gamma", "phi", "c_u")]

    _PARAM_UI = {
        "epsilon_50": ("epsilon_50 (strain)", 0.0, 0.0, 0.001, "%.4f",
                       "Strain at 50% ultimate. 0 = auto from c_u."),
        "J": ("J factor", 0.0, 0.5, 0.05, "%.2f",
              "Matlock J factor (0.25 shallow, 0.5 deep). 0 = auto."),
        "k_py": ("k (lb/in^3)", 0.0, 0.0, 10.0, "%.0f",
                 "Subgrade reaction modulus. 0 = auto from soil type."),
        "q_u": ("q_u — UCS (psf)", 0.0, 0.0, 500.0, "%.0f",
                "Unconfined compressive strength of rock."),
        "E_ir": ("E_ir — Initial rock modulus (psi)", 0.0, 0.0, 1000.0, "%.0f",
                 "Initial modulus of rock mass."),
        "RQD": ("RQD (%)", 0.0, 0.0, 5.0, "%.0f",
                "Rock Quality Designation."),
        "k_rm": ("k_rm — Strain factor", 0.0, 0.0005, 0.0001, "%.4f",
                 "Weak rock strain wedge factor."),
        "sigma_ci": ("sigma_ci — Intact UCS (psi)", 0.0, 0.0, 500.0, "%.0f",
                     "Intact rock uniaxial compressive strength (Hoek-Brown)."),
        "m_i": ("m_i — Material index", 0.0, 10.0, 1.0, "%.0f",
                "Hoek-Brown material constant."),
        "GSI": ("GSI", 0.0, 50.0, 5.0, "%.0f",
                "Geological Strength Index (0-100)."),
        "E_rock": ("E_rock — Rock modulus (psi)", 0.0, 0.0, 1000.0, "%.0f",
                   "Rock mass modulus (deformation)."),
        "G_max": ("G_max — Max shear modulus (psi)", 0.0, 0.0, 1000.0, "%.0f",
                  "Small-strain maximum shear modulus."),
        "poissons_ratio": ("Poisson's ratio", 0.0, 0.3, 0.05, "%.2f",
                           "Rock or soil Poisson's ratio."),
        "void_ratio": ("Void ratio", 0.0, 0.6, 0.05, "%.2f",
                       "Soil void ratio."),
        "C_u_uniformity": ("C_u — Uniformity coeff", 0.0, 2.0, 0.5, "%.1f",
                           "Coefficient of uniformity (D60/D10)."),
    }

    _adv_vals: dict = {}
    if _extra:
        # Exclude user_py_data from number inputs (handled separately)
        _num_extra = [p for p in _extra if p != "user_py_data"]
        if _num_extra:
            st.caption("Model-specific parameters:")
            cols_adv = st.columns(min(len(_num_extra), 3))
            for idx, param_name in enumerate(_num_extra):
                ui = _PARAM_UI.get(param_name)
                if ui:
                    label, mn, default, stp, fmt, hlp = ui
                    with cols_adv[idx % len(cols_adv)]:
                        _adv_vals[param_name] = st.number_input(
                            label, min_value=mn, value=default, step=stp,
                            format=fmt, key=f"new_{param_name}", help=hlp,
                        )

        if "user_py_data" in _extra:
            st.info("User-input p-y curves can be defined after adding the layer "
                    "(coming soon in a future update).")
    elif _sel_model != PYModel.AUTO:
        st.caption("This model uses standard soil parameters defined above.")

    if st.button("Add Layer", type="primary"):
        # Guard against None from cleared number_input fields
        _top = new_top if new_top is not None else 0.0
        _bot = new_bot if new_bot is not None else 0.5
        _N = new_N if new_N is not None else 0
        _gamma = new_gamma if new_gamma is not None else 0.0
        _phi = new_phi if new_phi is not None else 0.0
        _cu = new_cu if new_cu is not None else 0.0
        if _bot <= _top:
            st.error("Bottom depth must be greater than top depth.")
        else:
            _fs_down = new_fs_down if new_fs_down is not None else 0.0
            _fs_up = new_fs_up if new_fs_up is not None else 0.0
            _qb_val = new_qb if new_qb is not None else 0.0
            layer_data = {
                "top_depth": _top,
                "thickness": _bot - _top,
                "soil_type": new_type,
                "description": new_desc,
                "N_spt": _N if _N > 0 else None,
                "gamma": _gamma if _gamma > 0 else None,
                "phi": _phi if _phi > 0 else None,
                "c_u": _cu if _cu > 0 else None,
                "f_s_downward": _fs_down if _fs_down > 0 else None,
                "f_s_uplift": _fs_up if _fs_up > 0 else None,
                "q_b": _qb_val if _qb_val > 0 else None,
            }
            # Add p-y model if not Auto
            if _sel_model != PYModel.AUTO:
                layer_data["py_model"] = _sel_model.value
            # Add non-zero advanced parameters
            for _k, _v in _adv_vals.items():
                if _v and _v > 0:
                    layer_data[_k] = _v
            st.session_state.soil_layers.append(layer_data)
            st.success(f"Added layer: {new_desc or new_type} at {_top}-{_bot} ft")
            st.rerun()

# Display existing layers
if st.session_state.soil_layers:
    st.subheader("Current Layers")

    # Build SoilProfile for computed properties
    layers_obj = [build_soil_layer_from_dict(ld) for ld in st.session_state.soil_layers]
    profile = SoilProfile(layers=layers_obj, water_table_depth=st.session_state.water_table_depth)

    # Table display
    table_data = []
    for i, (ld, lo) in enumerate(zip(st.session_state.soil_layers, layers_obj)):
        sigma_v = profile.effective_stress_at(lo.mid_depth)
        N1_60 = correct_N_overburden(lo.N_60 or 0, sigma_v)
        table_data.append({
            "#": i + 1,
            "Depth (ft)": f"{lo.top_depth:.1f} - {lo.bottom_depth:.1f}",
            "Type": ld["soil_type"],
            "Description": ld.get("description", ""),
            "N_spt": ld.get("N_spt", "-"),
            "N_60": f"{lo.N_60:.1f}" if lo.N_60 else "-",
            "(N1)_60": f"{N1_60:.1f}" if N1_60 else "-",
            "gamma (pcf)": f"{lo.gamma or lo._estimate_gamma():.0f}",
            "phi' (deg)": f"{lo.get_phi(sigma_v):.1f}" if lo.get_phi(sigma_v) > 0 else "-",
            "c_u (psf)": f"{lo.get_cu():.0f}" if lo.get_cu() > 0 else "-",
            "sigma'_v mid (psf)": f"{sigma_v:.0f}",
            "f_s↓ (psf)": f"{ld['f_s_downward']:.0f}" if ld.get("f_s_downward") else "-",
            "f_s↑ (psf)": f"{ld['f_s_uplift']:.0f}" if ld.get("f_s_uplift") else "-",
            "q_b (psf)": f"{ld['q_b']:.0f}" if ld.get("q_b") else "-",
            "p-y Model": ld.get("py_model", "Auto") or "Auto",
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, width="stretch", hide_index=True)

    # Delete layer
    col_del1, col_del2 = st.columns([1, 3])
    with col_del1:
        del_idx = st.number_input("Layer # to delete", min_value=1, max_value=len(st.session_state.soil_layers), value=1)
    with col_del2:
        if st.button("Delete Layer"):
            _del = del_idx if del_idx is not None else 1
            st.session_state.soil_layers.pop(_del - 1)
            st.rerun()

    # --- Soil profile visualization ---
    st.subheader("Soil Profile Visualization")

    fig = go.Figure()

    color_map = {
        "Sand": "#F4D03F",
        "Gravel": "#D5D8DC",
        "Silt": "#A9CCE3",
        "Clay": "#A0522D",
        "Organic": "#2ECC71",
    }

    for lo in layers_obj:
        color = color_map.get(lo.soil_type.value, "#999999")
        fig.add_shape(
            type="rect",
            x0=0, x1=1,
            y0=-lo.bottom_depth, y1=-lo.top_depth,
            fillcolor=color, opacity=0.6,
            line=dict(width=1, color="black"),
        )
        label = f"{lo.description or lo.soil_type.value} (N={lo.N_spt})"
        fig.add_annotation(
            x=0.5, y=-(lo.top_depth + lo.thickness / 2),
            text=label, showarrow=False, font=dict(size=12),
        )

    # Water table line
    if st.session_state.water_table_depth is not None:
        fig.add_hline(
            y=-st.session_state.water_table_depth,
            line=dict(color="blue", width=2, dash="dash"),
            annotation_text="GWT",
        )

    max_d = max(lo.bottom_depth for lo in layers_obj)
    fig.update_layout(
        title="Soil Profile",
        yaxis_title="Depth (ft)",
        yaxis=dict(range=[-(max_d + 2), 1]),
        xaxis=dict(visible=False),
        height=400,
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

    # Effective stress plot
    st.subheader("Effective Stress Profile")
    depths_plot = [d * 0.5 for d in range(int(max_d * 2) + 1)]
    stresses = [profile.effective_stress_at(d) for d in depths_plot]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=stresses, y=[-d for d in depths_plot],
        mode="lines", name="sigma'_v",
        line=dict(color="red", width=2),
    ))
    fig2.update_layout(
        title="Effective Vertical Stress vs Depth",
        xaxis_title="sigma'_v (psf)",
        yaxis_title="Depth (ft)",
        height=400,
    )
    st.plotly_chart(fig2, width="stretch")

else:
    st.info("No layers defined yet. Add at least one soil layer to proceed.")

# ============================================================================
# Axial Soil Parameters (separate from lateral)
# ============================================================================
st.markdown("---")
st.subheader("Axial Design Parameters")
st.caption(
    "Optional: Define separate axial soil zones with explicit skin friction and "
    "end bearing values from the geotech report. These depth intervals can differ "
    "from the lateral soil layers above."
)

use_axial_zones = st.checkbox(
    "Use separate axial soil zones",
    value=bool(st.session_state.get("axial_zones")),
    key="use_axial_zones",
)

if use_axial_zones:
    if not st.session_state.get("axial_zones"):
        st.session_state["axial_zones"] = [
            {"top_ft": 0.0, "bottom_ft": 5.0, "f_s_comp_psf": 450.0,
             "f_s_uplift_psf": 450.0, "q_b_psf": 0.0, "description": "Zone 1"},
        ]

    axial_df = pd.DataFrame(st.session_state["axial_zones"])
    col_order = ["top_ft", "bottom_ft", "f_s_comp_psf", "f_s_uplift_psf", "q_b_psf", "description"]
    for c in col_order:
        if c not in axial_df.columns:
            axial_df[c] = 0.0 if c != "description" else ""
    axial_df = axial_df[col_order]

    edited_axial = st.data_editor(
        axial_df,
        column_config={
            "top_ft": st.column_config.NumberColumn("Top (ft)", format="%.1f", step=0.5),
            "bottom_ft": st.column_config.NumberColumn("Bottom (ft)", format="%.1f", step=0.5),
            "f_s_comp_psf": st.column_config.NumberColumn("f_s Comp (psf)", format="%.0f", step=25.0),
            "f_s_uplift_psf": st.column_config.NumberColumn("f_s Uplift (psf)", format="%.0f", step=25.0),
            "q_b_psf": st.column_config.NumberColumn("q_b End Bearing (psf)", format="%.0f", step=50.0,
                                                      help="End bearing at pile tip (only the zone containing the tip is used)"),
            "description": st.column_config.TextColumn("Description", width="medium"),
        },
        num_rows="dynamic",
        width="stretch",
        key="axial_zone_editor",
    )
    # Sync on button click to avoid double-entry
    if st.button("Save Axial Zones"):
        st.session_state["axial_zones"] = edited_axial.to_dict("records")
        st.success(f"Saved {len(edited_axial)} axial zone(s).")
else:
    st.session_state["axial_zones"] = []

# ============================================================================
# Frost Depth Check
# ============================================================================
st.markdown("---")
st.subheader("Frost Depth Check")
st.caption("IBC 1809.5: Embedment must extend at least 12 inches below frost line.")

# --- Double-buffered widget state (survives both double-click AND page nav) ---
# Streamlit clears widget-bound session_state on page unmount, but plain keys
# (prefixed with _ here) persist. Pattern: before each widget render, seed the
# widget key from the persistent shadow; after the widget renders, sync back.
_shadow_defaults = {
    "_frost_method": "Regional lookup",
    "_frost_region": list(FROST_DEPTH_TABLE.keys())[0],
    "_frost_F_I": 1000.0,
    "_frost_stefan_soil": list(STEFAN_C.keys())[0],
    "_frost_depth_manual": 42.0,
    "_tau_af_psi": 10.0,
    "_adfreeze_source_mode": "Geotech f_s_uplift (recommended)",
}
for _k, _v in _shadow_defaults.items():
    if _k not in st.session_state or st.session_state[_k] is None:
        st.session_state[_k] = _v

# Seed widget keys from shadows ONLY if the widget key is missing.
# (After page nav, Streamlit clears widget-bound keys; shadows survive.
# On a click-triggered rerun, widget key already holds the new click value
# and we must NOT overwrite it with stale shadow.)
# Seed widget keys for RADIOS/SELECTBOXES from shadows only if missing.
# (Number inputs don't use key= below; they read value= directly from shadows
# because pre-seeded session_state doesn't reliably control number_input's
# initial value on first render after page unmount.)
_radio_shadow_map = {
    "frost_method": "_frost_method",
    "frost_region": "_frost_region",
    "frost_stefan_soil": "_frost_stefan_soil",
    "adfreeze_source_mode": "_adfreeze_source_mode",
}
for _wk, _sk in _radio_shadow_map.items():
    if _wk not in st.session_state:
        st.session_state[_wk] = st.session_state[_sk]

frost_method = st.radio(
    "Frost depth method",
    ["Regional lookup", "Stefan equation", "Manual"],
    horizontal=True,
    key="frost_method",
)
st.session_state["_frost_method"] = frost_method

if frost_method == "Regional lookup":
    region = st.selectbox(
        "US Region", list(FROST_DEPTH_TABLE.keys()), key="frost_region",
    )
    st.session_state["_frost_region"] = region
    frost_in = frost_depth_regional(region)
elif frost_method == "Stefan equation":
    fc1, fc2 = st.columns(2)
    with fc1:
        F_I = st.number_input(
            "Freezing Index (degree-days F)",
            min_value=0.0,
            value=float(st.session_state.get("_frost_F_I", 1000.0) or 1000.0),
            step=100.0, format="%.0f",
        )
        if F_I is None:
            F_I = 1000.0
        st.session_state["_frost_F_I"] = F_I
    with fc2:
        stefan_soil = st.selectbox(
            "Soil type (Stefan C)", list(STEFAN_C.keys()),
            key="frost_stefan_soil",
        )
        st.session_state["_frost_stefan_soil"] = stefan_soil
    frost_in = frost_depth_stefan(F_I, stefan_soil)
    region = ""
else:
    frost_in = st.number_input(
        "Frost depth (in)", min_value=0.0,
        value=float(st.session_state.get("_frost_depth_manual", 42.0) or 42.0),
        step=6.0, format="%.0f",
    )
    if frost_in is None:
        frost_in = 42.0
    st.session_state["_frost_depth_manual"] = frost_in
    region = ""

# Store computed frost depth for use by optimizer and other pages
st.session_state["frost_depth_in"] = frost_in

st.markdown("**Adfreeze Uplift Source**")
_af_opts = ["Geotech f_s_uplift (recommended)", "Manual τ_af override"]
adfreeze_mode = st.radio(
    "Adfreeze source", _af_opts, horizontal=True,
    key="adfreeze_source_mode",
    help="Recommended: use the geotech-stated uplift skin friction values from the "
         "soil profile / axial zones. In frozen conditions the adfreeze bond IS the "
         "uplift skin friction, so using the same parameter keeps design consistent "
         "with the geotech report.",
)
st.session_state["_adfreeze_source_mode"] = adfreeze_mode

tau_af_psi = st.number_input(
    "Adfreeze bond strength, τ_af (psi) — used only in Manual mode",
    min_value=0.0,
    value=float(st.session_state.get("_tau_af_psi", 10.0) or 10.0),
    step=0.5, format="%.1f",
    help="Typical values: 5–15 psi for steel in frozen sand/gravel, "
         "10–25 psi for frozen silt, 15–40+ psi for ice-rich frozen clay. "
         "To convert from ksf: τ_af (psi) = f_s_uplift (ksf) × 1000 / 144.",
)
if tau_af_psi is None:
    tau_af_psi = 10.0
st.session_state["_tau_af_psi"] = tau_af_psi
st.session_state["_tau_af_psi"] = tau_af_psi

embedment = st.session_state.get("pile_embedment", 10.0)
section_obj = None
perimeter = 0.0
try:
    from core.sections import get_section
    section_obj = st.session_state.get("section") or get_section(st.session_state.pile_section)
    perimeter = section_obj.perimeter
except Exception:
    pass

# Compute adfreeze per selected mode
adfreeze_override_lbs = None
adfreeze_src_label = ""
if adfreeze_mode.startswith("Geotech") and st.session_state.get("soil_layers"):
    # Build profile + zones for integration
    _layers = [build_soil_layer_from_dict(ld) for ld in st.session_state.soil_layers]
    _prof = SoilProfile(layers=_layers, water_table_depth=st.session_state.get("water_table_depth"))
    _zones_dicts = st.session_state.get("axial_zones") or []
    _zones = []
    for zd in _zones_dicts:
        try:
            _zones.append(AxialSoilZone(
                top_depth_ft=float(zd.get("top_ft", 0.0)),
                bottom_depth_ft=float(zd.get("bottom_ft", 0.0)),
                f_s_comp_psf=float(zd.get("f_s_comp_psf", 0.0)),
                f_s_uplift_psf=float(zd.get("f_s_uplift_psf", 0.0)),
                q_b_psf=float(zd.get("q_b_psf", 0.0)),
                description=zd.get("description", ""),
            ))
        except (TypeError, ValueError):
            continue
    _force, _src, _notes = adfreeze_from_profile(
        profile=_prof,
        pile_perimeter_in=perimeter,
        frost_depth_ft=frost_in / 12.0,
        axial_zones=_zones if _zones else None,
    )
    adfreeze_override_lbs = _force
    adfreeze_src_label = _src

result_frost = frost_check(
    frost_depth_in=frost_in,
    embedment_ft=embedment,
    pile_perimeter_in=perimeter,
    tau_af_psi=tau_af_psi,
    method=frost_method,
    region=region if frost_method == "Regional lookup" else "",
    adfreeze_force_override_lbs=adfreeze_override_lbs,
    adfreeze_source_override=adfreeze_src_label,
)
st.session_state["frost_result"] = result_frost

fc1, fc2, fc3 = st.columns(3)
fc1.metric("Frost Depth", f"{frost_in:.0f} in ({frost_in / 12:.1f} ft)")
fc2.metric("Min Embedment (IBC)", f"{result_frost.min_embedment_ft:.1f} ft")
fc3.metric("Margin", f"{result_frost.margin_ft:.1f} ft")

if result_frost.passes:
    st.success(
        f"PASS — Embedment {embedment:.1f} ft >= required {result_frost.min_embedment_ft:.1f} ft"
    )
else:
    st.error(
        f"FAIL — Embedment {embedment:.1f} ft < required {result_frost.min_embedment_ft:.1f} ft"
    )

if result_frost.adfreeze_force_lbs:
    _af_src = result_frost.adfreeze_source or "tau_af manual"
    st.info(
        f"Adfreeze uplift force: **{result_frost.adfreeze_force_lbs:,.0f} lbs** "
        f"(source: {_af_src})"
    )

# ----------------------------------------------------------------------------
# Service-Level Adfreeze Check (skin below frost + D per pile vs adfreeze)
# ----------------------------------------------------------------------------
if result_frost.adfreeze_force_lbs and perimeter > 0 and st.session_state.get("soil_layers"):
    st.markdown("**Service-Level Adfreeze Check**")
    st.caption(
        "Industry-standard check: `skin_friction_below_frost + D_per_pile ≥ adfreeze`. "
        "Skin friction resistance is computed only below the frost depth; dead load per "
        "pile is taken from the Loading page at service level (no load factors)."
    )
    try:
        from core.axial import axial_capacity
        _ax = axial_capacity(
            profile=_prof if adfreeze_mode.startswith("Geotech") else
                    SoilProfile(
                        layers=[build_soil_layer_from_dict(ld) for ld in st.session_state.soil_layers],
                        water_table_depth=st.session_state.get("water_table_depth"),
                    ),
            pile_perimeter=perimeter,
            pile_tip_area=(section_obj.tip_area if section_obj else 0.0),
            embedment_depth=embedment,
            axial_zones=_zones if adfreeze_mode.startswith("Geotech") and _zones else None,
            frost_depth_ft=frost_in / 12.0,
        )
        _skin_below_frost_lbs = _ax.Q_s_below_frost
        _D_per_pile = float(st.session_state.get("dead_load", 0.0) or 0.0)
        svc = adfreeze_service_check(
            adfreeze_force_lbs=result_frost.adfreeze_force_lbs,
            skin_resistance_below_frost_lbs=_skin_below_frost_lbs,
            dead_load_per_pile_lbs=_D_per_pile,
            frost_depth_ft=frost_in / 12.0,
            embedment_ft=embedment,
        )
        st.session_state["adfreeze_service_result"] = svc

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Adfreeze Demand", f"{svc.adfreeze_force_lbs:,.0f} lbs")
        sc2.metric(f"Skin (below {svc.frost_depth_ft:.1f} ft)",
                   f"{svc.skin_resistance_below_frost_lbs:,.0f} lbs")
        sc3.metric("Dead / Pile", f"{svc.dead_load_per_pile_lbs:,.0f} lbs")
        sc4.metric("Margin", f"{svc.margin_lbs:+,.0f} lbs")

        if svc.passes:
            st.success(
                f"PASS — No net uplift. Total resistance "
                f"{svc.total_resistance_lbs:,.0f} lbs ≥ adfreeze "
                f"{svc.adfreeze_force_lbs:,.0f} lbs"
            )
        else:
            st.error(
                f"FAIL — Net uplift of {-svc.margin_lbs:,.0f} lbs. Increase embedment, "
                f"upsize pile, add frost sleeve, or increase reveal."
            )
    except Exception as _e:
        st.warning(f"Service-level adfreeze check unavailable: {_e}")
