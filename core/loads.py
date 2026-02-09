"""ASCE 7 load combinations and environmental load calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LoadCase:
    """A single load case with component forces on a pile."""
    name: str
    V_comp: float = 0.0    # Vertical compression (lbs, positive down)
    V_tens: float = 0.0    # Vertical tension (lbs, positive up)
    H_lat: float = 0.0     # Lateral load (lbs)
    M_ground: float = 0.0  # Moment at ground (ft-lbs)


@dataclass
class LoadInput:
    """Raw load inputs before combination."""
    dead: float = 0.0           # Dead load per pile (lbs, compression positive)
    live: float = 0.0           # Live load per pile (lbs)
    snow: float = 0.0           # Snow load per pile (lbs)
    wind_down: float = 0.0      # Wind downward component per pile (lbs)
    wind_up: float = 0.0        # Wind uplift per pile (lbs, positive = uplift)
    wind_lateral: float = 0.0   # Wind lateral force per pile (lbs)
    wind_moment: float = 0.0    # Wind moment at ground per pile (ft-lbs)
    seismic_vertical: float = 0.0
    seismic_lateral: float = 0.0
    seismic_moment: float = 0.0
    lever_arm: float = 4.0      # Height of lateral load above ground (ft)


def generate_lrfd_combinations(loads: LoadInput) -> list[LoadCase]:
    """Generate ASCE 7-22 LRFD load combinations.

    Returns list of governing load cases for solar pile design.
    """
    D = loads.dead
    L = loads.live
    S = loads.snow
    W_d = loads.wind_down
    W_u = loads.wind_up
    W_h = loads.wind_lateral
    W_m = loads.wind_moment
    E_v = loads.seismic_vertical
    E_h = loads.seismic_lateral
    E_m = loads.seismic_moment
    e = loads.lever_arm

    cases = []

    # LC1: 1.4D
    cases.append(LoadCase(
        name="LC1: 1.4D",
        V_comp=1.4 * D,
    ))

    # LC2: 1.2D + 1.6L + 0.5S
    cases.append(LoadCase(
        name="LC2: 1.2D + 1.6L + 0.5S",
        V_comp=1.2 * D + 1.6 * L + 0.5 * S,
    ))

    # LC3: 1.2D + 1.6S + 0.5W(down)
    cases.append(LoadCase(
        name="LC3: 1.2D + 1.6S + 0.5W↓",
        V_comp=1.2 * D + 1.6 * S + 0.5 * W_d,
    ))

    # LC4: 1.2D + 1.0W(down) + L + 0.5S — max compression with wind
    cases.append(LoadCase(
        name="LC4a: 1.2D + 1.0W↓ + L + 0.5S (compression)",
        V_comp=1.2 * D + 1.0 * W_d + L + 0.5 * S,
        H_lat=1.0 * W_h,
        M_ground=1.0 * W_m + 1.0 * W_h * e,
    ))

    # LC4b: 1.2D + 1.0W(up) + L + 0.5S — uplift case
    cases.append(LoadCase(
        name="LC4b: 1.2D + 1.0W↑ + L + 0.5S (uplift)",
        V_comp=1.2 * D + L + 0.5 * S,
        V_tens=1.0 * W_u - 1.2 * D,
        H_lat=1.0 * W_h,
        M_ground=1.0 * W_m + 1.0 * W_h * e,
    ))

    # LC5: 1.2D + 1.0E + L + 0.2S
    cases.append(LoadCase(
        name="LC5: 1.2D + 1.0E + L + 0.2S",
        V_comp=1.2 * D + E_v + L + 0.2 * S,
        H_lat=1.0 * E_h,
        M_ground=1.0 * E_m + 1.0 * E_h * e,
    ))

    # LC6: 0.9D + 1.0W — CRITICAL FOR SOLAR (uplift governs)
    net_uplift_6 = max(0, 1.0 * W_u - 0.9 * D)
    cases.append(LoadCase(
        name="LC6: 0.9D + 1.0W (UPLIFT - typically governs)",
        V_comp=max(0, 0.9 * D - 1.0 * W_u),
        V_tens=net_uplift_6,
        H_lat=1.0 * W_h,
        M_ground=1.0 * W_m + 1.0 * W_h * e,
    ))

    # LC7: 0.9D + 1.0E
    net_uplift_7 = max(0, E_v - 0.9 * D) if E_v > 0 else 0
    cases.append(LoadCase(
        name="LC7: 0.9D + 1.0E",
        V_comp=max(0, 0.9 * D - E_v),
        V_tens=net_uplift_7,
        H_lat=1.0 * E_h,
        M_ground=1.0 * E_m + 1.0 * E_h * e,
    ))

    return cases


def generate_asd_combinations(loads: LoadInput) -> list[LoadCase]:
    """Generate ASCE 7-22 ASD load combinations."""
    D = loads.dead
    L = loads.live
    S = loads.snow
    W_d = loads.wind_down
    W_u = loads.wind_up
    W_h = loads.wind_lateral
    W_m = loads.wind_moment
    E_v = loads.seismic_vertical
    E_h = loads.seismic_lateral
    E_m = loads.seismic_moment
    e = loads.lever_arm

    cases = []

    # LC1: D
    cases.append(LoadCase(name="ASD-1: D", V_comp=D))

    # LC2: D + L
    cases.append(LoadCase(name="ASD-2: D + L", V_comp=D + L))

    # LC3: D + S
    cases.append(LoadCase(name="ASD-3: D + S", V_comp=D + S))

    # LC5: D + 0.6W
    cases.append(LoadCase(
        name="ASD-5: D + 0.6W↓",
        V_comp=D + 0.6 * W_d,
        H_lat=0.6 * W_h,
        M_ground=0.6 * W_m + 0.6 * W_h * e,
    ))

    # LC6a: D + 0.75L + 0.75(0.6W) + 0.75S
    cases.append(LoadCase(
        name="ASD-6a: D + 0.75L + 0.45W↓ + 0.75S",
        V_comp=D + 0.75 * L + 0.75 * 0.6 * W_d + 0.75 * S,
        H_lat=0.75 * 0.6 * W_h,
        M_ground=0.75 * 0.6 * W_m + 0.75 * 0.6 * W_h * e,
    ))

    # LC7: 0.6D + 0.6W — CRITICAL FOR SOLAR
    net_uplift = max(0, 0.6 * W_u - 0.6 * D)
    cases.append(LoadCase(
        name="ASD-7: 0.6D + 0.6W (UPLIFT - typically governs)",
        V_comp=max(0, 0.6 * D - 0.6 * W_u),
        V_tens=net_uplift,
        H_lat=0.6 * W_h,
        M_ground=0.6 * W_m + 0.6 * W_h * e,
    ))

    # LC8: D + 0.7E
    cases.append(LoadCase(
        name="ASD-8: D + 0.7E",
        V_comp=D + 0.7 * E_v,
        H_lat=0.7 * E_h,
        M_ground=0.7 * E_m + 0.7 * E_h * e,
    ))

    # LC10: 0.6D + 0.7E
    cases.append(LoadCase(
        name="ASD-10: 0.6D + 0.7E",
        V_comp=max(0, 0.6 * D - 0.7 * E_v),
        V_tens=max(0, 0.7 * E_v - 0.6 * D),
        H_lat=0.7 * E_h,
        M_ground=0.7 * E_m + 0.7 * E_h * e,
    ))

    return cases


def wind_velocity_pressure(
    V: float,
    K_z: float = 0.85,
    K_zt: float = 1.0,
    K_d: float = 0.85,
    K_e: float = 1.0,
) -> float:
    """ASCE 7 velocity pressure q_z (psf).

    Args:
        V: Basic wind speed (mph), 3-sec gust
        K_z: Velocity pressure exposure coefficient
        K_zt: Topographic factor
        K_d: Wind directionality factor
        K_e: Ground elevation factor
    """
    return 0.00256 * K_z * K_zt * K_d * K_e * V**2


def seismic_base_shear_coeff(
    S_DS: float,
    R: float = 2.0,
    I_e: float = 1.0,
) -> float:
    """ASCE 7 seismic response coefficient C_s.

    Args:
        S_DS: Design spectral acceleration (short period, g)
        R: Response modification coefficient
        I_e: Importance factor
    """
    C_s = S_DS / (R / I_e)
    C_s_min = max(0.044 * S_DS * I_e, 0.01)
    return max(C_s, C_s_min)


def snow_load(
    p_g: float,
    C_e: float = 0.8,
    C_t: float = 1.2,
    I_s: float = 1.0,
) -> float:
    """ASCE 7 flat roof / ground-mount snow load (psf).

    Args:
        p_g: Ground snow load (psf)
        C_e: Exposure factor (0.8 open terrain)
        C_t: Thermal factor (1.2 unheated)
        I_s: Importance factor
    """
    return 0.7 * C_e * C_t * I_s * p_g


def K_z_exposure_C(z_ft: float) -> float:
    """Velocity pressure exposure coefficient for Exposure C.

    Args:
        z_ft: Height above ground (ft)
    """
    z = max(15.0, min(z_ft, 500.0))
    alpha = 9.5
    z_g = 900.0
    return 2.01 * (z / z_g) ** (2.0 / alpha)
