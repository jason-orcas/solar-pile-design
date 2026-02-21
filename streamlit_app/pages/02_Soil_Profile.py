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
    correct_N_overburden, build_soil_layer_from_dict,
)
from core.frost import (
    FROST_DEPTH_TABLE, STEFAN_C,
    frost_depth_regional, frost_depth_stefan, frost_check,
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
        new_N = st.number_input("SPT N-value", min_value=0, value=15, step=1, key="new_N")
    with r3b:
        new_gamma = st.number_input("gamma (pcf)", min_value=0.0, value=0.0, step=5.0, format="%.0f", key="new_gamma", help="Unit weight. 0 = auto from soil type.")
    with r3c:
        new_phi = st.number_input("phi (deg)", min_value=0.0, value=0.0, step=1.0, format="%.0f", key="new_phi", help="Friction angle. 0 = auto from N-value.")
    with r3d:
        new_cu = st.number_input("c_u (psf)", min_value=0.0, value=0.0, step=100.0, format="%.0f", key="new_cu", help="Undrained shear strength. 0 = auto from N-value.")

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
            layer_data = {
                "top_depth": _top,
                "thickness": _bot - _top,
                "soil_type": new_type,
                "description": new_desc,
                "N_spt": _N,
                "gamma": _gamma if _gamma > 0 else None,
                "phi": _phi if _phi > 0 else None,
                "c_u": _cu if _cu > 0 else None,
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
# Frost Depth Check
# ============================================================================
st.markdown("---")
st.subheader("Frost Depth Check")
st.caption("IBC 1809.5: Embedment must extend at least 12 inches below frost line.")

frost_method = st.radio(
    "Frost depth method",
    ["Regional lookup", "Stefan equation", "Manual"],
    horizontal=True,
    key="frost_method",
)

if frost_method == "Regional lookup":
    region = st.selectbox("US Region", list(FROST_DEPTH_TABLE.keys()), key="frost_region")
    frost_in = frost_depth_regional(region)
elif frost_method == "Stefan equation":
    fc1, fc2 = st.columns(2)
    with fc1:
        F_I = st.number_input(
            "Freezing Index (degree-days F)",
            min_value=0.0, value=1000.0, step=100.0, format="%.0f",
        )
    with fc2:
        stefan_soil = st.selectbox("Soil type (Stefan C)", list(STEFAN_C.keys()))
    frost_in = frost_depth_stefan(F_I if F_I is not None else 0.0, stefan_soil)
    region = ""
else:
    frost_in = st.number_input(
        "Frost depth (in)", min_value=0.0,
        value=st.session_state.get("frost_depth_in", 42.0),
        step=6.0, format="%.0f",
    )
    if frost_in is None:
        frost_in = 42.0
    region = ""

st.session_state["frost_depth_in"] = frost_in

embedment = st.session_state.get("pile_embedment", 10.0)
section_obj = None
perimeter = 0.0
try:
    from core.sections import get_section
    section_obj = st.session_state.get("section") or get_section(st.session_state.pile_section)
    perimeter = section_obj.perimeter
except Exception:
    pass

result_frost = frost_check(
    frost_depth_in=frost_in,
    embedment_ft=embedment,
    pile_perimeter_in=perimeter,
    method=frost_method,
    region=region if frost_method == "Regional lookup" else "",
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
    st.info(f"Estimated adfreeze uplift force: {result_frost.adfreeze_force_lbs:,.0f} lbs")
