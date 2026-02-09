"""OpenSeesPy-based BNWF solver.

Uses PySimple1, TzSimple1, QzSimple1, beam-column elements, fiber sections,
eigenvalue analysis, and pushover capabilities.

This module is imported conditionally — only when openseespy is available.
"""

from __future__ import annotations

import math
from typing import Union

import numpy as np

from .soil import SoilProfile, SoilType
from .sections import SteelSection, CustomPileSection
from .lateral import generate_py_curve, PYCurve
from .tz_qz import generate_tz_curve, generate_qz_curve, TZCurve, QZCurve
from .bnwf import BNWFLoadInput, BNWFOptions, BNWFResult

import openseespy.opensees as ops


def _solve_bnwf_opensees(
    profile: SoilProfile,
    section: Union[SteelSection, CustomPileSection],
    embedment: float,
    loads: BNWFLoadInput,
    options: BNWFOptions,
) -> BNWFResult:
    """Build and solve a full OpenSeesPy BNWF model."""
    notes: list[str] = []
    n_elem = options.n_elements
    n_nodes = n_elem + 1
    L_in = embedment * 12.0
    dz = L_in / n_elem

    if options.bending_axis == "strong":
        EI = section.EI_strong
    else:
        EI = section.EI_weak
    E = 29000.0e3  # psi
    A = section.area
    I = EI / E
    pile_width = section.depth if options.bending_axis == "strong" else section.width
    pile_perimeter = section.perimeter

    # ---- Build model ----
    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    # Nodes: pile nodes
    for i in range(n_nodes):
        z_in = i * dz
        ops.node(i + 1, 0.0, -z_in)

    # Anchor nodes for springs (fixed)
    for i in range(n_nodes):
        z_in = i * dz
        # p-y anchor
        py_anchor = 1000 + i + 1
        ops.node(py_anchor, 0.0, -z_in)
        ops.fix(py_anchor, 1, 1, 1)
        # t-z anchor
        tz_anchor = 2000 + i + 1
        ops.node(tz_anchor, 0.0, -z_in)
        ops.fix(tz_anchor, 1, 1, 1)

    # q-z anchor at tip
    ops.node(3001, 0.0, -L_in)
    ops.fix(3001, 1, 1, 1)

    # Head boundary condition
    if options.head_condition == "fixed":
        ops.fix(1, 0, 0, 1)  # fix rotation only

    # ---- Materials ----
    mat_tag = 0

    # Steel material for fiber section
    steel_tag = 1
    if options.use_fiber_section and isinstance(section, SteelSection):
        fy_psi = section.fy * 1000.0  # ksi -> psi
        b_hard = 0.01  # strain hardening ratio
        ops.uniaxialMaterial('Steel02', steel_tag, fy_psi, E, b_hard,
                             20.0, 0.925, 0.15)
        notes.append("Steel02 material with Fy={:.0f} psi, E={:.0f} psi".format(fy_psi, E))

    # p-y, t-z spring materials and elements
    py_curves_all: list[PYCurve | None] = []
    tz_curves_all: list[TZCurve | None] = []

    for i in range(n_nodes):
        z_ft = i * dz / 12.0
        layer = profile.layer_at_depth(z_ft)

        if layer is None or z_ft <= 0.001:
            py_curves_all.append(None)
            tz_curves_all.append(None)
            continue

        sigma_v = profile.effective_stress_at(z_ft)
        trib = dz if (0 < i < n_nodes - 1) else dz / 2.0
        is_cohesive = layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC)
        soil_type_ops = 1 if is_cohesive else 2

        # p-y spring
        py = generate_py_curve(z_ft, layer, sigma_v, pile_width, options.cyclic)
        py_curves_all.append(py)
        p_ult_trib = py.p_ult * trib
        if p_ult_trib > 0 and len(py.y) > 2:
            y_50 = float(np.interp(0.5 * py.p_ult, py.p, py.y))
            y_50 = max(y_50, 0.001)
        else:
            y_50 = 0.01
            p_ult_trib = max(p_ult_trib, 0.01)

        mat_tag += 1
        py_mat = mat_tag
        ops.uniaxialMaterial('PySimple1', py_mat, soil_type_ops,
                             p_ult_trib, y_50, 0.0, 0.0)

        # t-z spring
        tz = generate_tz_curve(z_ft, layer, sigma_v, pile_perimeter,
                               pile_width, options.pile_type)
        tz_curves_all.append(tz)
        t_ult_trib = tz.t_ult * trib
        if t_ult_trib > 0 and len(tz.z) > 2:
            z_50 = float(np.interp(0.5 * tz.t_ult, tz.t, tz.z))
            z_50 = max(z_50, 0.0001)
        else:
            z_50 = 0.01
            t_ult_trib = max(t_ult_trib, 0.01)

        mat_tag += 1
        tz_mat = mat_tag
        ops.uniaxialMaterial('TzSimple1', tz_mat, soil_type_ops,
                             t_ult_trib, z_50, 0.0)

        # Zero-length spring elements
        # p-y: DOF 1 (horizontal)
        py_ele = 5000 + i
        ops.element('zeroLength', py_ele, 1000 + i + 1, i + 1,
                     '-mat', py_mat, '-dir', 1)

        # t-z: DOF 2 (vertical)
        tz_ele = 6000 + i
        ops.element('zeroLength', tz_ele, 2000 + i + 1, i + 1,
                     '-mat', tz_mat, '-dir', 2)

    # q-z spring at tip
    tip_layer = profile.layer_at_depth(embedment - 0.01)
    qz_curve: QZCurve | None = None
    if tip_layer is not None:
        sigma_v_tip = profile.effective_stress_at(embedment)
        qz_curve = generate_qz_curve(tip_layer, sigma_v_tip, section.tip_area,
                                      pile_width)
        if qz_curve.q_ult > 0 and len(qz_curve.z) > 2:
            q_z50 = float(np.interp(0.5 * qz_curve.q_ult, qz_curve.q, qz_curve.z))
            q_z50 = max(q_z50, 0.001)
        else:
            q_z50 = 0.01

        is_tip_cohesive = tip_layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC)
        mat_tag += 1
        qz_mat = mat_tag
        ops.uniaxialMaterial('QzSimple1', qz_mat,
                             1 if is_tip_cohesive else 2,
                             max(qz_curve.q_ult, 0.01), q_z50, 0.0, 0.0)
        ops.element('zeroLength', 7001, 3001, n_nodes,
                     '-mat', qz_mat, '-dir', 2)

    # ---- Geometric transformation ----
    if options.include_p_delta:
        ops.geomTransf('PDelta', 1)
    else:
        ops.geomTransf('Linear', 1)

    # ---- Pile beam elements ----
    if options.use_fiber_section and isinstance(section, SteelSection):
        # Define fiber section
        sec_tag = 1
        ops.section('Fiber', sec_tag)
        d = section.depth
        bf = section.width
        tf = section.tf
        tw = section.tw
        n_flange_fibers = 10
        n_web_fibers = 20
        # Bottom flange
        ops.patch('rect', steel_tag, n_flange_fibers, 1,
                  -d / 2, -bf / 2, -d / 2 + tf, bf / 2)
        # Top flange
        ops.patch('rect', steel_tag, n_flange_fibers, 1,
                  d / 2 - tf, -bf / 2, d / 2, bf / 2)
        # Web
        ops.patch('rect', steel_tag, 1, n_web_fibers,
                  -d / 2 + tf, -tw / 2, d / 2 - tf, tw / 2)

        # Integration points
        n_ip = 5
        ops.beamIntegration('Legendre', 1, sec_tag, n_ip)

        for e in range(n_elem):
            ops.element('dispBeamColumn', e + 1, e + 1, e + 2, 1, 1)
        notes.append(f"Fiber section with {n_flange_fibers}+{n_web_fibers} fibers, Steel02")
    else:
        for e in range(n_elem):
            ops.element('elasticBeamColumn', e + 1, e + 1, e + 2, A, E, I, 1)
        notes.append("Elastic beam-column elements")

    # ---- Mass for eigenvalue analysis ----
    if options.run_eigenvalue:
        mass_per_in = section.weight / 12.0 / 386.4  # plf -> lb/in -> mass (lb·s²/in)
        for i in range(n_nodes):
            m = mass_per_in * (dz if 0 < i < n_nodes - 1 else dz / 2.0)
            if m > 0:
                ops.mass(i + 1, m, m, 0.0)

    # ---- Load pattern ----
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    M_in_lbs = loads.M_ground * 12.0  # ft-lbs -> in-lbs
    ops.load(1, loads.H_lateral, -loads.V_axial, M_in_lbs)

    # ---- Analysis ----
    is_pushover = loads.load_type.startswith("pushover")
    n_steps = loads.pushover_steps if is_pushover else 10

    ops.constraints('Transformation')
    ops.numberer('RCM')
    ops.system('BandGeneral')
    ops.test('NormDispIncr', 1e-6, options.max_iter, 0)
    ops.algorithm('Newton')
    ops.integrator('LoadControl', 1.0 / n_steps)
    ops.analysis('Static')

    push_load: list[float] = []
    push_disp: list[float] = []
    converged = True

    for step in range(n_steps):
        ok = ops.analyze(1)
        if ok != 0:
            ops.algorithm('ModifiedNewton')
            ok = ops.analyze(1)
        if ok != 0:
            ops.algorithm('KrylovNewton')
            ok = ops.analyze(1)
        if ok != 0:
            converged = False
            notes.append(f"Analysis failed at step {step + 1}/{n_steps}")
            break

        if is_pushover:
            frac = (step + 1) / n_steps
            if "lateral" in loads.load_type:
                push_load.append(loads.H_lateral * frac)
                push_disp.append(float(ops.nodeDisp(1, 1)))
            else:
                push_load.append(loads.V_axial * frac)
                push_disp.append(float(ops.nodeDisp(1, 2)))

    # ---- Extract results ----
    depth_ft = np.array([i * dz / 12.0 for i in range(n_nodes)])
    v_lateral = np.array([ops.nodeDisp(i + 1, 1) for i in range(n_nodes)])
    u_axial = np.array([ops.nodeDisp(i + 1, 2) for i in range(n_nodes)])

    # Moments and shears from element forces
    moment_in_lbs = np.zeros(n_nodes)
    shear_arr = np.zeros(n_nodes)
    axial_arr = np.zeros(n_nodes)

    for e in range(n_elem):
        forces = ops.eleForce(e + 1)  # [N1, V1, M1, N2, V2, M2]
        if len(forces) >= 6:
            # Average moment at element midpoint, assign to nodes
            moment_in_lbs[e] += forces[2]
            moment_in_lbs[e + 1] += -forces[5]  # sign convention
            shear_arr[e] = forces[1]
            axial_arr[e] = -forces[0]  # compression positive

    # Smooth moment by averaging overlaps
    for i in range(1, n_nodes - 1):
        moment_in_lbs[i] /= 2.0 if i > 0 and i < n_nodes - 1 else 1.0

    moment_ft_lbs = moment_in_lbs / 12.0
    shear_arr[0] = loads.H_lateral
    axial_arr[0] = loads.V_axial

    # Soil reactions
    soil_p = np.zeros(n_nodes)
    soil_t = np.zeros(n_nodes)
    for i in range(n_nodes):
        py = py_curves_all[i] if i < len(py_curves_all) else None
        if py is not None:
            v_abs = abs(v_lateral[i])
            soil_p[i] = float(np.interp(v_abs, py.y, py.p)) * np.sign(v_lateral[i])
        tz = tz_curves_all[i] if i < len(tz_curves_all) else None
        if tz is not None:
            u_abs = abs(u_axial[i])
            soil_t[i] = float(np.interp(u_abs, tz.z, tz.t)) * np.sign(u_axial[i])

    q_tip = 0.0
    if qz_curve is not None:
        u_tip = abs(u_axial[-1])
        q_tip = float(np.interp(u_tip, qz_curve.z, qz_curve.q))

    # Key scalars
    y_ground_lateral = float(v_lateral[0])
    y_ground_axial = float(u_axial[0])
    M_max_idx = int(np.argmax(np.abs(moment_ft_lbs)))
    M_max = float(moment_ft_lbs[M_max_idx])
    depth_M_max = float(depth_ft[M_max_idx])

    # ---- Eigenvalue analysis ----
    eigenvalues = None
    frequencies = None
    if options.run_eigenvalue:
        try:
            eigs = ops.eigen('-genBandArpack', options.n_modes)
            eigenvalues = [float(ev) for ev in eigs]
            frequencies = [math.sqrt(abs(ev)) / (2.0 * math.pi) for ev in eigs]
            notes.append(f"Eigenvalue analysis: {len(eigs)} modes computed")
        except Exception as e:
            notes.append(f"Eigenvalue analysis failed: {e}")

    # ---- Stiffness matrix (simplified) ----
    K_head = np.zeros((3, 3))
    notes.append(f"Solver: OpenSeesPy ({n_elem} elements)")

    # Display curves
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

    # Buckling estimate
    P_crit = None
    if options.include_p_delta:
        from .bnwf import _estimate_buckling
        P_crit = _estimate_buckling(profile, section, embedment, options)

    analysis_type = loads.load_type if is_pushover else "static"

    ops.wipe()

    return BNWFResult(
        solver_used="opensees",
        analysis_type=analysis_type,
        converged=converged,
        iterations=n_steps,
        notes=notes,
        depth_ft=depth_ft,
        deflection_lateral_in=v_lateral,
        deflection_axial_in=u_axial,
        moment_ft_lbs=moment_ft_lbs,
        shear_lbs=shear_arr,
        axial_force_lbs=axial_arr,
        soil_reaction_p_lb_in=soil_p,
        soil_reaction_t_lb_in=soil_t,
        soil_reaction_q_lbs=q_tip,
        y_ground_lateral=y_ground_lateral,
        y_ground_axial=y_ground_axial,
        M_max=M_max,
        depth_M_max=depth_M_max,
        K_head=K_head,
        pushover_load=push_load if is_pushover else None,
        pushover_disp=push_disp if is_pushover else None,
        pushover_axis=("lateral" if "lateral" in loads.load_type else "axial") if is_pushover else None,
        py_curves=disp_py,
        tz_curves=disp_tz,
        qz_curve=qz_curve,
        eigenvalues=eigenvalues,
        frequencies_hz=frequencies,
        P_critical=P_crit,
    )
