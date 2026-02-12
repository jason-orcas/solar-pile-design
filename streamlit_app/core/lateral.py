"""Lateral pile analysis: p-y curves and finite difference solver.

Implements Matlock (soft clay), Reese (sand), API RP 2A (sand & clay),
and Broms simplified method. FDM solver for full nonlinear lateral response.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
def _bisect(f, a, b, tol=1e-8, maxiter=200):
    """Simple bisection root finder replacing scipy.optimize.brentq."""
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError("f(a) and f(b) must have opposite signs")
    for _ in range(maxiter):
        mid = 0.5 * (a + b)
        fm = f(mid)
        if abs(fm) < tol or (b - a) < tol:
            return mid
        if fa * fm < 0:
            b = mid
        else:
            a, fa = mid, fm
    return 0.5 * (a + b)

from .soil import SoilProfile, SoilLayer, SoilType, PYModel, GAMMA_WATER


# ============================================================================
# p-y Curve Generation
# ============================================================================

@dataclass
class PYCurve:
    """A single p-y curve at a given depth."""
    depth_ft: float
    depth_in: float
    y: np.ndarray       # Deflection array (in)
    p: np.ndarray       # Soil resistance array (lb/in)
    p_ult: float        # Ultimate soil resistance (lb/in)
    method: str


def py_matlock_soft_clay(
    depth_ft: float,
    c_u: float,
    gamma_eff: float,
    B: float,
    J: float = 0.5,
    epsilon_50: float = 0.010,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Matlock (1970) p-y curve for soft clay.

    Args:
        depth_ft: Depth below ground (ft)
        c_u: Undrained shear strength (psf)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        J: Empirical constant (0.25 soft, 0.5 stiff)
        epsilon_50: Strain at 50% ultimate
        cyclic: Use cyclic degradation
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0

    # Ultimate resistance
    z_r = 6.0 * B_ft / (gamma_eff * B_ft / c_u + J) if c_u > 0 else 999
    if z < z_r:
        p_ult_per_ft = (3.0 + gamma_eff * z / c_u + J * z / B_ft) * c_u * B_ft
    else:
        p_ult_per_ft = 9.0 * c_u * B_ft
    p_ult = p_ult_per_ft / 12.0  # lb/in per inch of pile (lb/in)

    y_50 = 2.5 * epsilon_50 * B

    y_max = 16.0 * y_50
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    if not cyclic:
        for i, y in enumerate(y_arr):
            if y <= 0:
                p_arr[i] = 0
            elif y <= 8 * y_50:
                p_arr[i] = 0.5 * p_ult * (y / y_50) ** (1.0 / 3.0)
            else:
                p_arr[i] = p_ult
    else:
        ratio = z / z_r if z_r > 0 else 1.0
        for i, y in enumerate(y_arr):
            if y <= 0:
                p_arr[i] = 0
            elif y <= 3 * y_50:
                p_arr[i] = 0.5 * p_ult * (y / y_50) ** (1.0 / 3.0)
            else:
                if z < z_r:
                    p_arr[i] = 0.72 * p_ult * ratio
                else:
                    p_arr[i] = 0.72 * p_ult

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Matlock Soft Clay",
    )


def py_api_sand(
    depth_ft: float,
    phi: float,
    gamma_eff: float,
    B: float,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """API RP 2A p-y curve for sand.

    Args:
        depth_ft: Depth below ground (ft)
        phi: Friction angle (degrees)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        cyclic: Use cyclic A-factor
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0
    phi_r = math.radians(phi)

    # API coefficients
    C1, C2, C3 = _api_coefficients(phi)

    # Ultimate resistance (lb/ft)
    p_us = (C1 * z + C2 * B_ft) * gamma_eff * z
    p_ud = C3 * B_ft * gamma_eff * z
    p_ult_per_ft = min(p_us, p_ud) if z > 0 else 0.0
    p_ult = p_ult_per_ft / 12.0  # lb/in

    # A factor
    if cyclic:
        A = 0.9
    else:
        A = max(0.9, 3.0 - 0.8 * z / B_ft) if B_ft > 0 else 0.9

    # k (initial modulus of subgrade reaction)
    k = _api_sand_k(phi, submerged=(gamma_eff < 80))

    y_max = max(B * 0.1, 2.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    for i, y in enumerate(y_arr):
        if p_ult <= 0 or y <= 0:
            p_arr[i] = 0
        else:
            arg = k * z * 12.0 * y / (A * p_ult) if A * p_ult > 0 else 0
            p_arr[i] = A * p_ult * math.tanh(arg)

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="API Sand",
    )


