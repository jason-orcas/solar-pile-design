"""AISC 360 structural capacity checks for steel pile sections."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class AISCUnityResult:
    """Results from AISC 360 H1-1 interaction check."""

    # Demands
    P_u: float               # Factored axial compression (lbs)
    M_ux: float              # Factored strong-axis moment (kip-in)
    M_uy: float              # Factored weak-axis moment (kip-in)

    # Capacities
    P_n: float               # Nominal compression capacity (lbs)
    phi_c_Pn: float          # phi_c * P_n (lbs)
    M_nx: float              # Nominal strong-axis moment capacity (kip-in)
    M_ny: float              # Nominal weak-axis moment capacity (kip-in)
    phi_b_Mnx: float         # phi_b * M_nx (kip-in)
    phi_b_Mny: float         # phi_b * M_ny (kip-in)

    # Unity check
    axial_ratio: float       # P_u / (phi_c * P_n)
    equation_used: str       # "H1-1a" or "H1-1b"
    unity_ratio: float       # Governing interaction value
    passes: bool             # unity_ratio <= 1.0

    # Intermediate values
    K: float                 # Effective length factor
    L_b_ft: float            # Unbraced length (ft)
    r_x: float               # Radius of gyration, strong axis (in)
    r_y: float               # Radius of gyration, weak axis (in)
    KL_r: float              # Governing slenderness ratio
    F_cr_ksi: float          # Critical buckling stress (ksi)
    D_f_ft: float            # Depth of fixity used (ft)

    notes: list[str] = field(default_factory=list)


def aisc_h1_check(
    section,  # SteelSection
    P_u_lbs: float,
    M_ux_kip_in: float,
    M_uy_kip_in: float = 0.0,
    L_b_ft: float = 10.0,
    K: float = 2.1,
    phi_c: float = 0.90,
    phi_b: float = 0.90,
    D_f_ft: float = 0.0,
) -> AISCUnityResult:
    """AISC 360 H1-1 combined axial + bending interaction check.

    Args:
        section: SteelSection with area, Ix, Iy, Zx, Zy, fy properties.
        P_u_lbs: Factored axial compression load (lbs, positive = compression).
        M_ux_kip_in: Factored strong-axis moment (kip-in).
        M_uy_kip_in: Factored weak-axis moment (kip-in).
        L_b_ft: Unbraced length (ft) = above_grade + D_f.
        K: Effective length factor (2.1 for cantilever with partial fixity).
        phi_c: LRFD resistance factor for compression (0.90).
        phi_b: LRFD resistance factor for bending (0.90).
        D_f_ft: Depth of fixity (ft), for reporting only.

    Returns:
        AISCUnityResult with unity ratio and pass/fail.
    """
    E_ksi = 29000.0
    F_y = section.fy  # ksi
    A_g = section.area  # in^2

    # Radii of gyration
    r_x = math.sqrt(section.Ix / A_g) if A_g > 0 else 1.0
    r_y = math.sqrt(section.Iy / A_g) if A_g > 0 else 1.0

    L_b_in = L_b_ft * 12.0
    KL_r_x = K * L_b_in / r_x if r_x > 0 else 999.0
    KL_r_y = K * L_b_in / r_y if r_y > 0 else 999.0
    KL_r = max(KL_r_x, KL_r_y)  # governing slenderness

    notes: list[str] = []

    # --- AISC Chapter E: Compression capacity ---
    F_e = math.pi**2 * E_ksi / KL_r**2 if KL_r > 0 else 1e6

    if F_y / F_e <= 2.25:
        F_cr = (0.658 ** (F_y / F_e)) * F_y  # inelastic buckling
    else:
        F_cr = 0.877 * F_e  # elastic buckling

    P_n_kips = F_cr * A_g  # kips
    P_n_lbs = P_n_kips * 1000.0
    phi_c_Pn = phi_c * P_n_lbs

    # --- AISC Chapter F: Flexural capacity (compact W-shapes) ---
    M_nx = section.Zx * F_y  # kip-in (plastic moment, strong)
    M_ny = section.Zy * F_y  # kip-in (plastic moment, weak)
    phi_b_Mnx = phi_b * M_nx
    phi_b_Mny = phi_b * M_ny

    # --- AISC Chapter H: Interaction ---
    P_u_abs = abs(P_u_lbs)
    axial_ratio = P_u_abs / phi_c_Pn if phi_c_Pn > 0 else 0.0

    M_ux_abs = abs(M_ux_kip_in)
    M_uy_abs = abs(M_uy_kip_in)

    moment_x_ratio = M_ux_abs / phi_b_Mnx if phi_b_Mnx > 0 else 0.0
    moment_y_ratio = M_uy_abs / phi_b_Mny if phi_b_Mny > 0 else 0.0

    if axial_ratio >= 0.2:
        # H1-1a
        unity = axial_ratio + (8.0 / 9.0) * (moment_x_ratio + moment_y_ratio)
        eq_used = "H1-1a"
    else:
        # H1-1b
        unity = (axial_ratio / 2.0) + (moment_x_ratio + moment_y_ratio)
        eq_used = "H1-1b"

    passes = unity <= 1.0

    if KL_r > 200:
        notes.append(f"KL/r = {KL_r:.0f} exceeds AISC recommended limit of 200")
    if not passes:
        notes.append(f"FAIL: Unity ratio {unity:.3f} > 1.0")

    return AISCUnityResult(
        P_u=P_u_abs,
        M_ux=M_ux_abs,
        M_uy=M_uy_abs,
        P_n=P_n_lbs,
        phi_c_Pn=phi_c_Pn,
        M_nx=M_nx,
        M_ny=M_ny,
        phi_b_Mnx=phi_b_Mnx,
        phi_b_Mny=phi_b_Mny,
        axial_ratio=round(axial_ratio, 4),
        equation_used=eq_used,
        unity_ratio=round(unity, 4),
        passes=passes,
        K=K,
        L_b_ft=L_b_ft,
        r_x=round(r_x, 3),
        r_y=round(r_y, 3),
        KL_r=round(KL_r, 1),
        F_cr_ksi=round(F_cr, 2),
        D_f_ft=D_f_ft,
        notes=notes,
    )
