"""t-z and q-z curve generation for axial pile-soil transfer.

t-z curves define skin friction mobilization vs. axial displacement.
q-z curves define tip resistance mobilization vs. tip displacement.
Formulations follow API RP 2GEO (Tables 7.2-1, 7.2-2, 7.3-1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .soil import SoilProfile, SoilLayer, SoilType
from .axial import alpha_adhesion_factor, beta_coefficient, _meyerhof_Nq, _meyerhof_qb_limit


@dataclass
class TZCurve:
    """Axial skin friction transfer curve at a given depth."""
    depth_ft: float
    depth_in: float
    z: np.ndarray       # Axial displacement array (in)
    t: np.ndarray       # Mobilized skin friction per unit pile length (lb/in)
    t_ult: float        # Ultimate skin friction per unit pile length (lb/in)
    method: str


@dataclass
class QZCurve:
    """Tip resistance transfer curve."""
    z: np.ndarray       # Tip displacement array (in)
    q: np.ndarray       # Mobilized tip resistance (lbs total)
    q_ult: float        # Ultimate tip resistance (lbs total)
    method: str


# ============================================================================
# t-z Curve Generation
# ============================================================================

# API RP 2GEO Table 7.2-1: Clay t-z curve shape
_TZ_CLAY_TABLE = np.array([
    [0.0000, 0.000],
    [0.0016, 0.300],
    [0.0031, 0.500],
    [0.0057, 0.750],
    [0.0080, 0.900],
    [0.0100, 1.000],
    [0.0200, 0.900],
    [1.0000, 0.900],
])

# API RP 2GEO Table 7.3-1 / 7.3-2: q-z curve shape (same for clay and sand)
_QZ_TABLE = np.array([
    [0.000, 0.000],
    [0.002, 0.250],
    [0.013, 0.500],
    [0.042, 0.750],
    [0.073, 0.900],
    [0.100, 1.000],
    [1.000, 1.000],
])


def tz_api_clay(
    depth_ft: float,
    c_u: float,
    sigma_v: float,
    pile_perimeter_in: float,
    pile_diameter_in: float,
    n_points: int = 50,
) -> TZCurve:
    """API RP 2GEO t-z curve for clay (with post-peak softening).

    Args:
        depth_ft: Depth below ground (ft)
        c_u: Undrained shear strength (psf)
        sigma_v: Effective overburden (psf)
        pile_perimeter_in: Pile perimeter (in)
        pile_diameter_in: Pile width/diameter (in) for z_peak
        n_points: Number of curve points
    """
    alpha = alpha_adhesion_factor(c_u, sigma_v)
    f_s_psf = alpha * c_u
    # Convert to force per unit pile length: (psf / 144) * perimeter_in = lb/in
    t_ult = f_s_psf / 144.0 * pile_perimeter_in

    z_peak = 0.01 * pile_diameter_in  # 1% of pile diameter

    # Build curve from API table
    z_norm = _TZ_CLAY_TABLE[:, 0]
    t_norm = _TZ_CLAY_TABLE[:, 1]

    z_arr = np.linspace(0, max(0.2, 20.0 * z_peak), n_points)
    # Interpolate normalized curve
    z_ratio = z_arr / z_peak if z_peak > 0 else z_arr * 100
    t_ratio = np.interp(z_ratio, z_norm, t_norm)
    t_arr = t_ult * t_ratio

    return TZCurve(
        depth_ft=depth_ft,
        depth_in=depth_ft * 12.0,
        z=z_arr,
        t=t_arr,
        t_ult=t_ult,
        method="API Clay",
    )


def tz_api_sand(
    depth_ft: float,
    phi: float,
    sigma_v: float,
    pile_perimeter_in: float,
    pile_diameter_in: float,
    pile_type: str = "driven",
    n_points: int = 50,
) -> TZCurve:
    """API RP 2GEO t-z curve for sand (no post-peak softening).

    Uses hyperbolic shape: t = t_ult * (z/z_peak) / (1 + z/z_peak) up to t_ult.

    Args:
        depth_ft: Depth below ground (ft)
        phi: Friction angle (degrees)
        sigma_v: Effective overburden (psf)
        pile_perimeter_in: Pile perimeter (in)
        pile_diameter_in: Pile width/diameter (in)
        pile_type: "driven", "drilled", or "helical"
        n_points: Number of curve points
    """
    K_s_r = 1.0 if pile_type == "driven" else 0.7
    delta_r = 0.7 if pile_type == "driven" else 0.8
    b = beta_coefficient(phi, K_s_ratio=K_s_r, delta_ratio=delta_r)
    f_s_psf = b * sigma_v
    t_ult = f_s_psf / 144.0 * pile_perimeter_in  # lb/in

    z_peak = 0.1  # in (typical for sand)

    z_arr = np.linspace(0, max(0.5, 20.0 * z_peak), n_points)
    t_arr = np.zeros(n_points)

    for i, z in enumerate(z_arr):
        if z <= 0 or z_peak <= 0:
            t_arr[i] = 0.0
        else:
            ratio = z / z_peak
            t_arr[i] = t_ult * ratio / (1.0 + ratio)

    return TZCurve(
        depth_ft=depth_ft,
        depth_in=depth_ft * 12.0,
        z=z_arr,
        t=t_arr,
        t_ult=t_ult,
        method="API Sand",
    )


def generate_tz_curve(
    depth_ft: float,
    layer: SoilLayer,
    sigma_v: float,
    pile_perimeter_in: float,
    pile_diameter_in: float,
    pile_type: str = "driven",
    n_points: int = 50,
) -> TZCurve:
    """Auto-select and generate t-z curve based on soil type."""
    is_cohesive = layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC)

    if is_cohesive:
        c_u = layer.get_cu()
        return tz_api_clay(depth_ft, c_u, sigma_v, pile_perimeter_in,
                           pile_diameter_in, n_points)
    else:
        phi = layer.get_phi(sigma_v)
        return tz_api_sand(depth_ft, phi, sigma_v, pile_perimeter_in,
                           pile_diameter_in, pile_type, n_points)


# ============================================================================
# q-z Curve Generation
# ============================================================================

def qz_api(
    q_ult_lbs: float,
    pile_diameter_in: float,
    soil_type: str = "sand",
    n_points: int = 50,
) -> QZCurve:
    """API RP 2GEO q-z curve for tip resistance.

    Args:
        q_ult_lbs: Ultimate tip resistance (lbs total)
        pile_diameter_in: Pile width/diameter (in)
        soil_type: "sand" or "clay"
        n_points: Number of curve points
    """
    z_peak = 0.10 * pile_diameter_in  # 10% of pile diameter

    z_norm = _QZ_TABLE[:, 0]
    q_norm = _QZ_TABLE[:, 1]

    z_arr = np.linspace(0, max(1.0, 10.0 * z_peak), n_points)
    z_ratio = z_arr / z_peak if z_peak > 0 else z_arr * 100
    q_ratio = np.interp(z_ratio, z_norm, q_norm)
    q_arr = q_ult_lbs * q_ratio

    method = "API Clay Tip" if soil_type == "clay" else "API Sand Tip"
    return QZCurve(z=z_arr, q=q_arr, q_ult=q_ult_lbs, method=method)


def generate_qz_curve(
    tip_layer: SoilLayer,
    sigma_v_tip: float,
    pile_tip_area_in2: float,
    pile_diameter_in: float,
    n_points: int = 50,
) -> QZCurve:
    """Generate q-z curve at pile tip using existing end bearing formulas.

    Args:
        tip_layer: Soil layer at pile tip
        sigma_v_tip: Effective overburden at tip (psf)
        pile_tip_area_in2: Pile tip area (in^2)
        pile_diameter_in: Pile width/diameter (in)
        n_points: Number of curve points
    """
    is_cohesive = tip_layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC)

    if is_cohesive:
        c_u = tip_layer.get_cu()
        N_c = 9.0
        q_b_psf = N_c * c_u
        soil_type = "clay"
    else:
        phi = tip_layer.get_phi(sigma_v_tip)
        N_q = _meyerhof_Nq(phi)
        q_b_psf = sigma_v_tip * N_q
        q_b_max = _meyerhof_qb_limit(phi) * 2000.0  # tsf -> psf
        q_b_psf = min(q_b_psf, q_b_max)
        soil_type = "sand"

    q_b_psi = q_b_psf / 144.0
    q_ult_lbs = q_b_psi * pile_tip_area_in2

    return qz_api(q_ult_lbs, pile_diameter_in, soil_type, n_points)
