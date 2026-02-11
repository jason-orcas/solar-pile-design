"""Page 13: Installation QC — dynamic formulas and torque correlation."""

import sys
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.installation import (
    enr_formula, gates_formula, fhwa_modified_gates,
    helical_torque_check, HELICAL_KT,
)

st.header("Installation QC")
st.caption("Dynamic driving formulas for driven piles; torque correlation for helical piles.")

pile_type = st.session_state.get("pile_type", "driven")

if pile_type == "helical":
    # ======================================================================
    # Helical pile torque correlation
    # ======================================================================
    st.subheader("Helical Pile — Torque Correlation")
    st.markdown("**Q_ult = K_t x T**")

    col1, col2, col3 = st.columns(3)
    with col1:
        shaft_size = st.selectbox(
            "Shaft size",
            list(HELICAL_KT.keys()),
            format_func=lambda x: x.replace("_", " "),
        )
    with col2:
        torque = st.number_input(
            "Installation torque (ft-lbs)",
            min_value=0.0, value=1000.0, step=100.0, format="%.0f",
        )
    with col3:
        FS_hel = st.number_input(
            "Factor of safety", min_value=1.0, value=2.0, step=0.5, format="%.1f",
        )

    if st.button("Calculate Helical Capacity", type="primary"):
        result = helical_torque_check(torque, shaft_size, FS_hel)
        st.session_state["installation_qc_helical"] = result

    if "installation_qc_helical" in st.session_state:
        r = st.session_state["installation_qc_helical"]
        c1, c2, c3 = st.columns(3)
        c1.metric("K_t", f"{r.K_t:.0f} 1/ft")
        c2.metric("Q_ult", f"{r.Q_ult_lbs:,.0f} lbs ({r.Q_ult_lbs / 1000:.1f} kips)")
        c3.metric("Q_allow (FS={:.1f})".format(r.FS), f"{r.Q_allow_lbs:,.0f} lbs")

        # Compare to axial capacity if available
        axial = st.session_state.get("axial_result")
        if axial:
            st.markdown("---")
            st.markdown("**Comparison with Geotechnical Capacity**")
            c1, c2 = st.columns(2)
            c1.metric("Torque-based Q_ult", f"{r.Q_ult_lbs:,.0f} lbs")
            c2.metric("Geotechnical Q_ult", f"{axial.Q_ult_compression:,.0f} lbs")

else:
    # ======================================================================
    # Driven pile dynamic formulas
    # ======================================================================
    st.subheader("Driven Pile — Dynamic Formulas")

    col1, col2, col3 = st.columns(3)
    with col1:
        W_r = st.number_input(
            "Ram weight (lbs)", min_value=100.0, value=5000.0,
            step=500.0, format="%.0f",
        )
    with col2:
        h = st.number_input(
            "Drop height (ft)", min_value=0.5, value=3.0,
            step=0.5, format="%.1f",
        )
    with col3:
        s = st.number_input(
            "Set per blow (in)", min_value=0.01, value=0.25,
            step=0.05, format="%.3f",
            help="Penetration per hammer blow, typically measured over last 10 blows.",
        )

    st.metric("Hammer Energy", f"{W_r * h:,.0f} ft-lbs ({W_r * h / 1000:.1f} kip-ft)")

    if st.button("Run Dynamic Formulas", type="primary"):
        r_enr = enr_formula(W_r, h, s)
        r_gates = gates_formula(W_r, h, s)
        r_fhwa = fhwa_modified_gates(W_r, h, s)
        st.session_state["installation_qc_driven"] = [r_enr, r_gates, r_fhwa]

    if "installation_qc_driven" in st.session_state:
        results = st.session_state["installation_qc_driven"]

        rows = []
        for r in results:
            rows.append({
                "Method": r.method,
                "R_u (kips)": f"{r.R_u_kips:.1f}",
                "R_allow (kips)": f"{r.R_allow_lbs / 1000:.1f}",
                "FS": f"{r.FS:.1f}",
                "Notes": "; ".join(r.notes),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.caption(
            "ENR uses FS=6.0 (historically conservative). "
            "Gates and FHWA Modified Gates use FS=3.0. "
            "FHWA Modified Gates is generally considered the most reliable."
        )

        # Compare to axial capacity
        axial = st.session_state.get("axial_result")
        if axial:
            st.markdown("---")
            st.markdown("**Comparison with Geotechnical Capacity**")
            best = results[2]  # FHWA Modified Gates
            c1, c2 = st.columns(2)
            c1.metric(
                f"Dynamic R_allow ({best.method})",
                f"{best.R_allow_lbs:,.0f} lbs ({best.R_allow_lbs / 1000:.1f} kips)",
            )
            c2.metric(
                "Geotechnical Q_ult (compression)",
                f"{axial.Q_ult_compression:,.0f} lbs ({axial.Q_ult_compression / 1000:.1f} kips)",
            )
