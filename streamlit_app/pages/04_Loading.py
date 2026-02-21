"""Page 4: Load input and ASCE 7 load combinations."""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.loads import (
    LoadInput, generate_lrfd_combinations, generate_asd_combinations,
    wind_velocity_pressure, seismic_base_shear_coeff, snow_load,
)

st.header("Loading")

# --- Design method ---
st.session_state.design_method = st.radio(
    "Design Method", ["LRFD", "ASD", "Both"],
    index=["LRFD", "ASD", "Both"].index(st.session_state.get("design_method", "LRFD")),
    horizontal=True,
)

st.markdown("---")

# --- Direct load input ---
st.subheader("Per-Pile Loads")
st.caption("Enter unfactored (service) loads per pile. Load combinations are generated automatically.")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Gravity Loads**")
    st.session_state.dead_load = st.number_input(
        "Dead load (lbs)", min_value=0.0,
        value=st.session_state.get("dead_load", 400.0), step=50.0, format="%.0f",
    )
    st.session_state.live_load = st.number_input(
        "Live load (lbs)", min_value=0.0,
        value=st.session_state.get("live_load", 0.0), step=50.0, format="%.0f",
    )
    st.session_state.snow_load = st.number_input(
        "Snow load (lbs)", min_value=0.0,
        value=st.session_state.get("snow_load", 0.0), step=50.0, format="%.0f",
    )

with col2:
    st.markdown("**Wind Loads**")
    st.session_state.wind_down = st.number_input(
        "Wind downward (lbs)", min_value=0.0,
        value=st.session_state.get("wind_down", 0.0), step=100.0, format="%.0f",
    )
    st.session_state.wind_up = st.number_input(
        "Wind uplift (lbs)", min_value=0.0,
        value=st.session_state.get("wind_up", 1500.0), step=100.0, format="%.0f",
    )
    st.session_state.wind_lateral = st.number_input(
        "Wind lateral (lbs)", min_value=0.0,
        value=st.session_state.get("wind_lateral", 1500.0), step=100.0, format="%.0f",
    )
    st.session_state.wind_moment = st.number_input(
        "Wind moment at ground (ft-lbs)", min_value=0.0,
        value=st.session_state.get("wind_moment", 0.0), step=500.0, format="%.0f",
    )

with col3:
    st.markdown("**Seismic & Geometry**")
    st.session_state.seismic_lateral = st.number_input(
        "Seismic lateral (lbs)", min_value=0.0,
        value=st.session_state.get("seismic_lateral", 0.0), step=100.0, format="%.0f",
    )
    st.session_state.seismic_vertical = st.number_input(
        "Seismic vertical (lbs)", min_value=0.0,
        value=st.session_state.get("seismic_vertical", 0.0), step=100.0, format="%.0f",
    )
    st.session_state.seismic_moment = st.number_input(
        "Seismic moment (ft-lbs)", min_value=0.0,
        value=st.session_state.get("seismic_moment", 0.0), step=500.0, format="%.0f",
    )
    st.session_state.lever_arm = st.number_input(
        "Lateral load height above ground (ft)", min_value=0.0,
        value=st.session_state.get("lever_arm", 4.0), step=0.5, format="%.1f",
    )

# Guard against None from cleared number_input fields
for _k, _d in [("dead_load", 0.0), ("live_load", 0.0), ("snow_load", 0.0),
               ("wind_down", 0.0), ("wind_up", 0.0), ("wind_lateral", 0.0),
               ("wind_moment", 0.0), ("seismic_lateral", 0.0),
               ("seismic_vertical", 0.0), ("seismic_moment", 0.0),
               ("lever_arm", 4.0)]:
    if st.session_state.get(_k) is None:
        st.session_state[_k] = _d

st.markdown("---")

