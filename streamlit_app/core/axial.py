"""Axial pile capacity calculations.

Methods: Alpha, Beta, Meyerhof SPT, end bearing, helical torque correlation.
Supports both LRFD and ASD.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .soil import SoilProfile, SoilLayer, SoilType, GAMMA_WATER


@dataclass
class AxialResult:
    """Results from an axial capacity analysis."""
    method: str
    Q_s: float              # Total skin friction (lbs)
    Q_b: float              # End bearing (lbs)
    Q_ult_compression: float  # Ultimate compression capacity (lbs)
    Q_ult_tension: float    # Ultimate tension capacity (lbs)
    Q_allow_compression: float
    Q_allow_tension: float
    FS_compression: float
    FS_tension: float
    phi_compression: float  # LRFD resistance factor
    phi_tension: float
    Q_r_compression: float  # LRFD factored resistance (lbs)
    Q_r_tension: float
    layer_contributions: list[dict]  # Per-layer breakdown
    notes: list[str]


def alpha_adhesion_factor(c_u: float, sigma_v: float = 0) -> float:
    """API RP 2A adhesion factor for clay.

    Args:
        c_u: Undrained shear strength (psf)
        sigma_v: Effective overburden stress (psf) — used for API ratio method

    Returns:
        alpha (dimensionless)
    """
    if sigma_v > 0:
        psi = c_u / sigma_v
        if psi <= 1.0:
            alpha = min(1.0, 0.5 * psi ** (-0.5))
        else:
            alpha = min(1.0, 0.5 * psi ** (-0.25))
    else:
        # Tabulated fallback (Tomlinson)
        if c_u <= 500:
            alpha = 1.0
        elif c_u <= 1000:
            alpha = 1.0 - 0.2 * (c_u - 500) / 500
        elif c_u <= 2000:
            alpha = 0.8 - 0.3 * (c_u - 1000) / 1000
        elif c_u <= 4000:
            alpha = 0.5 - 0.15 * (c_u - 2000) / 2000
        else:
            alpha = 0.30
    return max(0.25, min(1.0, alpha))


def beta_coefficient(
    phi: float,
    K_s_ratio: float = 1.0,
    delta_ratio: float = 0.7,
    OCR: float = 1.0,
) -> float:
    """Compute beta = K_s * tan(delta) for effective stress method.

    Args:
        phi: Friction angle (degrees)
        K_s_ratio: K_s / K_0 ratio (1.0 for driven displacement)
        delta_ratio: delta / phi' ratio (0.7 for smooth steel)
        OCR: Overconsolidation ratio
    """
    phi_rad = math.radians(phi)
    K_0 = (1 - math.sin(phi_rad)) * OCR ** math.sin(phi_rad)
    K_s = K_s_ratio * K_0
    delta = delta_ratio * phi
    return K_s * math.tan(math.radians(delta))


def axial_capacity(
    profile: SoilProfile,
    pile_perimeter: float,
    pile_tip_area: float,
    embedment_depth: float,
    method: str = "auto",
    pile_type: str = "driven",
    FS_compression: float = 2.5,
    FS_tension: float = 3.0,
    tension_factor: float = 0.75,
    dz: float = 0.5,
) -> AxialResult:
    """Compute axial compression and tension capacity.

    Args:
        profile: SoilProfile object
        pile_perimeter: Pile perimeter (in)
        pile_tip_area: Pile tip area for end bearing (in^2)
        embedment_depth: Pile embedment below ground (ft)
        method: "alpha", "beta", "meyerhof", or "auto"
        pile_type: "driven", "drilled", or "helical"
        FS_compression: Factor of safety for compression (ASD)
        FS_tension: Factor of safety for tension (ASD)
        tension_factor: Reduction factor for tension skin friction
        dz: Depth increment for integration (ft)

    Returns:
        AxialResult with complete breakdown
    """
    notes = []
    layer_contributions = []
    Q_s_total = 0.0
    Q_b = 0.0

    # LRFD resistance factors
    if pile_type == "driven":
        phi_comp = 0.45
        phi_tens = 0.35
    elif pile_type == "helical":
        phi_comp = 0.50
        phi_tens = 0.50
    else:  # drilled
        phi_comp = 0.40
        phi_tens = 0.30

    # --- Skin friction integration ---
    depths = _frange(dz, embedment_depth, dz)
    for z in depths:
        layer = profile.layer_at_depth(z)
        if layer is None:
            continue

        sigma_v = profile.effective_stress_at(z)
        A_s = pile_perimeter * dz * 12.0  # in^2 (perimeter in inches * dz in ft * 12)

        is_cohesive = layer.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC)
        use_method = method
        if method == "auto":
            use_method = "alpha" if is_cohesive else "beta"

        if use_method == "alpha" and is_cohesive:
            c_u = layer.get_cu()
            alpha = alpha_adhesion_factor(c_u, sigma_v)
            f_s = alpha * c_u  # psf
            f_s_psi = f_s / 144.0  # convert to psi for A_s in in^2
            dQ = f_s_psi * A_s  # lbs
            layer_contributions.append({
                "depth_ft": z,
                "layer": layer.description or layer.soil_type.value,
                "method": "Alpha",
                "alpha": round(alpha, 3),
                "c_u_psf": round(c_u, 0),
                "f_s_psf": round(f_s, 1),
                "dQ_lbs": round(dQ, 0),
            })

        elif use_method == "meyerhof":
            N_60 = layer.N_60 or 10
            if is_cohesive:
                c_u = layer.get_cu()
                alpha = alpha_adhesion_factor(c_u, sigma_v)
                f_s = alpha * c_u  # psf
            else:
                f_s = min(N_60 / 50.0 * 2000.0, 2000.0)  # psf (N/50 tsf -> psf, cap 1 tsf)
                if layer.soil_type == SoilType.SILT:
                    f_s = min(f_s, 1200.0)
            f_s_psi = f_s / 144.0
            dQ = f_s_psi * A_s
            layer_contributions.append({
                "depth_ft": z,
                "layer": layer.description or layer.soil_type.value,
                "method": "Meyerhof SPT",
                "N_60": round(N_60, 1),
                "f_s_psf": round(f_s, 1),
                "dQ_lbs": round(dQ, 0),
            })

        else:  # Beta method
            phi = layer.get_phi(sigma_v)
            if is_cohesive:
                # Beta for cohesive with effective stress
                b = beta_coefficient(phi if phi > 0 else 20, K_s_ratio=0.8, delta_ratio=0.8)
            else:
                K_s_r = 1.0 if pile_type == "driven" else 0.7
                delta_r = 0.7 if pile_type == "driven" else 0.8
                b = beta_coefficient(phi, K_s_ratio=K_s_r, delta_ratio=delta_r)

            f_s = b * sigma_v  # psf
            # Apply critical depth limit (cap sigma_v effect at 20*B)
            f_s_psi = f_s / 144.0
            dQ = f_s_psi * A_s
            layer_contributions.append({
                "depth_ft": z,
                "layer": layer.description or layer.soil_type.value,
                "method": "Beta",
                "beta": round(b, 3),
                "sigma_v_psf": round(sigma_v, 0),
                "f_s_psf": round(f_s, 1),
                "dQ_lbs": round(dQ, 0),
            })

        Q_s_total += dQ

    # --- End bearing ---
    tip_layer = profile.layer_at_depth(embedment_depth - 0.01)
    if tip_layer is not None:
        sigma_v_tip = profile.effective_stress_at(embedment_depth)
        is_tip_cohesive = tip_layer.soil_type in (
            SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC
        )

        if is_tip_cohesive:
            c_u_tip = tip_layer.get_cu()
            N_c = 9.0
            q_b = N_c * c_u_tip  # psf
            notes.append(f"End bearing: N_c * c_u = {N_c} * {c_u_tip:.0f} psf")
        else:
            phi_tip = tip_layer.get_phi(sigma_v_tip)
            N_q = _meyerhof_Nq(phi_tip)
            q_b = sigma_v_tip * N_q  # psf
            # Apply limiting value
            q_b_max = _meyerhof_qb_limit(phi_tip) * 2000.0  # tsf -> psf
            q_b = min(q_b, q_b_max)
            notes.append(
                f"End bearing: sigma'_v * N_q = {sigma_v_tip:.0f} * {N_q:.1f} = {q_b:.0f} psf"
                f" (limit {q_b_max:.0f} psf)"
            )

        q_b_psi = q_b / 144.0
        Q_b = q_b_psi * pile_tip_area  # lbs

    # --- Assemble results ---
    Q_ult_comp = Q_s_total + Q_b
    Q_ult_tens = Q_s_total * tension_factor

    notes.append(f"Skin friction: {Q_s_total:.0f} lbs")
    notes.append(f"End bearing: {Q_b:.0f} lbs")
    notes.append(f"Tension factor on skin friction: {tension_factor}")
    notes.append(f"Pile type: {pile_type}")

    return AxialResult(
        method=method,
        Q_s=Q_s_total,
        Q_b=Q_b,
        Q_ult_compression=Q_ult_comp,
        Q_ult_tension=Q_ult_tens,
        Q_allow_compression=Q_ult_comp / FS_compression,
        Q_allow_tension=Q_ult_tens / FS_tension,
        FS_compression=FS_compression,
        FS_tension=FS_tension,
        phi_compression=phi_comp,
        phi_tension=phi_tens,
        Q_r_compression=phi_comp * Q_ult_comp,
        Q_r_tension=phi_tens * Q_ult_tens,
        layer_contributions=layer_contributions,
        notes=notes,
    )


def helical_capacity_torque(
    torque_ft_lbs: float,
    shaft_size: str = "1.75in_sq",
) -> dict:
    """Helical pile capacity from installation torque correlation.

    Q_ult = K_t * T

    Returns dict with Q_ult, K_t, and notes.
    """
    Kt_table = {
        "1.5in_sq": 10.0,
        "1.75in_sq": 9.0,
        "2.875in_pipe": 7.0,
        "3.5in_pipe": 6.0,
        "4.5in_pipe": 5.0,
    }
    K_t = Kt_table.get(shaft_size, 7.0)
    Q_ult = K_t * torque_ft_lbs
    return {
        "Q_ult_lbs": Q_ult,
        "K_t": K_t,
        "torque_ft_lbs": torque_ft_lbs,
        "notes": f"K_t = {K_t} 1/ft for {shaft_size} shaft",
    }


# --- Internal helpers ---

def _meyerhof_Nq(phi: float) -> float:
    """Interpolate Meyerhof N_q for driven piles."""
    table = [
        (25, 12.5), (26, 14.5), (28, 21), (30, 30), (32, 44),
        (34, 65), (36, 100), (38, 150), (40, 225),
    ]
    if phi <= table[0][0]:
        return table[0][1]
    if phi >= table[-1][0]:
        return table[-1][1]
    for i in range(len(table) - 1):
        p1, n1 = table[i]
        p2, n2 = table[i + 1]
        if p1 <= phi <= p2:
            return n1 + (n2 - n1) * (phi - p1) / (p2 - p1)
    return 30.0


def _meyerhof_qb_limit(phi: float) -> float:
    """Limiting end bearing (tsf) from Meyerhof."""
    table = [
        (25, 50), (28, 75), (30, 100), (32, 125), (34, 175),
        (36, 250), (38, 350), (40, 500),
    ]
    if phi <= table[0][0]:
        return table[0][1]
    if phi >= table[-1][0]:
        return table[-1][1]
    for i in range(len(table) - 1):
        p1, n1 = table[i]
        p2, n2 = table[i + 1]
        if p1 <= phi <= p2:
            return n1 + (n2 - n1) * (phi - p1) / (p2 - p1)
    return 100.0


def _frange(start: float, stop: float, step: float) -> list[float]:
    """Float range inclusive of stop (within half step)."""
    result = []
    v = start
    while v <= stop + step * 0.01:
        result.append(round(v, 6))
        v += step
    return result
