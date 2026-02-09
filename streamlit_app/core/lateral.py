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

from .soil import SoilProfile, SoilLayer, SoilType, GAMMA_WATER


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


def generate_py_curve(
    depth_ft: float,
    layer: SoilLayer,
    sigma_v: float,
    B: float,
    cyclic: bool = False,
    n_points: int = 50,
) -> PYCurve:
    """Auto-select and generate the appropriate p-y curve for a layer."""
    gamma_eff = layer.gamma_effective
    if gamma_eff <= 0:
        gamma_eff = 1.0  # Avoid division by zero

    is_cohesive = layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC)

    if is_cohesive:
        c_u = layer.get_cu()
        eps50 = layer.get_epsilon_50()
        J = 0.25 if c_u < 500 else 0.5
        return py_matlock_soft_clay(
            depth_ft, c_u, gamma_eff, B, J, eps50, cyclic, n_points,
        )
    else:
        phi = layer.get_phi(sigma_v)
        return py_api_sand(
            depth_ft, phi, gamma_eff, B, cyclic, n_points,
        )


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