# --- Optional calculators ---
with st.expander("Wind Pressure Calculator (ASCE 7)"):
    wc1, wc2 = st.columns(2)
    with wc1:
        V_wind = st.number_input("Basic wind speed V (mph)", value=110.0, step=5.0, format="%.0f")
        K_z = st.number_input("K_z (exposure coeff)", value=0.85, step=0.05, format="%.2f")
        K_zt = st.number_input("K_zt (topo factor)", value=1.0, step=0.1, format="%.1f")
    with wc2:
        K_d = st.number_input("K_d (directionality)", value=0.85, step=0.05, format="%.2f")
        K_e = st.number_input("K_e (elevation factor)", value=1.0, step=0.05, format="%.2f")

    q_z = wind_velocity_pressure(
        V_wind if V_wind is not None else 0.0,
        K_z if K_z is not None else 0.85,
        K_zt if K_zt is not None else 1.0,
        K_d if K_d is not None else 0.85,
        K_e if K_e is not None else 1.0,
    )
    st.metric("Velocity Pressure q_z (psf)", f"{q_z:.1f}")

with st.expander("Seismic C_s Calculator"):
    sc1, sc2 = st.columns(2)
    with sc1:
        S_DS = st.number_input("S_DS (g)", value=0.5, step=0.05, format="%.2f")
    with sc2:
        R_seis = st.number_input("R (response mod.)", value=2.0, step=0.5, format="%.1f")
    C_s = seismic_base_shear_coeff(
        S_DS if S_DS is not None else 0.0,
        R_seis if R_seis is not None else 2.0,
    )
    st.metric("C_s", f"{C_s:.4f}")

with st.expander("Snow Load Calculator"):
    snc1, snc2 = st.columns(2)
    with snc1:
        p_g = st.number_input("Ground snow load p_g (psf)", value=20.0, step=5.0, format="%.0f")
        C_e = st.number_input("C_e (exposure)", value=0.8, step=0.1, format="%.1f")
    with snc2:
        C_t = st.number_input("C_t (thermal)", value=1.2, step=0.1, format="%.1f")
        I_s = st.number_input("I_s (importance)", value=1.0, step=0.1, format="%.1f")
    p_f = snow_load(
        p_g if p_g is not None else 0.0,
        C_e if C_e is not None else 0.8,
        C_t if C_t is not None else 1.2,
        I_s if I_s is not None else 1.0,
    )
    st.metric("Design snow load p_f (psf)", f"{p_f:.1f}")

st.markdown("---")

# --- Generate load combinations ---
st.subheader("Load Combinations")

load_input = LoadInput(
    dead=st.session_state.dead_load,
    live=st.session_state.live_load,
    snow=st.session_state.snow_load,
    wind_down=st.session_state.wind_down,
    wind_up=st.session_state.wind_up,
    wind_lateral=st.session_state.wind_lateral,
    wind_moment=st.session_state.wind_moment,
    seismic_vertical=st.session_state.seismic_vertical,
    seismic_lateral=st.session_state.seismic_lateral,
    seismic_moment=st.session_state.seismic_moment,
    lever_arm=st.session_state.lever_arm,
)

if st.session_state.design_method in ("LRFD", "Both"):
    st.markdown("### LRFD Combinations")
    lrfd = generate_lrfd_combinations(load_input)
    lrfd_data = []
    for lc in lrfd:
        lrfd_data.append({
            "Load Case": lc.name,
            "V_comp (lbs)": f"{lc.V_comp:.0f}",
            "V_tens (lbs)": f"{lc.V_tens:.0f}",
            "H_lat (lbs)": f"{lc.H_lat:.0f}",
            "M_ground (ft-lbs)": f"{lc.M_ground:.0f}",
        })
    st.dataframe(pd.DataFrame(lrfd_data), width="stretch", hide_index=True)

if st.session_state.design_method in ("ASD", "Both"):
    st.markdown("### ASD Combinations")
    asd = generate_asd_combinations(load_input)
    asd_data = []
    for lc in asd:
        asd_data.append({
            "Load Case": lc.name,
            "V_comp (lbs)": f"{lc.V_comp:.0f}",
            "V_tens (lbs)": f"{lc.V_tens:.0f}",
            "H_lat (lbs)": f"{lc.H_lat:.0f}",
            "M_ground (ft-lbs)": f"{lc.M_ground:.0f}",
        })
    st.dataframe(pd.DataFrame(asd_data), width="stretch", hide_index=True)
