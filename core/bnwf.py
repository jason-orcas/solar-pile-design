"""BNWF (Beam on Nonlinear Winkler Foundation) analysis.

Pure Python solver using direct stiffness method with nonlinear p-y, t-z,
and q-z springs. Supports combined axial+lateral loading, P-delta effects,
pushover analysis, stiffness matrix extraction, and buckling estimation.

Also serves as the facade that optionally delegates to bnwf_opensees.py
when OpenSeesPy is available and advanced features are requested.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .soil import SoilProfile, SoilLayer, SoilType
from .sections import SteelSection, CustomPileSection
from .lateral import generate_py_curve, PYCurve
from .tz_qz import generate_tz_curve, generate_qz_curve, TZCurve, QZCurve


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class BNWFLoadInput:
    """Load input for BNWF analysis."""
    V_axial: float = 0.0           # Axial load (lbs): + compression, - tension
    H_lateral: float = 0.0         # Lateral load at ground (lbs)
    M_ground: float = 0.0          # Moment at ground (ft-lbs)
    load_type: str = "static"      # "static" | "pushover_lateral" | "pushover_axial"
    pushover_steps: int = 20
    pushover_max_mult: float = 3.0


@dataclass
class BNWFOptions:
    """Configuration for BNWF analysis."""
    n_elements: int = 50
    bending_axis: str = "strong"
    head_condition: str = "free"
    cyclic: bool = False
    include_p_delta: bool = True
    max_iter: int = 300
    tol: float = 1e-5
    solver: str = "auto"              # "auto" | "python" | "opensees"
    use_fiber_section: bool = False   # OpenSees only
    run_eigenvalue: bool = False      # OpenSees only
    n_modes: int = 3                  # OpenSees only
    pile_type: str = "driven"
    _skip_post: bool = False          # Internal: skip K_head/buckling to avoid recursion


@dataclass
class BNWFResult:
    """Complete BNWF analysis results."""
    # Metadata
    solver_used: str
    analysis_type: str
    converged: bool
    iterations: int
    notes: list[str]

    # Depth profiles
    depth_ft: np.ndarray
    deflection_lateral_in: np.ndarray
    deflection_axial_in: np.ndarray
    moment_ft_lbs: np.ndarray
    shear_lbs: np.ndarray
    axial_force_lbs: np.ndarray
    soil_reaction_p_lb_in: np.ndarray    # lateral p
    soil_reaction_t_lb_in: np.ndarray    # axial skin friction t
    soil_reaction_q_lbs: float           # tip reaction

    # Scalar results
    y_ground_lateral: float
    y_ground_axial: float
    M_max: float
    depth_M_max: float

    # Pile head stiffness matrix (3x3: axial, lateral, rotational)
    K_head: np.ndarray

    # Pushover data
    pushover_load: list[float] | None = None
    pushover_disp: list[float] | None = None
    pushover_axis: str | None = None

    # Spring curves at display depths
    py_curves: list = field(default_factory=list)
    tz_curves: list = field(default_factory=list)
    qz_curve: QZCurve | None = None

    # Eigenvalue results (OpenSees only)
    eigenvalues: list[float] | None = None
    frequencies_hz: list[float] | None = None

    # Buckling
    P_critical: float | None = None


# ============================================================================
# Facade: Solver Selection
# ============================================================================

def run_bnwf_analysis(
    profile: SoilProfile,
    section: SteelSection | CustomPileSection,
    embedment: float,
    loads: BNWFLoadInput,
    options: BNWFOptions,
) -> BNWFResult:
    """Run BNWF analysis, selecting the best available solver.

    Args:
        profile: SoilProfile with soil layers
        section: Pile cross-section properties
        embedment: Embedment depth (ft)
        loads: Applied loads
        options: Analysis configuration

    Returns:
        BNWFResult with complete analysis output
    """
    use_opensees = False

    if options.solver == "opensees":
        use_opensees = True
    elif options.solver == "auto":
        # Use OpenSees if available AND an advanced feature is requested
        needs_opensees = (
            options.use_fiber_section or
            options.run_eigenvalue
        )
        if needs_opensees:
            use_opensees = True

    if use_opensees:
        try:
            from .bnwf_opensees import _solve_bnwf_opensees
            return _solve_bnwf_opensees(profile, section, embedment, loads, options)
        except ImportError:
            # Fall back to Python solver
            pass

    # Python solver
    if loads.load_type.startswith("pushover"):
        return _pushover_python(profile, section, embedment, loads, options)
    else:
        return _solve_bnwf_python(profile, section, embedment, loads, options)


# ============================================================================
# Pure Python Direct Stiffness BNWF Solver
# ============================================================================

def _solve_bnwf_python(
    profile: SoilProfile,
    section: SteelSection | CustomPileSection,
    embedment: float,
    loads: BNWFLoadInput,
    options: BNWFOptions,
) -> BNWFResult:
    """Solve BNWF using direct stiffness method with nonlinear springs.

    3 DOFs per node: u (axial), v (lateral), theta (rotation).
    Beam-column elements with optional P-delta geometric stiffness.
    """
    notes: list[str] = []
    n_elem = options.n_elements
    n_nodes = n_elem + 1
    n_dof = 3 * n_nodes  # u, v, theta per node

    L_in = embedment * 12.0
    dz = L_in / n_elem

    # Section properties
    if options.bending_axis == "strong":
        EI = section.EI_strong
    else:
        EI = section.EI_weak
    E = 29000.0 * 1000.0  # psi
    A = section.area       # in^2
    EA = E * A
    pile_width = section.depth if options.bending_axis == "strong" else section.width
    pile_perimeter = section.perimeter

    # Generate soil springs at each node
    py_at_node: list[PYCurve | None] = []
    tz_at_node: list[TZCurve | None] = []

    for i in range(n_nodes):
        z_in = i * dz
        z_ft = z_in / 12.0
        layer = profile.layer_at_depth(z_ft)

        if layer is None or z_ft <= 0.001:
            py_at_node.append(None)
            tz_at_node.append(None)
            continue

        sigma_v = profile.effective_stress_at(z_ft)
        py = generate_py_curve(z_ft, layer, sigma_v, pile_width, options.cyclic)
        tz = generate_tz_curve(z_ft, layer, sigma_v, pile_perimeter,
                               pile_width, options.pile_type)
        py_at_node.append(py)
        tz_at_node.append(tz)

    # q-z spring at tip
    tip_layer = profile.layer_at_depth(embedment - 0.01)
    if tip_layer is not None:
        sigma_v_tip = profile.effective_stress_at(embedment)
        qz = generate_qz_curve(tip_layer, sigma_v_tip, section.tip_area,
                                pile_width)
    else:
        qz = None

    # Initial spring stiffnesses (secant)
    k_py = np.zeros(n_nodes)  # lateral spring stiffness (lb/in per in of pile)
    k_tz = np.zeros(n_nodes)  # axial spring stiffness (lb/in per in of pile)
    k_qz = 0.0               # tip spring stiffness (lb/in)

    for i in range(n_nodes):
        py = py_at_node[i]
        if py is not None and py.p_ult > 0 and len(py.y) > 1 and py.y[1] > 0:
            k_py[i] = py.p[1] / py.y[1]
        tz = tz_at_node[i]
        if tz is not None and tz.t_ult > 0 and len(tz.z) > 1 and tz.z[1] > 0:
            k_tz[i] = tz.t[1] / tz.z[1]

    if qz is not None and qz.q_ult > 0 and len(qz.z) > 1 and qz.z[1] > 0:
        k_qz = qz.q[1] / qz.z[1]

    # DOF mapping: node i -> [3*i (axial u), 3*i+1 (lateral v), 3*i+2 (rotation theta)]
    d = np.zeros(n_dof)
    converged = False
    iterations = 0

    for iteration in range(options.max_iter):
        K = np.zeros((n_dof, n_dof))
        F = np.zeros(n_dof)

        # Assemble beam-column element stiffnesses
        for e in range(n_elem):
            ni = e
            nj = e + 1
            _add_beam_stiffness(K, ni, nj, EA, EI, dz)

            # P-delta geometric stiffness
            if options.include_p_delta and iteration > 0:
                # Axial force in this element from previous iteration
                u_i = d[3 * ni]
                u_j = d[3 * nj]
                N_elem = EA * (u_i - u_j) / dz  # compression positive
                if abs(N_elem) > 1.0:
                    _add_geometric_stiffness(K, ni, nj, N_elem, dz)

        # Assemble spring stiffnesses (tributary length = dz, half at ends)
        for i in range(n_nodes):
            trib = dz
            if i == 0 or i == n_nodes - 1:
                trib = dz / 2.0

            # Lateral p-y spring on DOF 3*i+1 (v)
            idx_v = 3 * i + 1
            K[idx_v, idx_v] += k_py[i] * trib

            # Axial t-z spring on DOF 3*i (u)
            idx_u = 3 * i
            K[idx_u, idx_u] += k_tz[i] * trib

        # q-z spring at tip node (axial DOF)
        idx_tip_u = 3 * (n_nodes - 1)
        K[idx_tip_u, idx_tip_u] += k_qz

        # Apply loads at pile head (node 0)
        F[0] = -loads.V_axial       # axial: compression = negative displacement
        F[1] = loads.H_lateral       # lateral
        F[2] = loads.M_ground * 12.0  # moment (ft-lbs -> in-lbs)

        # Boundary conditions at pile head
        if options.head_condition == "fixed":
            # Fix rotation at head: theta_0 = 0
            # Use penalty method
            penalty = 1e12 * EI / dz
            K[2, 2] += penalty
            F[2] = 0.0

        # Solve
        try:
            d_new = np.linalg.solve(K, F)
        except np.linalg.LinAlgError:
            notes.append("Matrix solve failed — system is singular or ill-conditioned")
            break

        # Check convergence
        if iteration > 0:
            max_d = max(np.abs(d_new).max(), 1e-12)
            change = np.abs(d_new - d).max() / max_d
            if change < options.tol:
                converged = True
                d = d_new
                iterations = iteration + 1
                break

        d = d_new

        # Update nonlinear spring stiffnesses (secant)
        for i in range(n_nodes):
            # Lateral
            py = py_at_node[i]
            v_abs = abs(d[3 * i + 1])
            if py is not None and v_abs > 1e-12:
                p_val = np.interp(v_abs, py.y, py.p)
                k_py[i] = p_val / v_abs
            elif py is None:
                k_py[i] = 0.0

            # Axial skin friction
            tz = tz_at_node[i]
            u_abs = abs(d[3 * i])
            if tz is not None and u_abs > 1e-12:
                t_val = np.interp(u_abs, tz.z, tz.t)
                k_tz[i] = t_val / u_abs
            elif tz is None:
                k_tz[i] = 0.0

        # q-z at tip
        if qz is not None:
            u_tip = abs(d[idx_tip_u])
            if u_tip > 1e-12:
                q_val = np.interp(u_tip, qz.z, qz.q)
                k_qz = q_val / u_tip

        iterations = iteration + 1

    if not converged and iterations >= options.max_iter:
        notes.append(f"Did not converge in {options.max_iter} iterations")

    # ---- Post-process results ----
    depth_ft = np.array([i * dz / 12.0 for i in range(n_nodes)])
    u_axial = np.array([d[3 * i] for i in range(n_nodes)])
    v_lateral = np.array([d[3 * i + 1] for i in range(n_nodes)])
    theta = np.array([d[3 * i + 2] for i in range(n_nodes)])

    # Moments and shears from beam curvature
    moment_in_lbs = np.zeros(n_nodes)
    for i in range(1, n_nodes - 1):
        moment_in_lbs[i] = EI * (v_lateral[i - 1] - 2 * v_lateral[i] + v_lateral[i + 1]) / dz**2
    moment_ft_lbs = moment_in_lbs / 12.0

    shear = np.zeros(n_nodes)
    for i in range(1, n_nodes - 1):
        shear[i] = (moment_in_lbs[i + 1] - moment_in_lbs[i - 1]) / (2 * dz)
    shear[0] = loads.H_lateral

    # Axial force in elements
    axial_force = np.zeros(n_nodes)
    axial_force[0] = loads.V_axial
    for i in range(1, n_nodes):
        # Axial force reduces as skin friction is mobilized
        trib = dz if i < n_nodes - 1 else dz / 2.0
        tz = tz_at_node[i]
        if tz is not None:
            u_abs = abs(u_axial[i])
            t_mob = np.interp(u_abs, tz.z, tz.t) if u_abs > 1e-12 else 0.0
        else:
            t_mob = 0.0
        axial_force[i] = axial_force[i - 1] - t_mob * trib

    # Soil reactions
    soil_p = np.zeros(n_nodes)
    soil_t = np.zeros(n_nodes)
    for i in range(n_nodes):
        trib = dz if (0 < i < n_nodes - 1) else dz / 2.0
        soil_p[i] = k_py[i] * v_lateral[i]
        soil_t[i] = k_tz[i] * u_axial[i]

    q_tip = 0.0
    if qz is not None:
        u_tip = abs(u_axial[-1])
        q_tip = float(np.interp(u_tip, qz.z, qz.q)) if u_tip > 1e-12 else 0.0

    # Key scalar results
    y_ground_lateral = float(v_lateral[0])
    y_ground_axial = float(u_axial[0])
    M_max_idx = int(np.argmax(np.abs(moment_ft_lbs)))
    M_max = float(moment_ft_lbs[M_max_idx])
    depth_M_max = float(depth_ft[M_max_idx])

    # Stiffness matrix extraction and buckling (skip during inner unit-load solves)
    if options._skip_post:
        K_head = np.zeros((3, 3))
        P_crit = None
    else:
        K_head = _compute_head_stiffness(profile, section, embedment, options)
        P_crit = _estimate_buckling(profile, section, embedment, options)

    # Collect display curves at representative depths
    display_depths = [1, 3, 5, 8, 10]
    disp_py: list[PYCurve] = []
    disp_tz: list[TZCurve] = []
    for dd in display_depths:
        if dd < embedment:
            layer = profile.layer_at_depth(dd)
            if layer:
                sv = profile.effective_stress_at(dd)
                disp_py.append(generate_py_curve(dd, layer, sv, pile_width, options.cyclic))
                disp_tz.append(generate_tz_curve(dd, layer, sv, pile_perimeter,
                                                  pile_width, options.pile_type))

    notes.append(f"Solver: Pure Python direct stiffness ({n_elem} elements)")
    notes.append(f"P-delta: {'enabled' if options.include_p_delta else 'disabled'}")

    return BNWFResult(
        solver_used="python",
        analysis_type="static",
        converged=converged,
        iterations=iterations,
        notes=notes,
        depth_ft=depth_ft,
        deflection_lateral_in=v_lateral,
        deflection_axial_in=u_axial,
        moment_ft_lbs=moment_ft_lbs,
        shear_lbs=shear,
        axial_force_lbs=axial_force,
        soil_reaction_p_lb_in=soil_p,
        soil_reaction_t_lb_in=soil_t,
        soil_reaction_q_lbs=q_tip,
        y_ground_lateral=y_ground_lateral,
        y_ground_axial=y_ground_axial,
        M_max=M_max,
        depth_M_max=depth_M_max,
        K_head=K_head,
        py_curves=disp_py,
        tz_curves=disp_tz,
        qz_curve=qz,
        P_critical=P_crit,
    )


# ============================================================================
# Pushover Analysis
# ============================================================================

def _pushover_python(
    profile: SoilProfile,
    section: SteelSection | CustomPileSection,
    embedment: float,
    loads: BNWFLoadInput,
    options: BNWFOptions,
) -> BNWFResult:
    """Run pushover by incrementally scaling the load."""
    n_steps = loads.pushover_steps
    max_mult = loads.pushover_max_mult

    multipliers = np.linspace(0.0, max_mult, n_steps + 1)[1:]  # skip zero
    push_load: list[float] = []
    push_disp: list[float] = []

    last_result = None
    for mult in multipliers:
        step_loads = BNWFLoadInput(
            V_axial=loads.V_axial * mult,
            H_lateral=loads.H_lateral * mult,
            M_ground=loads.M_ground * mult,
            load_type="static",
        )
        result = _solve_bnwf_python(profile, section, embedment, step_loads, options)
        last_result = result

        if loads.load_type == "pushover_lateral":
            push_load.append(step_loads.H_lateral)
            push_disp.append(result.y_ground_lateral)
        else:
            push_load.append(step_loads.V_axial)
            push_disp.append(result.y_ground_axial)

        if not result.converged:
            break

    if last_result is None:
        # No steps completed — run static at full load
        last_result = _solve_bnwf_python(profile, section, embedment, loads, options)

    last_result.analysis_type = loads.load_type
    last_result.pushover_load = push_load
    last_result.pushover_disp = push_disp
    last_result.pushover_axis = "lateral" if "lateral" in loads.load_type else "axial"
    return last_result


# ============================================================================
# Stiffness Matrix Extraction
# ============================================================================

def _compute_head_stiffness(
    profile: SoilProfile,
    section: SteelSection | CustomPileSection,
    embedment: float,
    options: BNWFOptions,
) -> np.ndarray:
    """Compute 3x3 pile head stiffness matrix by applying unit loads.

    K_head relates [V_axial, H_lateral, M] to [u_axial, v_lateral, theta] at head.
    """
    unit_loads = [
        BNWFLoadInput(V_axial=1000.0, H_lateral=0.0, M_ground=0.0),
        BNWFLoadInput(V_axial=0.0, H_lateral=1000.0, M_ground=0.0),
        BNWFLoadInput(V_axial=0.0, H_lateral=0.0, M_ground=1000.0),
    ]

    # Use a quick solve with fewer iterations for stiffness extraction
    stiff_opts = BNWFOptions(
        n_elements=min(options.n_elements, 30),
        bending_axis=options.bending_axis,
        head_condition=options.head_condition,
        cyclic=options.cyclic,
        include_p_delta=False,  # Linear for stiffness extraction
        max_iter=50,
        tol=1e-4,
        solver="python",
        pile_type=options.pile_type,
        _skip_post=True,  # Prevent recursive K_head/buckling computation
    )

    flexibility = np.zeros((3, 3))
    load_mags = [1000.0, 1000.0, 1000.0]

    for col, (unit_load, mag) in enumerate(zip(unit_loads, load_mags)):
        result = _solve_bnwf_python(profile, section, embedment, unit_load, stiff_opts)
        # Flexibility matrix column: [u, v, theta] / load_magnitude
        flexibility[0, col] = result.y_ground_axial / mag
        flexibility[1, col] = result.y_ground_lateral / mag
        # theta at ground
        if len(result.depth_ft) > 1:
            dz_in = (result.depth_ft[1] - result.depth_ft[0]) * 12.0
            if dz_in > 0:
                theta_0 = (result.deflection_lateral_in[1] - result.deflection_lateral_in[0]) / dz_in
            else:
                theta_0 = 0.0
        else:
            theta_0 = 0.0
        flexibility[2, col] = theta_0 / mag

    # Symmetrize
    flexibility = 0.5 * (flexibility + flexibility.T)

    try:
        K_head = np.linalg.inv(flexibility)
    except np.linalg.LinAlgError:
        K_head = np.zeros((3, 3))

    return K_head


# ============================================================================
# Buckling Estimation
# ============================================================================

def _estimate_buckling(
    profile: SoilProfile,
    section: SteelSection | CustomPileSection,
    embedment: float,
    options: BNWFOptions,
) -> float | None:
    """Estimate critical buckling load via incremental P-delta analysis.

    Apply increasing axial compression, check when lateral stiffness vanishes.
    Uses a simplified approach: Euler buckling with effective length from
    depth of fixity.
    """
    if options.bending_axis == "strong":
        EI = section.EI_strong
    else:
        EI = section.EI_weak

    # Simplified: use depth of fixity as effective length
    # For a pile in soil, effective length ≈ 2 * depth_of_fixity for free head
    # Estimate depth of fixity from soil stiffness
    top_layer = profile.layer_at_depth(1.0) if profile.layers else None
    if top_layer is not None:
        k_h = top_layer.get_k_h()
        if top_layer.soil_type in (SoilType.SAND, SoilType.GRAVEL):
            T = (EI / (k_h * 12.0)) ** 0.2 if k_h > 0 else embedment * 12.0
            L_fix = 1.8 * T
        else:
            R = (EI / k_h) ** 0.25 if k_h > 0 else embedment * 12.0
            L_fix = 1.4 * R
    else:
        L_fix = embedment * 12.0

    # Effective length factor
    if options.head_condition == "fixed":
        K_eff = 1.0  # fixed-fixed approximate
    else:
        K_eff = 2.0  # free-fixed (cantilever)

    L_eff = K_eff * L_fix
    if L_eff <= 0:
        return None

    P_cr = math.pi**2 * EI / L_eff**2
    return P_cr


# ============================================================================
# Beam Element Stiffness Matrices
# ============================================================================

def _add_beam_stiffness(K: np.ndarray, ni: int, nj: int, EA: float, EI: float, L: float):
    """Add a 2-node beam-column element stiffness to the global matrix.

    DOFs per node: [u (axial), v (lateral), theta (rotation)]
    Local stiffness: 6x6 combining axial bar + Euler-Bernoulli beam.
    """
    dofs_i = [3 * ni, 3 * ni + 1, 3 * ni + 2]
    dofs_j = [3 * nj, 3 * nj + 1, 3 * nj + 2]
    dofs = dofs_i + dofs_j

    # Axial stiffness (bar)
    ka = EA / L

    # Bending stiffness (Euler-Bernoulli)
    kb = EI / L**3

    # 6x6 local stiffness matrix
    ke = np.zeros((6, 6))

    # Axial: DOFs 0, 3 (u_i, u_j)
    ke[0, 0] = ka
    ke[0, 3] = -ka
    ke[3, 0] = -ka
    ke[3, 3] = ka

    # Bending: DOFs 1,2,4,5 (v_i, theta_i, v_j, theta_j)
    ke[1, 1] = 12 * kb
    ke[1, 2] = 6 * kb * L
    ke[1, 4] = -12 * kb
    ke[1, 5] = 6 * kb * L

    ke[2, 1] = 6 * kb * L
    ke[2, 2] = 4 * kb * L**2
    ke[2, 4] = -6 * kb * L
    ke[2, 5] = 2 * kb * L**2

    ke[4, 1] = -12 * kb
    ke[4, 2] = -6 * kb * L
    ke[4, 4] = 12 * kb
    ke[4, 5] = -6 * kb * L

    ke[5, 1] = 6 * kb * L
    ke[5, 2] = 2 * kb * L**2
    ke[5, 4] = -6 * kb * L
    ke[5, 5] = 4 * kb * L**2

    # Assemble into global K
    for r in range(6):
        for c in range(6):
            K[dofs[r], dofs[c]] += ke[r, c]


def _add_geometric_stiffness(K: np.ndarray, ni: int, nj: int, N: float, L: float):
    """Add geometric stiffness matrix for P-delta effects.

    N: axial force in element (positive = compression).
    Only affects lateral DOFs (v, theta).
    """
    dofs_i = [3 * ni, 3 * ni + 1, 3 * ni + 2]
    dofs_j = [3 * nj, 3 * nj + 1, 3 * nj + 2]
    dofs = dofs_i + dofs_j

    # Linearized geometric stiffness for lateral DOFs
    # Standard formulation: N/L * [[6/5, L/10, -6/5, L/10], ...]
    c = N / L

    kg = np.zeros((6, 6))

    # Only lateral DOFs: indices 1,2,4,5 in local
    kg[1, 1] = 6.0 / 5.0 * c
    kg[1, 2] = L / 10.0 * c
    kg[1, 4] = -6.0 / 5.0 * c
    kg[1, 5] = L / 10.0 * c

    kg[2, 1] = L / 10.0 * c
    kg[2, 2] = 2.0 * L**2 / 15.0 * c
    kg[2, 4] = -L / 10.0 * c
    kg[2, 5] = -L**2 / 30.0 * c

    kg[4, 1] = -6.0 / 5.0 * c
    kg[4, 2] = -L / 10.0 * c
    kg[4, 4] = 6.0 / 5.0 * c
    kg[4, 5] = -L / 10.0 * c

    kg[5, 1] = L / 10.0 * c
    kg[5, 2] = -L**2 / 30.0 * c
    kg[5, 4] = -L / 10.0 * c
    kg[5, 5] = 2.0 * L**2 / 15.0 * c

    for r in range(6):
        for c_ in range(6):
            K[dofs[r], dofs[c_]] += kg[r, c_]