def py_api_soft_clay(
    depth_ft: float,
    c_u: float,
    gamma_eff: float,
    B: float,
    J: float = 0.5,
    epsilon_50: float = 0.010,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """API RP 2A p-y curve for soft clay (same as Matlock)."""
    return py_matlock_soft_clay(
        depth_ft, c_u, gamma_eff, B, J, epsilon_50, cyclic, n_points,
    )


def py_reese_sand(
    depth_ft: float,
    phi: float,
    gamma_eff: float,
    B: float,
    k: float,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Reese et al. (1974) p-y curve for sand.

    4-point construction: linear + parabolic + 2 straight-line segments.

    Args:
        depth_ft: Depth below ground (ft)
        phi: Friction angle (degrees)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        k: Initial modulus of subgrade reaction (lb/in^3)
        cyclic: Use cyclic loading factors
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0
    phi_r = math.radians(phi)

    alpha = phi / 2.0
    beta = 45.0 + phi / 2.0
    alpha_r = math.radians(alpha)
    beta_r = math.radians(beta)

    K0 = 0.4
    Ka = math.tan(math.radians(45.0 - phi / 2.0)) ** 2

    # Ultimate resistance (lb/ft)
    if z <= 0 or gamma_eff <= 0:
        p_ult = 0.0
        p_ult_per_ft = 0.0
    else:
        # Shallow wedge (Eq. 3-53 simplified)
        sin_b = math.sin(beta_r)
        cos_a = math.cos(alpha_r)
        tan_b = math.tan(beta_r)
        tan_a = math.tan(alpha_r)
        tan_bma = math.tan(beta_r - phi_r) if abs(beta_r - phi_r) > 0.001 else 1e6
        sin_bphi = math.sin(beta_r) * math.sin(phi_r) if True else 0

        p_st = gamma_eff * z * (
            K0 * z * math.tan(phi_r) * sin_b / (tan_bma * cos_a)
            + tan_b / tan_bma * (B_ft + z * tan_b * tan_a)
            + K0 * z * tan_b * (math.tan(phi_r) * sin_b - tan_a)
            - Ka * B_ft
        )

        # Deep flow-around (Eq. 3-54)
        tan_b8 = tan_b ** 8
        p_sd = Ka * B_ft * gamma_eff * z * (tan_b8 - 1.0) + K0 * B_ft * gamma_eff * z * math.tan(phi_r) * tan_b ** 4

        p_s = min(p_st, p_sd)
        p_ult_per_ft = max(p_s, 0.0)
        p_ult = p_ult_per_ft / 12.0  # lb/in

    # Depth ratio for A_s, A_c, B_s, B_c (simplified from Figures 3.28-3.29)
    x_over_b = z / B_ft if B_ft > 0 else 0

    if cyclic:
        A_fac = max(0.88, 0.88) if x_over_b >= 5 else max(0.2 + 0.136 * x_over_b, 0.2)
        B_fac = max(0.55, 0.55) if x_over_b >= 5 else max(0.2 + 0.07 * x_over_b, 0.2)
    else:
        A_fac = max(0.88, 0.88) if x_over_b >= 5 else max(0.2 + 0.136 * x_over_b, 0.2)
        B_fac = max(0.50, 0.50) if x_over_b >= 5 else max(0.2 + 0.06 * x_over_b, 0.2)

    # Characteristic points
    y_u = 3.0 * B / 80.0
    y_m = B / 60.0
    p_u = A_fac * p_ult
    p_m = B_fac * p_ult

    # Build curve
    y_max = max(y_u * 2.0, B * 0.1, 1.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    if p_ult <= 0 or z <= 0:
        return PYCurve(depth_ft=depth_ft, depth_in=depth_ft * 12.0,
                       y=y_arr, p=p_arr, p_ult=0.0, method="Reese Sand")

    # Parabola parameters
    if y_u > y_m and p_u > p_m:
        m_slope = (p_u - p_m) / (y_u - y_m)
    else:
        m_slope = p_m / y_m if y_m > 0 else 1.0
    n_exp = p_m / (m_slope * y_m) if m_slope * y_m > 0 else 1.0
    n_exp = max(min(n_exp, 5.0), 0.1)
    C_bar = p_m / (y_m ** (1.0 / n_exp)) if y_m > 0 else 0

    # Intersection of initial line with parabola
    k_init = k * z * 12.0  # lb/in^2 per in of depth (z in ft, k in lb/in^3)
    if k_init > 0 and C_bar > 0 and n_exp != 1.0:
        y_k = (C_bar / k_init) ** (n_exp / (n_exp - 1.0)) if n_exp > 1.0 else 0
    else:
        y_k = 0

    for i, y in enumerate(y_arr):
        if y <= 0:
            p_arr[i] = 0
        elif y <= y_k:
            p_arr[i] = k_init * y
        elif y <= y_m:
            p_arr[i] = C_bar * y ** (1.0 / n_exp)
        elif y <= y_u:
            p_arr[i] = p_m + m_slope * (y - y_m)
        else:
            p_arr[i] = p_u

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Reese Sand",
    )


def py_stiff_clay_free_water(
    depth_ft: float,
    c_u: float,
    gamma_eff: float,
    B: float,
    epsilon_50: float = 0.005,
    k: float = 500.0,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Reese, Cox & Koop (1975) p-y curve for stiff clay with free water.

    5-segment curve: initial linear, parabolic, second parabolic, straight, residual.

    Args:
        depth_ft: Depth below ground (ft)
        c_u: Undrained shear strength (psf)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        epsilon_50: Strain at 50% ultimate stress
        k: Initial modulus of subgrade reaction (lb/in^3)
        cyclic: Use cyclic loading
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0
    c_a = c_u  # Average c_u from surface to depth (simplified)

    # Ultimate resistance (lb/ft)
    if z <= 0 or c_u <= 0:
        p_ult = 0.0
    else:
        p_ct = 2.0 * c_a * B_ft + gamma_eff * B_ft * z + 2.83 * c_a * z
        p_cd = 11.0 * c_u * B_ft
        p_c = min(p_ct, p_cd)
        p_ult = max(p_c, 0.0) / 12.0  # lb/in

    y_50 = epsilon_50 * B  # Note: no 2.5 multiplier for this model

    # Depth factor
    x_over_b = z / B_ft if B_ft > 0 else 0
    if cyclic:
        A_s = 0.2 + 0.1 * math.tanh(1.5 * x_over_b)
    else:
        A_s = 0.2 + 0.4 * math.tanh(0.62 * x_over_b)

    y_max = max(20.0 * A_s * y_50, B * 0.05, 1.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    if p_ult <= 0 or z <= 0:
        return PYCurve(depth_ft=depth_ft, depth_in=depth_ft * 12.0,
                       y=y_arr, p=p_arr, p_ult=0.0, method="Stiff Clay w/ Free Water")

    k_init = k * z * 12.0  # lb/in per in

    if not cyclic:
        for i, y in enumerate(y_arr):
            if y <= 0:
                p_arr[i] = 0
                continue
            p_linear = k_init * y
            p_para = 0.5 * p_ult * (y / y_50) ** 0.5 if y_50 > 0 else p_ult
            if y <= A_s * y_50:
                p_arr[i] = min(p_linear, p_para)
            elif y <= 6.0 * A_s * y_50:
                p_second = p_para - 0.055 * p_ult * ((y - A_s * y_50) / (A_s * y_50)) ** 1.25
                p_arr[i] = max(p_second, 0)
            elif y <= 18.0 * A_s * y_50:
                p_at_6 = 0.5 * p_ult * math.sqrt(6.0 * A_s) - 0.411 * p_ult
                p_arr[i] = max(p_at_6 - 0.0625 / y_50 * p_ult * (y - 6.0 * A_s * y_50), 0)
            else:
                p_arr[i] = max(p_ult * (1.225 * math.sqrt(A_s) - 0.75 * A_s - 0.411), 0)
    else:
        y_p = 4.1 * A_s * y_50
        for i, y in enumerate(y_arr):
            if y <= 0:
                p_arr[i] = 0
                continue
            p_linear = k_init * y
            if y <= 0.6 * y_p:
                p_para = A_s * p_ult * max(1.0 - (abs(y - 0.45 * y_p) / (0.45 * y_p)) ** 2.5, 0)
                p_arr[i] = min(p_linear, p_para)
            elif y <= 1.8 * y_p:
                p_arr[i] = max(0.936 * A_s * p_ult - 0.085 / y_50 * p_ult * (y - 0.6 * y_p), 0)
            else:
                p_arr[i] = max(0.936 * A_s * p_ult - 0.102 / y_50 * p_ult * y_p, 0)

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Stiff Clay w/ Free Water",
    )


def py_stiff_clay_no_free_water(
    depth_ft: float,
    c_u: float,
    gamma_eff: float,
    B: float,
    epsilon_50: float = 0.005,
    cyclic: bool = False,
    N_cycles: int = 1,
    n_points: int = 50,
) -> PYCurve:
    """Welch & Reese (1975) p-y curve for stiff clay without free water.

    Power curve: p = 0.5 * p_ult * (y / y_50)^0.25
    Cyclic: y-expansion via C * log(N).

    Args:
        depth_ft: Depth below ground (ft)
        c_u: Undrained shear strength (psf)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        epsilon_50: Strain at 50% ultimate stress
        cyclic: Use cyclic degradation
        N_cycles: Number of loading cycles (for cyclic)
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0
    J = 0.5

    # Ultimate resistance (same as Matlock)
    if z <= 0 or c_u <= 0:
        p_ult = 0.0
    else:
        z_r = 6.0 * B_ft / (gamma_eff * B_ft / c_u + J) if c_u > 0 else 999
        if z < z_r:
            p_ult_per_ft = (3.0 + gamma_eff * z / c_u + J * z / B_ft) * c_u * B_ft
        else:
            p_ult_per_ft = 9.0 * c_u * B_ft
        p_ult = p_ult_per_ft / 12.0

    y_50 = 2.5 * epsilon_50 * B

    y_max = 16.0 * y_50
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    if p_ult <= 0:
        return PYCurve(depth_ft=depth_ft, depth_in=depth_ft * 12.0,
                       y=y_arr, p=p_arr, p_ult=0.0, method="Stiff Clay w/o Free Water")

    if not cyclic or N_cycles <= 1:
        for i, y in enumerate(y_arr):
            if y <= 0:
                p_arr[i] = 0
            elif y <= 16.0 * y_50:
                p_arr[i] = 0.5 * p_ult * (y / y_50) ** 0.25
            else:
                p_arr[i] = p_ult
    else:
        # Cyclic: expand y by C*log(N)
        log_N = math.log10(max(N_cycles, 1))
        for i, y in enumerate(y_arr):
            if y <= 0:
                p_arr[i] = 0
                continue
            # Invert: find p for this y under cyclic
            # y_c = y_s + y_50 * 9.6 * (p/p_ult)^4 * log(N)
            # Solve iteratively for p given y_c = y
            p_trial = 0.5 * p_ult * (y / y_50) ** 0.25
            for _ in range(20):
                ratio = min(p_trial / p_ult, 1.0) if p_ult > 0 else 0
                C = 9.6 * ratio ** 4
                y_s = y_50 * (2.0 * ratio) ** 4 if ratio > 0 else 0
                y_c = y_s + y_50 * C * log_N
                if y_c <= 0:
                    break
                # Adjust: if y_c > y, reduce p; if y_c < y, increase p
                scale = (y / y_c) ** 0.25 if y_c > 0 else 1.0
                p_trial = min(p_trial * scale, p_ult)
            p_arr[i] = min(p_trial, p_ult)

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Stiff Clay w/o Free Water",
    )


def py_elastic_subgrade(
    depth_ft: float,
    gamma_eff: float,
    B: float,
    k: float,
    n_points: int = 50,
) -> PYCurve:
    """Linear elastic subgrade p-y curve: p = k * z * y (no ultimate cap).

    Args:
        depth_ft: Depth below ground (ft)
        gamma_eff: Effective unit weight (pcf, not used directly)
        B: Pile width (in)
        k: Subgrade reaction modulus (lb/in^3)
        n_points: Number of curve points
    """
    z_in = depth_ft * 12.0
    k_init = k * z_in  # lb/in per in

    y_max = max(B * 0.1, 2.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = k_init * y_arr

    p_ult = k_init * y_max  # No cap — linear to end

    return PYCurve(
        depth_ft=depth_ft, depth_in=z_in,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Elastic Subgrade",
    )


def py_liquefied_sand_rollins(
    depth_ft: float,
    B: float,
    n_points: int = 50,
) -> PYCurve:
    """Rollins et al. (2005) p-y curve for liquefied sand.

    Concave-upward empirical curve: p = P_d * A * (B_coeff * y)^C.
    Cap at 15 kN/m for 0.3m reference diameter.

    Args:
        depth_ft: Depth below ground (ft)
        B: Pile width (in)
        n_points: Number of curve points
    """
    z_m = depth_ft * 0.3048  # ft to m
    B_m = B * 0.0254  # in to m

    # Depth-dependent coefficients (z in meters)
    A_coeff = 3e-7 * (z_m + 1.0) ** 6.05
    B_coeff = 2.80 * (z_m + 1.0) ** 0.11
    C_coeff = 2.85 * (z_m + 1.0) ** (-0.41)

    # Diameter correction factor
    if B_m < 0.3:
        P_d = 1.0129 * (B_m / 0.3)
    elif B_m <= 2.6:
        P_d = 3.81 * math.log(B_m) + 5.6
    else:
        P_d = 9.24

    # Reference cap: 15 kN/m for 0.3m pile
    p_cap_ref = 15.0  # kN/m

    y_max_mm = 150.0  # mm
    y_arr_mm = np.linspace(0, y_max_mm, n_points)

    p_arr_kn_m = np.zeros(n_points)
    for i, y_mm in enumerate(y_arr_mm):
        if y_mm <= 0:
            p_arr_kn_m[i] = 0
        else:
            p_ref = min(A_coeff * (B_coeff * y_mm) ** C_coeff, p_cap_ref)
            p_arr_kn_m[i] = P_d * p_ref

    # Convert to US units: kN/m → lb/in
    # 1 kN/m = 5.7102 lb/in
    conv = 5.7102
    y_arr = y_arr_mm / 25.4  # mm to in
    p_arr = p_arr_kn_m * conv

    p_ult = p_arr[-1]

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Liquefied Sand (Rollins)",
    )


def py_mod_stiff_clay(
    depth_ft: float,
    c_u: float,
    gamma_eff: float,
    B: float,
    epsilon_50: float = 0.005,
    k: float = 500.0,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Modified Stiff Clay (Brown 2002) p-y curve.

    Same 0.25-power curve as Welch & Reese (stiff clay w/o free water),
    but with a user-defined initial stiffness k that provides a linear
    segment at small deflections before transitioning to the power curve.

    Args:
        depth_ft: Depth below ground (ft)
        c_u: Undrained shear strength (psf)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        epsilon_50: Strain at 50% ultimate stress
        k: Initial modulus of subgrade reaction (lb/in^3)
        cyclic: Use cyclic degradation
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0
    J = 0.5

    # Ultimate resistance (same as Matlock / Welch-Reese)
    if z <= 0 or c_u <= 0:
        p_ult = 0.0
    else:
        z_r = 6.0 * B_ft / (gamma_eff * B_ft / c_u + J) if c_u > 0 else 999
        if z < z_r:
            p_ult_per_ft = (3.0 + gamma_eff * z / c_u + J * z / B_ft) * c_u * B_ft
        else:
            p_ult_per_ft = 9.0 * c_u * B_ft
        p_ult = p_ult_per_ft / 12.0

    y_50 = 2.5 * epsilon_50 * B

    y_max = 16.0 * y_50
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    if p_ult <= 0:
        return PYCurve(depth_ft=depth_ft, depth_in=depth_ft * 12.0,
                       y=y_arr, p=p_arr, p_ult=0.0, method="Modified Stiff Clay")

    # Initial linear stiffness
    k_init = k * z * 12.0  # lb/in per in

    for i, y in enumerate(y_arr):
        if y <= 0:
            p_arr[i] = 0
        else:
            p_linear = k_init * y
            p_power = 0.5 * p_ult * (y / y_50) ** 0.25 if y_50 > 0 else p_ult
            # Use min of linear and power curve (linear governs at small y)
            if y <= 16.0 * y_50:
                p_arr[i] = min(p_linear, p_power) if k_init > 0 else p_power
            else:
                p_arr[i] = min(p_linear, p_ult) if k_init > 0 else p_ult

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Modified Stiff Clay",
    )


def py_small_strain_sand(
    depth_ft: float,
    phi: float,
    gamma_eff: float,
    B: float,
    G_max: float = 0.0,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Small-Strain Sand (Hanssen 2015) p-y curve.

    Hardin-Drnevich degradation overlay on API sand. At small deflections
    the curve follows G_max-based stiffness; at large deflections it
    converges to the standard API sand curve.

    Args:
        depth_ft: Depth below ground (ft)
        phi: Friction angle (degrees)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        G_max: Maximum shear modulus (psi). If 0, estimated from phi/sigma_v.
        cyclic: Use cyclic loading
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0

    # Get API sand p_ult and k
    C1, C2, C3 = _api_coefficients(phi)
    p_us = (C1 * z + C2 * B_ft) * gamma_eff * z
    p_ud = C3 * B_ft * gamma_eff * z
    p_ult_per_ft = min(p_us, p_ud) if z > 0 else 0.0
    p_ult = p_ult_per_ft / 12.0

    if cyclic:
        A = 0.9
    else:
        A = max(0.9, 3.0 - 0.8 * z / B_ft) if B_ft > 0 else 0.9

    # Estimate G_max if not provided
    if G_max <= 0:
        sigma_v_psi = gamma_eff * z / 144.0  # psf to psi
        # Hardin & Drnevich: G_max ~ 1000 * K2 * (sigma_m')^0.5 (psi)
        K2 = 30 + 2.0 * (phi - 25)  # Approx K2 from phi
        G_max = max(1000.0 * K2 * max(sigma_v_psi, 1.0) ** 0.5, 500.0)

    # Reference deflection: yr = A * p_ult / (4 * G_max)
    yr = A * p_ult / (4.0 * G_max) if G_max > 0 else 0.01

    k_api = _api_sand_k(phi, submerged=(gamma_eff < 80))

    y_max = max(B * 0.1, 2.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    for i, y in enumerate(y_arr):
        if p_ult <= 0 or y <= 0:
            p_arr[i] = 0
            continue

        # API sand curve
        arg = k_api * z * 12.0 * y / (A * p_ult) if A * p_ult > 0 else 0
        p_api = A * p_ult * math.tanh(arg)

        # Small-strain overlay: Hardin-Drnevich degradation
        # G/G_max = 1 / (1 + |y/yr|)
        ratio = abs(y / yr) if yr > 0 else 1e6
        G_ratio = 1.0 / (1.0 + ratio)
        p_small = 4.0 * G_max * G_ratio * y  # Small-strain resistance

        # Use maximum of small-strain and API curves
        # At small y, small-strain is stiffer; at large y, API governs
        p_arr[i] = max(p_small, p_api)
        # Cap at p_ult
        p_arr[i] = min(p_arr[i], A * p_ult)

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Small-Strain Sand",
    )


def py_liquefied_sand_hybrid(
    depth_ft: float,
    c_u_residual: float,
    gamma_eff: float,
    B: float,
    n_points: int = 50,
) -> PYCurve:
    """Liquefied Sand Hybrid (Franke & Rollins 2013) p-y curve.

    Combines Rollins (2005) dilative curve with Matlock soft clay using
    the liquefied residual shear strength. At each deflection y, the
    hybrid resistance is the minimum of the two component curves.

    Args:
        depth_ft: Depth below ground (ft)
        c_u_residual: Residual undrained shear strength of liquefied soil (psf)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        n_points: Number of curve points
    """
    # Get Rollins dilative curve
    rollins = py_liquefied_sand_rollins(depth_ft, B, n_points)

    # Get Matlock residual curve using liquefied residual strength
    if c_u_residual <= 0:
        c_u_residual = 50.0  # Minimum default for very loose sand

    matlock = py_matlock_soft_clay(
        depth_ft, c_u_residual, gamma_eff, B,
        J=0.5, epsilon_50=0.02, cyclic=True, n_points=n_points,
    )

    # Hybrid = minimum of the two at each deflection
    # Interpolate both curves onto a common y array
    y_max = max(rollins.y[-1], matlock.y[-1])
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    for i, y in enumerate(y_arr):
        p_roll = float(np.interp(y, rollins.y, rollins.p))
        p_mat = float(np.interp(y, matlock.y, matlock.p))
        p_arr[i] = min(p_roll, p_mat)

    p_ult = p_arr.max()

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Liquefied Sand (Hybrid)",
    )


def py_weak_rock(
    depth_ft: float,
    q_ur: float,
    B: float,
    E_ir: float = 0.0,
    RQD: float = 0.0,
    k_rm: float = 0.0005,
    n_points: int = 50,
) -> PYCurve:
    """Reese (1997) p-y curve for weak rock.

    3-branch model: linear, 0.25-power curve, and ultimate plateau.
    Weak rock: q_ur < ~1000 psi (6.9 MPa).

    Args:
        depth_ft: Depth below ground (ft)
        q_ur: Uniaxial compressive strength of rock (psf)
        B: Pile width (in)
        E_ir: Initial modulus of rock mass (psi). If 0, estimated from q_ur.
        RQD: Rock Quality Designation (0-100%)
        k_rm: Strain factor analogous to epsilon_50 (typically 0.0005 to 0.00005)
        n_points: Number of curve points
    """
    x_r = depth_ft * 12.0  # depth in inches (below rock surface)
    b = B  # pile diameter in inches

    # Strength reduction factor (Eq 3-131)
    alpha_r = max(1.0 - (2.0 / 3.0) * (RQD / 100.0), 1.0 / 3.0)

    # Ultimate resistance (Eq 3-129, 3-130) — in lb/in
    if x_r <= 3.0 * b:
        p_ur = alpha_r * q_ur * b * (1.0 + 1.4 * x_r / b) / 144.0  # q_ur psf → psi
    else:
        p_ur = 5.2 * alpha_r * q_ur * b / 144.0

    # Note: q_ur in psf; convert to psi for consistency: q_ur_psi = q_ur / 144
    q_ur_psi = q_ur / 144.0

    # Recompute p_ur using psi units directly
    if x_r <= 3.0 * b:
        p_ur = alpha_r * q_ur_psi * b * (1.0 + 1.4 * x_r / b)
    else:
        p_ur = 5.2 * alpha_r * q_ur_psi * b

    # Estimate E_ir if not provided
    if E_ir <= 0:
        # Approximate: E_ir ~ 150 * q_ur_psi for weak rock
        E_ir = max(150.0 * q_ur_psi, 1000.0)

    # Dimensionless constant k_ir (Eq 3-133, 3-134)
    if x_r <= 3.0 * b:
        k_ir = 100.0 + 400.0 * x_r / (3.0 * b) if b > 0 else 100.0
    else:
        k_ir = 500.0

    # Initial modulus M_ir = k_ir * E_ir (Eq 3-132) — lb/in per in
    M_ir = k_ir * E_ir

    # Strain parameter y_rm (Eq 3-136)
    if k_rm <= 0:
        k_rm = 0.0005
    y_rm = k_rm * b

    # Intersection point y_A (Eq 3-139)
    if M_ir > 0 and y_rm > 0:
        denom = 2.0 * (y_rm ** 0.25) * M_ir
        y_A = (p_ur / denom) ** 1.333 if denom > 0 else 0.001
    else:
        y_A = 0.001

    y_max = max(16.0 * y_rm, y_A * 3.0, 1.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    if p_ur <= 0:
        return PYCurve(depth_ft=depth_ft, depth_in=x_r,
                       y=y_arr, p=p_arr, p_ult=0.0, method="Weak Rock (Reese)")

    for i, y in enumerate(y_arr):
        if y <= 0:
            p_arr[i] = 0
        elif y <= y_A:
            # Branch 1: linear (Eq 3-135)
            p_arr[i] = M_ir * y
        elif y <= 16.0 * y_rm:
            # Branch 2: power curve (Eq 3-137)
            p_arr[i] = min(0.5 * p_ur * (y / y_rm) ** 0.25, p_ur)
        else:
            # Branch 3: ultimate (Eq 3-138)
            p_arr[i] = p_ur

    return PYCurve(
        depth_ft=depth_ft, depth_in=x_r,
        y=y_arr, p=p_arr, p_ult=p_ur, method="Weak Rock (Reese)",
    )


def py_strong_rock(
    depth_ft: float,
    q_ur: float,
    B: float,
    E_ir: float = 0.0,
    n_points: int = 50,
) -> PYCurve:
    """Vuggy Limestone bilinear p-y curve for strong rock.

    Strong rock: q_ur >= 1000 psi (6.9 MPa). Two-slope bilinear curve.
    LPile Section 3.8.3.

    Args:
        depth_ft: Depth below ground (ft)
        q_ur: Uniaxial compressive strength (psf)
        B: Pile width (in)
        E_ir: Initial modulus of rock mass (psi). If 0, estimated.
        n_points: Number of curve points
    """
    b = B  # pile diameter (in)
    q_ur_psi = q_ur / 144.0
    s_u = q_ur_psi / 2.0  # Shear strength = half UCS

    # Ultimate resistance: p_u = b * s_u (lb/in)
    p_ult = b * s_u

    # Bilinear breakpoints (Figure 3.63)
    y_1 = 0.0004 * b  # Transition from steep to shallow slope
    y_2 = 0.0024 * b  # Brittle fracture threshold

    # Initial slope: E_s1 = 2000 * s_u
    E_s1 = 2000.0 * s_u
    # Second slope: E_s2 = 100 * s_u
    E_s2 = 100.0 * s_u

    p_at_y1 = E_s1 * y_1

    y_max = max(y_2 * 1.5, 1.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    for i, y in enumerate(y_arr):
        if y <= 0:
            p_arr[i] = 0
        elif y <= y_1:
            p_arr[i] = E_s1 * y
        else:
            p_arr[i] = min(p_at_y1 + E_s2 * (y - y_1), p_ult)

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Strong Rock (Vuggy)",
    )


def py_massive_rock(
    depth_ft: float,
    sigma_ci: float,
    gamma_eff: float,
    B: float,
    m_i: float = 10.0,
    GSI: float = 50.0,
    E_rock: float = 0.0,
    poissons_ratio: float = 0.25,
    n_points: int = 50,
) -> PYCurve:
    """Massive Rock (Liang et al. 2009) p-y curve using Hoek-Brown criterion.

    Hyperbolic p-y relationship: p = y / (1/K_i + y/p_u).
    Uses Hoek-Brown to derive rock mass strength parameters.

    Args:
        depth_ft: Depth below ground (ft)
        sigma_ci: Intact rock UCS (psi)
        gamma_eff: Effective unit weight of rock (pcf)
        B: Pile width (in)
        m_i: Hoek-Brown material index
        GSI: Geological Strength Index (0-100)
        E_rock: Rock mass modulus (psi). If 0, estimated from GSI.
        poissons_ratio: Poisson's ratio of rock mass
        n_points: Number of curve points
    """
    b = B  # pile diameter (in)
    z = depth_ft

    # Hoek-Brown parameter m_b (Eq 3-144, D_r = 0 for bored piles)
    D_r = 0.0
    m_b = m_i * math.exp((GSI - 100.0) / (28.0 - 14.0 * D_r))

    # s parameter for Hoek-Brown (s=1 for intact, s<1 for rock mass)
    s = math.exp((GSI - 100.0) / (9.0 - 3.0 * D_r))
    a_hb = 0.5  # Standard for most rock types

    # Confining stress at depth (sigma_3) — psi
    sigma_3 = gamma_eff * z / 144.0  # psf to psi
    sigma_3 = max(sigma_3, 0.1)

    # Major principal stress at failure (Eq 3-143)
    sigma_1 = sigma_3 + sigma_ci * (m_b * sigma_3 / sigma_ci + s) ** a_hb

    # Derive Mohr-Coulomb c' and phi' from Hoek-Brown
    d_sigma = sigma_1 - sigma_3
    if d_sigma > 0:
        tau = d_sigma * math.sqrt(1.0 + m_b * sigma_ci / (2.0 * d_sigma))
        sin_arg = min(2.0 * tau / d_sigma, 1.0) if d_sigma > 0 else 0
        phi_rad = math.pi / 2.0 - math.asin(min(sin_arg, 1.0))
        phi_deg = math.degrees(phi_rad)

        sigma_n = sigma_3 + d_sigma ** 2 / (2.0 * d_sigma + 0.5 * m_b * sigma_ci)
        c_prime = tau - sigma_n * math.tan(phi_rad)
        c_prime = max(c_prime, 0.0)
    else:
        phi_deg = 30.0
        c_prime = sigma_ci * 0.1

    # Rock mass modulus (Eq 3-149)
    if E_rock <= 0:
        # E_m = E_i * e^(GSI/21.7) / 100 (Eq 3-149)
        # Estimate E_i from sigma_ci: E_i ~ 300 * sigma_ci for average rock
        E_i = 300.0 * sigma_ci
        E_rock = E_i * math.exp(GSI / 21.7) / 100.0

    # Initial stiffness K_i (lb/in per in)
    K_i = E_rock * b / (1.0 - poissons_ratio ** 2) if poissons_ratio < 1 else E_rock * b

    # Ultimate resistance p_u
    # Near surface passive wedge (simplified)
    Kp = math.tan(math.radians(45 + phi_deg / 2)) ** 2
    Ka = math.tan(math.radians(45 - phi_deg / 2)) ** 2
    K0 = 1.0 - math.sin(math.radians(phi_deg))
    sigma_v = gamma_eff * z / 144.0  # psi

    # Shallow: passive wedge
    p_us = (Kp - Ka) * sigma_v * b + 2.0 * c_prime * math.sqrt(Kp) * b
    # Deep: flow-around
    p_ud = (Kp ** 2 - Ka) * sigma_v * b + 2.0 * c_prime * Kp * b
    p_u = min(p_us, p_ud) if z > 0 else c_prime * b

    # Ensure minimum p_u
    p_u = max(p_u, sigma_ci * b * 0.01)

    # Hyperbolic curve (Eq 3-142): p = y / (1/K_i + y/p_u)
    y_max = max(b * 0.02, 1.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    for i, y in enumerate(y_arr):
        if y <= 0 or K_i <= 0:
            p_arr[i] = 0
        else:
            p_arr[i] = y / (1.0 / K_i + y / p_u) if p_u > 0 else K_i * y

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_u, method="Massive Rock (Hoek-Brown)",
    )


def py_piedmont_residual(
    depth_ft: float,
    c_u: float,
    gamma_eff: float,
    B: float,
    epsilon_50: float = 0.007,
    k: float = 0.0,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Piedmont Residual Soil (Simpson & Brown 2006) p-y curve.

    Modified stiff clay approach for residual soils of the Piedmont
    geologic province. Uses the Welch & Reese power curve with a
    reduced ultimate resistance to account for the partially drained
    behavior of residual soils.

    Args:
        depth_ft: Depth below ground (ft)
        c_u: Undrained shear strength (psf)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        epsilon_50: Strain at 50% ultimate (default 0.007 for residual soils)
        k: Initial subgrade modulus (lb/in^3). If 0, uses power curve only.
        cyclic: Use cyclic degradation
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0
    J = 0.5

    if z <= 0 or c_u <= 0:
        p_ult = 0.0
    else:
        z_r = 6.0 * B_ft / (gamma_eff * B_ft / c_u + J) if c_u > 0 else 999
        if z < z_r:
            p_ult_per_ft = (3.0 + gamma_eff * z / c_u + J * z / B_ft) * c_u * B_ft
        else:
            p_ult_per_ft = 9.0 * c_u * B_ft
        # Reduction factor for residual soil (0.85 accounts for partial drainage)
        p_ult = 0.85 * p_ult_per_ft / 12.0

    y_50 = 2.5 * epsilon_50 * B
    k_init = k * z * 12.0 if k > 0 else 0.0

    y_max = 16.0 * y_50
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    if p_ult <= 0:
        return PYCurve(depth_ft=depth_ft, depth_in=depth_ft * 12.0,
                       y=y_arr, p=p_arr, p_ult=0.0, method="Piedmont Residual")

    for i, y in enumerate(y_arr):
        if y <= 0:
            p_arr[i] = 0
        else:
            p_power = 0.5 * p_ult * (y / y_50) ** 0.25 if y_50 > 0 else p_ult
            if k_init > 0:
                p_arr[i] = min(k_init * y, p_power)
            else:
                p_arr[i] = p_power
            p_arr[i] = min(p_arr[i], p_ult)

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Piedmont Residual",
    )


def py_loess(
    depth_ft: float,
    gamma_eff: float,
    B: float,
    q_c: float = 0.0,
    c_u: float = 0.0,
    N_cycles: int = 1,
    n_points: int = 50,
) -> PYCurve:
    """Loess soil (Johnson et al. 2006) p-y curve.

    Hyperbolic degradation model calibrated from load tests in Kansas
    loess. Uses CPT cone tip resistance (q_c) or c_u to derive ultimate.
    LPile Section 3.6.

    Args:
        depth_ft: Depth below ground (ft)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        q_c: CPT cone tip resistance (psf). If 0, estimated from c_u.
        c_u: Undrained shear strength (psf). Used if q_c = 0.
        N_cycles: Number of load cycles (1-10)
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0
    b = B  # diameter (in)

    # Get q_c
    if q_c <= 0 and c_u > 0:
        # Approximate: q_c ~ 10 * c_u (typical for silts/loess)
        q_c = 10.0 * c_u
    elif q_c <= 0:
        q_c = 10000.0  # Default 10 ksf

    # Depth reduction: reduce q_c by 50% at surface, full at 2*B depth
    # (LPile Section 3.6, passive wedge reduction)
    depth_in = z * 12.0
    if depth_in < 2.0 * b:
        reduction = 0.5 + 0.5 * (depth_in / (2.0 * b))
    else:
        reduction = 1.0
    q_c_adj = q_c * reduction

    # Ultimate unit lateral resistance: p_u0 = N_CPT * q_c (Eq 3-93)
    N_CPT = 0.409
    p_u0 = N_CPT * q_c_adj  # psf per ft width

    # Ultimate p per unit pile length: p_u = p_u0 * b / (1 + C_N * log|N|)
    # (Eq 3-95)
    C_N = 0.24
    N_eff = max(N_cycles, 1)
    log_N = math.log10(N_eff) if N_eff > 1 else 0.0
    p_u = p_u0 * (b / 12.0) / (1.0 + C_N * log_N)  # lb/ft → need lb/in
    p_u = p_u / 12.0  # lb/in

    # Reference displacement (Eq 3-97)
    y_ref = 0.117  # inches

    # Initial modulus E_i = p_u / y_ref (Eq 3-98)
    E_i = p_u / y_ref if y_ref > 0 else p_u * 10.0

    # p-y curve: p = E_s * y where E_s = E_i / (1 + y'_h) (Eq 3-99)
    # y'_h = (y/y_ref) * [1 + a * exp(-y/y_ref)] (Eq 3-100), a = 0.10
    a_const = 0.10

    y_max = max(7.0, b * 0.1)  # inches
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    for i, y in enumerate(y_arr):
        if y <= 0 or p_u <= 0:
            p_arr[i] = 0
        else:
            y_ratio = y / y_ref
            y_h_prime = y_ratio * (1.0 + a_const * math.exp(-y_ratio))
            E_s = E_i / (1.0 + y_h_prime)
            p_arr[i] = E_s * y

    p_ult = p_arr.max() if len(p_arr) > 0 else p_u

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult, method="Loess (Johnson)",
    )


def py_silt_cemented(
    depth_ft: float,
    phi: float,
    c: float,
    gamma_eff: float,
    B: float,
    k: float = 0.0,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Cemented c-phi soil (LPile Section 3.7) 4-segment p-y curve.

    For soils with both cohesion and friction (e.g., cemented sand,
    calcareous soils, residual soils). Follows Reese sand procedure
    with both frictional and cohesive components.

    Args:
        depth_ft: Depth below ground (ft)
        phi: Friction angle (degrees)
        c: Cohesion/cementation strength (psf)
        gamma_eff: Effective unit weight (pcf)
        B: Pile width (in)
        k: Initial modulus of subgrade reaction (lb/in^3). If 0, estimated.
        cyclic: Use cyclic loading
        n_points: Number of curve points
    """
    z = depth_ft
    B_ft = B / 12.0
    b = B
    phi_r = math.radians(phi)

    if z <= 0 or (phi <= 0 and c <= 0):
        y_arr = np.linspace(0, max(b * 0.1, 1.0), n_points)
        return PYCurve(depth_ft=depth_ft, depth_in=depth_ft * 12.0,
                       y=y_arr, p=np.zeros(n_points), p_ult=0.0,
                       method="Cemented c-phi")

    alpha = phi / 2.0
    beta = 45.0 + phi / 2.0
    alpha_r = math.radians(alpha)
    beta_r = math.radians(beta)
    K0 = 0.4
    Ka = math.tan(math.radians(45.0 - phi / 2.0)) ** 2 if phi > 0 else 1.0
    J_val = 0.5

    # Frictional component p_uphi = min(p_phis, p_phid) (Eq 3-109, 3-110)
    if phi > 0:
        sin_b = math.sin(beta_r)
        cos_a = math.cos(alpha_r)
        tan_b = math.tan(beta_r)
        tan_a = math.tan(alpha_r)
        tan_bmphi = math.tan(beta_r - phi_r) if abs(beta_r - phi_r) > 0.001 else 1e6

        p_phis = gamma_eff * z * (
            K0 * z * math.tan(phi_r) * sin_b / (tan_bmphi * cos_a)
            + tan_b / tan_bmphi * (B_ft + z * tan_b * tan_a)
            + K0 * z * tan_b * (math.tan(phi_r) * sin_b - tan_a)
            - Ka * B_ft
        )
        p_phid = Ka * B_ft * gamma_eff * z * (math.tan(beta_r) ** 8 - 1.0) \
            + K0 * B_ft * gamma_eff * z * math.tan(phi_r) * math.tan(beta_r) ** 4
        p_uphi = max(min(p_phis, p_phid), 0.0)
    else:
        p_uphi = 0.0

    # Cohesive component p_c = min(p_cs, p_cd) (Eq 3-112, 3-113)
    if c > 0:
        p_cs = (3.0 + gamma_eff / c * z + J_val / B_ft * z) * c * B_ft
        p_cd = 9.0 * c * B_ft
        p_uc = min(p_cs, p_cd)
    else:
        p_uc = 0.0

    # Depth factor (same as Reese sand, Figure 3.28)
    x_over_b = z / B_ft if B_ft > 0 else 0
    if cyclic:
        A_fac = max(0.88, 0.88) if x_over_b >= 5 else max(0.2 + 0.136 * x_over_b, 0.2)
        B_fac = max(0.55, 0.55) if x_over_b >= 5 else max(0.2 + 0.07 * x_over_b, 0.2)
    else:
        A_fac = max(0.88, 0.88) if x_over_b >= 5 else max(0.2 + 0.136 * x_over_b, 0.2)
        B_fac = max(0.50, 0.50) if x_over_b >= 5 else max(0.2 + 0.06 * x_over_b, 0.2)

    # Characteristic points (Eq 3-115 through 3-120)
    y_u = 3.0 * b / 80.0  # inches
    y_m = b / 60.0
    p_u_total = A_fac * p_uphi / 12.0  # Convert from lb/ft to lb/in
    p_m_total = B_fac * p_uphi / 12.0 + p_uc / 12.0

    # Residual: only frictional component (Eq 3-114)
    p_residual = A_fac * p_uphi / 12.0

    # Estimate k if not provided (Eq 3-122: k = k_c + k_phi)
    if k <= 0:
        k_phi = _api_sand_k(max(phi, 25), submerged=(gamma_eff < 80)) if phi > 0 else 0
        # k_c estimated from Figure 3.57 (simplified)
        if c > 0:
            c_tsf = c / 2000.0
            k_c = max(100.0 + 300.0 * c_tsf, 50.0)
        else:
            k_c = 0
        k = k_c + k_phi

    k_init = k * z * 12.0  # lb/in per in

    # Build parabolic section parameters
    if y_u > y_m and p_u_total > p_m_total:
        m_slope = (p_u_total - p_m_total) / (y_u - y_m)
    else:
        m_slope = p_m_total / y_m if y_m > 0 else 1.0

    n_exp = p_m_total / (abs(m_slope) * y_m) if abs(m_slope) * y_m > 0 else 1.0
    n_exp = max(min(n_exp, 5.0), 0.1)
    S_coeff = p_m_total / (y_m ** (1.0 / n_exp)) if y_m > 0 else 0

    # Intersection of initial line with parabola (Eq 3-128)
    if k_init > 0 and S_coeff > 0 and n_exp != 1.0:
        y_k = (S_coeff / k_init) ** (n_exp / (n_exp - 1.0)) if n_exp > 1.0 else 0
    else:
        y_k = 0

    y_max = max(y_u * 2.0, b * 0.1, 1.0)
    y_arr = np.linspace(0, y_max, n_points)
    p_arr = np.zeros(n_points)

    for i, y in enumerate(y_arr):
        if y <= 0:
            p_arr[i] = 0
        elif y <= y_k:
            p_arr[i] = k_init * y
        elif y <= y_m:
            p_arr[i] = S_coeff * y ** (1.0 / n_exp) if S_coeff > 0 else p_m_total
        elif y <= y_u:
            p_arr[i] = p_m_total + m_slope * (y - y_m)
        else:
            # Residual: only frictional component
            p_arr[i] = p_residual

    p_ult_curve = max(p_arr) if len(p_arr) > 0 else p_u_total

    return PYCurve(
        depth_ft=depth_ft, depth_in=depth_ft * 12.0,
        y=y_arr, p=p_arr, p_ult=p_ult_curve, method="Cemented c-phi",
    )


def generate_py_curve(
    depth_ft: float,
    layer: SoilLayer,
    sigma_v: float,
    B: float,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Select and generate the appropriate p-y curve for a layer.

    Routes to the correct p-y function based on layer.effective_py_model.
    """
    gamma_eff = layer.gamma_effective
    if gamma_eff <= 0:
        gamma_eff = 1.0  # Avoid division by zero

    model = layer.effective_py_model

    # --- Clay models ---
    if model == PYModel.SOFT_CLAY_MATLOCK:
        c_u = layer.get_cu()
        eps50 = layer.get_epsilon_50()
        J = layer.J if layer.J is not None else (0.25 if c_u < 500 else 0.5)
        return py_matlock_soft_clay(depth_ft, c_u, gamma_eff, B, J, eps50, cyclic, n_points)

    elif model == PYModel.API_SOFT_CLAY_USER_J:
        c_u = layer.get_cu()
        eps50 = layer.get_epsilon_50()
        J = layer.J if layer.J is not None else 0.5
        return py_matlock_soft_clay(depth_ft, c_u, gamma_eff, B, J, eps50, cyclic, n_points)

    elif model == PYModel.STIFF_CLAY_FREE_WATER:
        c_u = layer.get_cu()
        eps50 = layer.get_epsilon_50()
        k = layer.get_k_h()
        return py_stiff_clay_free_water(depth_ft, c_u, gamma_eff, B, eps50, k, cyclic, n_points)

    elif model == PYModel.STIFF_CLAY_NO_FREE_WATER:
        c_u = layer.get_cu()
        eps50 = layer.get_epsilon_50()
        return py_stiff_clay_no_free_water(depth_ft, c_u, gamma_eff, B, eps50, cyclic, 1, n_points)

    elif model == PYModel.MOD_STIFF_CLAY:
        c_u = layer.get_cu()
        eps50 = layer.get_epsilon_50()
        k = layer.get_k_h()
        return py_mod_stiff_clay(depth_ft, c_u, gamma_eff, B, eps50, k, cyclic, n_points)

    # --- Sand models ---
    elif model == PYModel.API_SAND:
        phi = layer.get_phi(sigma_v)
        return py_api_sand(depth_ft, phi, gamma_eff, B, cyclic, n_points)

    elif model == PYModel.SAND_REESE:
        phi = layer.get_phi(sigma_v)
        k = layer.get_k_h()
        return py_reese_sand(depth_ft, phi, gamma_eff, B, k, cyclic, n_points)

    elif model == PYModel.LIQUEFIED_SAND_ROLLINS:
        return py_liquefied_sand_rollins(depth_ft, B, n_points)

    elif model == PYModel.ELASTIC_SUBGRADE:
        k = layer.get_k_h()
        return py_elastic_subgrade(depth_ft, gamma_eff, B, k, n_points)

    # --- Sand models (continued) ---
    elif model == PYModel.SMALL_STRAIN_SAND:
        phi = layer.get_phi(sigma_v)
        G_max = layer.G_max if layer.G_max is not None else 0.0
        return py_small_strain_sand(depth_ft, phi, gamma_eff, B, G_max, cyclic, n_points)

    elif model == PYModel.LIQUEFIED_SAND_HYBRID:
        c_u_res = layer.get_cu() if layer.c_u else 50.0  # Residual strength
        return py_liquefied_sand_hybrid(depth_ft, c_u_res, gamma_eff, B, n_points)

    # --- Rock models ---
    elif model == PYModel.WEAK_ROCK:
        q_ur = layer.q_u if layer.q_u else 500 * 144  # Default 500 psi in psf
        E_ir = layer.E_ir if layer.E_ir else 0.0
        RQD = layer.RQD if layer.RQD else 0.0
        k_rm = layer.k_rm if layer.k_rm else 0.0005
        return py_weak_rock(depth_ft, q_ur, B, E_ir, RQD, k_rm, n_points)

    elif model == PYModel.STRONG_ROCK:
        q_ur = layer.q_u if layer.q_u else 1000 * 144  # Default 1000 psi in psf
        E_ir = layer.E_ir if layer.E_ir else 0.0
        return py_strong_rock(depth_ft, q_ur, B, E_ir, n_points)

    elif model == PYModel.MASSIVE_ROCK:
        sigma_ci = layer.sigma_ci if layer.sigma_ci else 5000.0  # psi
        m_i = layer.m_i if layer.m_i else 10.0
        GSI = layer.GSI if layer.GSI else 50.0
        E_rock = layer.E_rock if layer.E_rock else 0.0
        nu = layer.poissons_ratio if layer.poissons_ratio else 0.25
        return py_massive_rock(depth_ft, sigma_ci, gamma_eff, B, m_i, GSI, E_rock, nu, n_points)

    # --- Special soil models ---
    elif model == PYModel.PIEDMONT_RESIDUAL:
        c_u = layer.get_cu()
        eps50 = layer.get_epsilon_50()
        k = layer.get_k_h()
        return py_piedmont_residual(depth_ft, c_u, gamma_eff, B, eps50, k, cyclic, n_points)

    elif model == PYModel.LOESS:
        c_u = layer.get_cu()
        return py_loess(depth_ft, gamma_eff, B, q_c=0.0, c_u=c_u, N_cycles=1, n_points=n_points)

    elif model == PYModel.SILT_CEMENTED:
        phi = layer.get_phi(sigma_v)
        c = layer.get_cu()
        k = layer.get_k_h()
        return py_silt_cemented(depth_ft, phi, c, gamma_eff, B, k, cyclic, n_points)

    elif model == PYModel.USER_INPUT:
        # Placeholder: linear elastic if no data
        k = layer.get_k_h()
        curve = py_elastic_subgrade(depth_ft, gamma_eff, B, k, n_points)
        curve.method = "User-Input p-y (no data)"
        return curve

    # Default fallback (should not reach here)
    else:
        is_cohesive = layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC)
        if is_cohesive:
            c_u = layer.get_cu()
            eps50 = layer.get_epsilon_50()
            J = 0.25 if c_u < 500 else 0.5
            return py_matlock_soft_clay(depth_ft, c_u, gamma_eff, B, J, eps50, cyclic, n_points)
        else:
            phi = layer.get_phi(sigma_v)
            return py_api_sand(depth_ft, phi, gamma_eff, B, cyclic, n_points)


# ============================================================================
# Broms Simplified Lateral Capacity
# ============================================================================

@dataclass
class BromsResult:
    method: str
    H_ult: float            # Ultimate lateral capacity (lbs)
    H_allow: float          # Allowable lateral capacity (lbs)
    failure_mode: str        # "short" or "long"
    depth_to_max_moment: float  # ft
    M_max: float            # Maximum moment (ft-lbs)
    FS: float
    notes: list[str]


def broms_cohesionless(
    phi: float,
    gamma: float,
    B: float,
    L: float,
    e: float,
    EI: float,
    My: float,
    FS: float = 2.0,
) -> BromsResult:
    """Broms method for free-head pile in cohesionless soil.

    Args:
        phi: Friction angle (degrees)
        gamma: Effective unit weight (pcf)
        B: Pile width (in)
        L: Embedded length (ft)
        e: Load eccentricity above ground (ft)
        EI: Flexural rigidity (lb-in^2)
        My: Yield moment (kip-in)
        FS: Factor of safety
    """
    Kp = math.tan(math.radians(45 + phi / 2)) ** 2
    B_ft = B / 12.0
    My_ft_lbs = My * 1000.0 / 12.0  # kip-in to ft-lbs

    # Short pile capacity
    H_short = 0.5 * Kp * gamma * B_ft * L**2 / (1 + e / L) if L > 0 else 0

    # Long pile: iterative — find H where M_max = My
    # M_max = H * (e + 0.67 * f), f = sqrt(H / (Kp * gamma * B_ft))
    def moment_eq(H):
        if H <= 0:
            return -My_ft_lbs
        f = math.sqrt(H / (Kp * gamma * B_ft)) if Kp * gamma * B_ft > 0 else 0
        return H * (e + 0.67 * f) - My_ft_lbs

    try:
        H_long = _bisect(moment_eq, 0.1, 500000, maxiter=200)
    except ValueError:
        H_long = float("inf")

    if H_short < H_long:
        H_ult = H_short
        mode = "short (rigid body rotation)"
        f = 0.0
    else:
        H_ult = H_long
        mode = "long (structural yield)"
        f = math.sqrt(H_long / (Kp * gamma * B_ft)) if Kp * gamma * B_ft > 0 else 0

    depth_max_m = math.sqrt(H_ult / (Kp * gamma * B_ft)) if Kp * gamma * B_ft > 0 else 0
    M_max = H_ult * (e + 0.67 * depth_max_m)

    return BromsResult(
        method="Broms - Cohesionless",
        H_ult=H_ult,
        H_allow=H_ult / FS,
        failure_mode=mode,
        depth_to_max_moment=depth_max_m,
        M_max=M_max,
        FS=FS,
        notes=[
            f"K_p = {Kp:.2f}",
            f"Short pile H_ult = {H_short:.0f} lbs",
            f"Long pile H_ult = {H_long:.0f} lbs",
            f"Governing: {mode}",
        ],
    )


def broms_cohesive(
    c_u: float,
    B: float,
    L: float,
    e: float,
    EI: float,
    My: float,
    FS: float = 2.0,
) -> BromsResult:
    """Broms method for free-head pile in cohesive soil.

    Args:
        c_u: Undrained shear strength (psf)
        B: Pile width (in)
        L: Embedded length (ft)
        e: Eccentricity above ground (ft)
        EI: Flexural rigidity (lb-in^2)
        My: Yield moment (kip-in)
        FS: Factor of safety
    """
    B_ft = B / 12.0
    My_ft_lbs = My * 1000.0 / 12.0

    # Short pile: H = 9*c_u*B*(L-1.5B) / (2*(1 + 1.5*e/L))
    L_eff = L - 1.5 * B_ft
    if L_eff > 0:
        H_short = 9.0 * c_u * B_ft * L_eff / (2.0 * (1.0 + 1.5 * e / L))
    else:
        H_short = 0.0

    # Long pile: M_max = My, solve for H
    # M_max = H*(e + 1.5*B_ft + 0.5*f), f = H/(9*c_u*B_ft)
    denom = 9.0 * c_u * B_ft
    if denom > 0:
        # H*(e + 1.5*B_ft + 0.5*H/(9*c_u*B_ft)) = My
        # 0.5/(9*c_u*B_ft) * H^2 + (e+1.5*B_ft)*H - My = 0
        a_coeff = 0.5 / denom
        b_coeff = e + 1.5 * B_ft
        c_coeff = -My_ft_lbs
        disc = b_coeff**2 - 4 * a_coeff * c_coeff
        if disc >= 0 and a_coeff > 0:
            H_long = (-b_coeff + math.sqrt(disc)) / (2 * a_coeff)
        else:
            H_long = float("inf")
    else:
        H_long = float("inf")

    if H_short < H_long:
        H_ult = H_short
        mode = "short (rigid body rotation)"
    else:
        H_ult = H_long
        mode = "long (structural yield)"

    f = H_ult / denom if denom > 0 else 0
    M_max = H_ult * (e + 1.5 * B_ft + 0.5 * f)

    return BromsResult(
        method="Broms - Cohesive",
        H_ult=H_ult,
        H_allow=H_ult / FS,
        failure_mode=mode,
        depth_to_max_moment=1.5 * B_ft + f,
        M_max=M_max,
        FS=FS,
        notes=[
            f"c_u = {c_u:.0f} psf",
            f"Short pile H_ult = {H_short:.0f} lbs",
            f"Long pile H_ult = {H_long:.0f} lbs",
            f"Governing: {mode}",
        ],
    )


# ============================================================================
# Finite Difference Lateral Pile Solver
# ============================================================================

@dataclass
class LateralResult:
    """Full lateral analysis results."""
    # Input summary
    H_applied: float        # Applied lateral load (lbs)
    M_applied: float        # Applied moment at ground (ft-lbs)
    head_condition: str     # "free" or "fixed"

    # Deflection and force profiles
    depth_ft: np.ndarray
    deflection_in: np.ndarray
    slope_rad: np.ndarray
    moment_ft_lbs: np.ndarray
    shear_lbs: np.ndarray
    soil_reaction_lb_in: np.ndarray

    # Key results
    y_ground: float         # Ground-line deflection (in)
    M_max: float            # Maximum moment (ft-lbs)
    depth_M_max: float      # Depth of maximum moment (ft)
    depth_zero_defl: float  # Depth of first zero deflection (ft)

    # p-y curves at selected depths
    py_curves: list[PYCurve]

    # Convergence info
    converged: bool
    iterations: int
    notes: list[str]


def solve_lateral(
    profile: SoilProfile,
    pile_width: float,
    EI: float,
    embedment: float,
    H: float,
    M_ground: float = 0,
    head_condition: str = "free",
    cyclic: bool = False,
    n_elements: int = 100,
    max_iter: int = 200,
    tol: float = 1e-4,
) -> LateralResult:
    """Solve lateral pile response using finite difference method.

    Args:
        profile: SoilProfile object
        pile_width: Pile width/diameter (in)
        EI: Flexural rigidity (lb-in^2)
        embedment: Embedded pile length (ft)
        H: Applied lateral load at ground line (lbs)
        M_ground: Applied moment at ground line (ft-lbs)
        head_condition: "free" or "fixed"
        cyclic: Use cyclic p-y curves
        n_elements: Number of finite difference elements
        max_iter: Maximum iterations for nonlinear convergence
        tol: Convergence tolerance (relative)

    Returns:
        LateralResult with full depth profiles and key values
    """
    notes = []
    L_in = embedment * 12.0
    dz = L_in / n_elements
    n_nodes = n_elements + 1

    # Generate p-y curves at each node
    py_at_node: list[PYCurve | None] = []
    for i in range(n_nodes):
        z_in = i * dz
        z_ft = z_in / 12.0
        layer = profile.layer_at_depth(z_ft)
        if layer is None or z_ft <= 0.001:
            py_at_node.append(None)
            continue
        sigma_v = profile.effective_stress_at(z_ft)
        py = generate_py_curve(z_ft, layer, sigma_v, pile_width, cyclic)
        py_at_node.append(py)

    # Initial stiffness (secant from p-y curves)
    k_soil = np.zeros(n_nodes)
    for i in range(n_nodes):
        py = py_at_node[i]
        if py is not None and py.p_ult > 0:
            # Initial linear stiffness
            y_small = py.y[1] if len(py.y) > 1 and py.y[1] > 0 else 0.01
            p_small = py.p[1] if len(py.p) > 1 else 0
            k_soil[i] = p_small / y_small if y_small > 0 else 0

    # Iterative FDM solution
    y = np.zeros(n_nodes)
    converged = False
    iterations = 0

    for iteration in range(max_iter):
        # Build stiffness matrix [K]{y} = {F}
        # EI * d4y/dz4 + k(y)*y = 0 interior
        # Boundary conditions at top and bottom
        K = np.zeros((n_nodes, n_nodes))
        F = np.zeros(n_nodes)

        # Interior nodes: EI*(y[i-2]-4*y[i-1]+6*y[i]-4*y[i+1]+y[i+2])/dz^4 + k*y[i] = 0
        for i in range(2, n_nodes - 2):
            coeff = EI / dz**4
            K[i, i - 2] += coeff
            K[i, i - 1] += -4.0 * coeff
            K[i, i] += 6.0 * coeff + k_soil[i]
            K[i, i + 1] += -4.0 * coeff
            K[i, i + 2] += coeff

        # Boundary conditions at pile head (node 0, 1)
        if head_condition == "free":
            # Node 0: Shear = H -> EI * d3y/dz3 = H
            # Using FD: EI*(-y[0]+2*y[1]-2*y[3]+y[4])/(2*dz^3) = H (centered needs ghost)
            # Simplified: use first 2 rows for shear and moment BCs
            # Shear BC: EI*(-y[0]+3*y[1]-3*y[2]+y[3])/dz^3 = H
            coeff_s = EI / dz**3
            K[0, 0] = -coeff_s
            K[0, 1] = 3.0 * coeff_s
            K[0, 2] = -3.0 * coeff_s
            K[0, 3] = coeff_s
            F[0] = H

            # Moment BC: EI*(y[0]-2*y[1]+y[2])/dz^2 = M_ground
            coeff_m = EI / dz**2
            K[1, 0] = coeff_m
            K[1, 1] = -2.0 * coeff_m
            K[1, 2] = coeff_m
            F[1] = M_ground * 12.0  # ft-lbs to in-lbs

        else:  # fixed head
            # Node 0: Shear = H
            coeff_s = EI / dz**3
            K[0, 0] = -coeff_s
            K[0, 1] = 3.0 * coeff_s
            K[0, 2] = -3.0 * coeff_s
            K[0, 3] = coeff_s
            F[0] = H

            # Slope = 0 at head: (y[1]-y[0])/dz = 0 -> y[0]=y[1] (simplified)
            K[1, 0] = 1.0
            K[1, 1] = -1.0
            F[1] = 0.0

        # Boundary at pile tip (node n-2, n-1)
        # Free tip: moment = 0 and shear = 0
        n = n_nodes
        coeff_m = EI / dz**2
        K[n - 2, n - 3] = coeff_m
        K[n - 2, n - 2] = -2.0 * coeff_m
        K[n - 2, n - 1] = coeff_m
        F[n - 2] = 0.0

        coeff_s = EI / dz**3
        K[n - 1, n - 4] = -coeff_s if n >= 5 else 0
        K[n - 1, n - 3] = 3.0 * coeff_s
        K[n - 1, n - 2] = -3.0 * coeff_s
        K[n - 1, n - 1] = coeff_s
        F[n - 1] = 0.0

        # Solve
        try:
            y_new = np.linalg.solve(K, F)
        except np.linalg.LinAlgError:
            notes.append("Matrix solve failed — ill-conditioned system")
            break

        # Check convergence
        if iteration > 0:
            max_y = max(abs(y_new).max(), 1e-10)
            change = abs(y_new - y).max() / max_y
            if change < tol:
                converged = True
                y = y_new
                iterations = iteration + 1
                break

        y = y_new

        # Update soil stiffness (secant modulus from p-y curves)
        for i in range(n_nodes):
            py = py_at_node[i]
            if py is None or abs(y[i]) < 1e-10:
                k_soil[i] = 0
                continue
            y_abs = abs(y[i])
            p_val = np.interp(y_abs, py.y, py.p)
            k_soil[i] = p_val / y_abs if y_abs > 0 else 0

        iterations = iteration + 1

    if not converged:
        notes.append(f"Did not converge in {max_iter} iterations (last change: {change:.2e})")

    # Post-process: compute moment, shear, soil reaction
    depth_in = np.arange(n_nodes) * dz
    depth_ft_arr = depth_in / 12.0

    moment_in_lbs = np.zeros(n_nodes)
    for i in range(1, n_nodes - 1):
        moment_in_lbs[i] = EI * (y[i - 1] - 2 * y[i] + y[i + 1]) / dz**2
    moment_ft_lbs = moment_in_lbs / 12.0  # in-lbs to ft-lbs

    shear_lbs = np.zeros(n_nodes)
    for i in range(1, n_nodes - 1):
        shear_lbs[i] = EI * (y[i + 1] - y[i - 1]) / (2 * dz**3)
        # Better: shear = dM/dz
    # Compute shear from moment gradient
    for i in range(1, n_nodes - 1):
        shear_lbs[i] = (moment_in_lbs[i + 1] - moment_in_lbs[i - 1]) / (2 * dz)
    shear_lbs[0] = H

    soil_p = np.zeros(n_nodes)
    for i in range(n_nodes):
        soil_p[i] = k_soil[i] * y[i]

    slope = np.zeros(n_nodes)
    for i in range(1, n_nodes - 1):
        slope[i] = (y[i + 1] - y[i - 1]) / (2 * dz)

    # Key results
    y_ground = y[0]
    M_max_idx = np.argmax(np.abs(moment_ft_lbs))
    M_max = moment_ft_lbs[M_max_idx]
    depth_M_max = depth_ft_arr[M_max_idx]

    # Depth of zero deflection
    zero_crossings = np.where(np.diff(np.sign(y)))[0]
    if len(zero_crossings) > 0:
        depth_zero = depth_ft_arr[zero_crossings[0]]
    else:
        depth_zero = embedment

    # Collect select p-y curves for display
    display_depths = [1, 3, 5, 8, 10]
    display_curves = []
    for d in display_depths:
        if d < embedment:
            layer = profile.layer_at_depth(d)
            if layer:
                sv = profile.effective_stress_at(d)
                display_curves.append(generate_py_curve(d, layer, sv, pile_width, cyclic))

    return LateralResult(
        H_applied=H,
        M_applied=M_ground,
        head_condition=head_condition,
        depth_ft=depth_ft_arr,
        deflection_in=y,
        slope_rad=slope,
        moment_ft_lbs=moment_ft_lbs,
        shear_lbs=shear_lbs,
        soil_reaction_lb_in=soil_p,
        y_ground=y_ground,
        M_max=M_max,
        depth_M_max=depth_M_max,
        depth_zero_defl=depth_zero,
        py_curves=display_curves,
        converged=converged,
        iterations=iterations,
        notes=notes,
    )


def depth_of_fixity(EI: float, soil_type: str, n_h: float = 0, k_h: float = 0) -> float:
    """Approximate depth of fixity (ft).

    Args:
        EI: Flexural rigidity (lb-in^2)
        soil_type: "sand" or "clay"
        n_h: Constant of horizontal subgrade reaction (lb/in^3) — sand
        k_h: Horizontal subgrade modulus (lb/in^3) — clay
    """
    if soil_type == "sand" and n_h > 0:
        T = (EI / n_h) ** 0.2  # in
        return 1.8 * T / 12.0  # ft
    elif k_h > 0:
        R = (EI / k_h) ** 0.25  # in
        return 1.4 * R / 12.0  # ft
    return 5.0  # default 5 ft


def minimum_embedment_broms(
    profile,  # SoilProfile
    B: float,
    EI: float,
    My: float,
    H_required: float,
    e: float = 4.0,
    L_min: float = 1.0,
    L_max: float = 50.0,
    tol: float = 0.01,
) -> dict:
    """Find minimum embedment for lateral stability using Broms bisection.

    Args:
        profile: SoilProfile (uses top layer properties).
        B: Pile width (in).
        EI: Flexural rigidity (lb-in^2).
        My: Yield moment (kip-in).
        H_required: Required lateral capacity (lbs) — typically H_applied * FS.
        e: Load eccentricity above ground (ft).
        L_min: Lower search bound (ft).
        L_max: Upper search bound (ft).
        tol: Convergence tolerance (ft).

    Returns:
        dict with L_min_ft, H_ult_at_L_min, failure_mode, FS_achieved, method, notes.
    """
    from .soil import SoilType

    if not profile.layers:
        return {"L_min_ft": None, "notes": ["No soil layers defined"]}

    top_layer = profile.layers[0]
    is_cohesive = top_layer.soil_type in (
        SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC,
    )

    def _broms_capacity(L: float) -> BromsResult:
        if is_cohesive:
            c_u = top_layer.get_cu()
            return broms_cohesive(c_u=c_u, B=B, L=L, e=e, EI=EI, My=My, FS=1.0)
        else:
            phi = top_layer.get_phi()
            gamma = top_layer.gamma_effective
            return broms_cohesionless(
                phi=phi, gamma=gamma, B=B, L=L, e=e, EI=EI, My=My, FS=1.0,
            )

    # Check if even L_max is sufficient
    result_max = _broms_capacity(L_max)
    if result_max.H_ult < H_required:
        return {
            "L_min_ft": None,
            "H_ult_at_L_min": result_max.H_ult,
            "failure_mode": result_max.failure_mode,
            "FS_achieved": result_max.H_ult / H_required if H_required > 0 else 0,
            "method": result_max.method,
            "notes": [f"Cannot achieve H_required={H_required:.0f} lbs even at L={L_max} ft"],
        }

    # Bisection
    a, b = L_min, L_max
    result = result_max
    for _ in range(100):
        mid = (a + b) / 2.0
        result = _broms_capacity(mid)
        if result.H_ult >= H_required:
            b = mid
        else:
            a = mid
        if (b - a) < tol:
            break

    L_found = round(b, 2)  # conservative upper bound
    result = _broms_capacity(L_found)

    return {
        "L_min_ft": L_found,
        "H_ult_at_L_min": result.H_ult,
        "failure_mode": result.failure_mode,
        "FS_achieved": result.H_ult / H_required if H_required > 0 else 0,
        "method": result.method,
        "notes": result.notes,
    }


# ============================================================================
# Internal Helpers
# ============================================================================

def _api_coefficients(phi: float) -> tuple[float, float, float]:
    """Interpolate API C1, C2, C3 from phi'."""
    table = [
        (25, 1.22, 2.88, 12.7),
        (28, 1.78, 3.29, 20.8),
        (30, 2.46, 3.81, 31.4),
        (32, 3.39, 4.47, 47.9),
        (34, 4.68, 5.30, 73.9),
        (36, 6.50, 6.37, 115.4),
        (38, 9.10, 7.78, 182.5),
        (40, 12.85, 9.64, 292.0),
    ]
    if phi <= table[0][0]:
        return table[0][1], table[0][2], table[0][3]
    if phi >= table[-1][0]:
        return table[-1][1], table[-1][2], table[-1][3]
    for i in range(len(table) - 1):
        p1, c1a, c2a, c3a = table[i]
        p2, c1b, c2b, c3b = table[i + 1]
        if p1 <= phi <= p2:
            f = (phi - p1) / (p2 - p1)
            return (
                c1a + f * (c1b - c1a),
                c2a + f * (c2b - c2a),
                c3a + f * (c3b - c3a),
            )
    return 2.46, 3.81, 31.4


def _api_sand_k(phi: float, submerged: bool = False) -> float:
    """Initial modulus of subgrade reaction k (lb/in^3) for API sand."""
    table_dry = [
        (25, 25), (28, 28), (30, 60), (32, 90), (34, 115),
        (36, 150), (38, 200), (40, 300),
    ]
    table_sub = [
        (25, 5), (28, 10), (30, 25), (32, 35), (34, 45),
        (36, 60), (38, 80), (40, 100),
    ]
    table = table_sub if submerged else table_dry
    if phi <= table[0][0]:
        return table[0][1]
    if phi >= table[-1][0]:
        return table[-1][1]
    for i in range(len(table) - 1):
        p1, k1 = table[i]
        p2, k2 = table[i + 1]
        if p1 <= phi <= p2:
            return k1 + (k2 - k1) * (phi - p1) / (p2 - p1)
    return 60.0
