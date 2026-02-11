"""Installation QC: dynamic formulas for driven piles, torque correlation for helical."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class DrivenPileQCResult:
    """Result from a single driven pile dynamic formula."""

    method: str
    R_u_lbs: float        # Ultimate resistance (lbs)
    R_u_kips: float       # Same in kips
    R_allow_lbs: float    # Allowable = R_u / FS
    FS: float
    W_r_lbs: float        # Ram weight
    h_ft: float           # Drop height
    s_in: float           # Set per blow
    E_h_ft_lbs: float     # Hammer energy
    notes: list[str] = field(default_factory=list)


@dataclass
class HelicalQCResult:
    """Result from helical pile torque correlation."""

    Q_ult_lbs: float
    K_t: float
    torque_ft_lbs: float
    Q_allow_lbs: float
    FS: float
    shaft_size: str
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Driven pile dynamic formulas
# ---------------------------------------------------------------------------

def enr_formula(
    W_r_lbs: float,
    h_ft: float,
    s_in: float,
    c: float = 0.1,
    FS: float = 6.0,
) -> DrivenPileQCResult:
    """Engineering News Record (ENR) dynamic formula.

    R_u = (W_r * h * 12) / (s + c)

    Args:
        W_r_lbs: Ram weight (lbs).
        h_ft: Drop height (ft).
        s_in: Set per blow (inches).
        c: Elastic compression constant (in), default 0.1 for drop hammers.
        FS: Factor of safety (traditionally 6.0 for ENR).
    """
    E_h = W_r_lbs * h_ft  # ft-lbs
    denom = s_in + c
    R_u = (E_h * 12.0) / denom if denom > 0 else 0.0
    return DrivenPileQCResult(
        method="ENR",
        R_u_lbs=R_u,
        R_u_kips=R_u / 1000.0,
        R_allow_lbs=R_u / FS,
        FS=FS,
        W_r_lbs=W_r_lbs,
        h_ft=h_ft,
        s_in=s_in,
        E_h_ft_lbs=E_h,
        notes=[f"ENR with c={c} in, FS={FS}"],
    )


def gates_formula(
    W_r_lbs: float,
    h_ft: float,
    s_in: float,
    FS: float = 3.0,
) -> DrivenPileQCResult:
    """Gates (1957) dynamic formula.

    R_u (lbs) = 27 * sqrt(E_h) * (1 - log10(s))

    Args:
        W_r_lbs: Ram weight (lbs).
        h_ft: Drop height (ft).
        s_in: Set per blow (inches).
        FS: Factor of safety (typically 3.0).
    """
    E_h = W_r_lbs * h_ft  # ft-lbs
    safe_s = max(s_in, 0.001)
    R_u = 27.0 * math.sqrt(E_h) * (1.0 - math.log10(safe_s))
    R_u = max(R_u, 0.0)
    return DrivenPileQCResult(
        method="Gates",
        R_u_lbs=R_u,
        R_u_kips=R_u / 1000.0,
        R_allow_lbs=R_u / FS,
        FS=FS,
        W_r_lbs=W_r_lbs,
        h_ft=h_ft,
        s_in=s_in,
        E_h_ft_lbs=E_h,
        notes=[f"Gates formula, FS={FS}"],
    )


def fhwa_modified_gates(
    W_r_lbs: float,
    h_ft: float,
    s_in: float,
    FS: float = 3.0,
) -> DrivenPileQCResult:
    """FHWA Modified Gates dynamic formula (GEC-12).

    R_u (kips) = 1.75 * sqrt(E_d) * log10(10 * N_b) - 100

    Args:
        W_r_lbs: Ram weight (lbs).
        h_ft: Drop height (ft).
        s_in: Set per blow (inches).
        FS: Factor of safety (typically 3.0).
    """
    E_d_kip_ft = (W_r_lbs / 1000.0) * h_ft
    N_b = 1.0 / s_in if s_in > 0 else 1000.0  # blows per inch
    R_u_kips = 1.75 * math.sqrt(E_d_kip_ft) * math.log10(10.0 * N_b) - 100.0
    R_u_kips = max(R_u_kips, 0.0)
    R_u_lbs = R_u_kips * 1000.0
    return DrivenPileQCResult(
        method="FHWA Modified Gates",
        R_u_lbs=R_u_lbs,
        R_u_kips=R_u_kips,
        R_allow_lbs=R_u_lbs / FS,
        FS=FS,
        W_r_lbs=W_r_lbs,
        h_ft=h_ft,
        s_in=s_in,
        E_h_ft_lbs=W_r_lbs * h_ft,
        notes=[
            f"FHWA Modified Gates, E_d={E_d_kip_ft:.2f} kip-ft, "
            f"N_b={N_b:.1f} bpi, FS={FS}",
        ],
    )


# ---------------------------------------------------------------------------
# Helical pile torque correlation
# ---------------------------------------------------------------------------

# K_t values by shaft size (1/ft)
HELICAL_KT: dict[str, float] = {
    "1.5in_sq": 10.0,
    "1.75in_sq": 9.0,
    "2.875in_pipe": 7.0,
    "3.5in_pipe": 6.0,
    "4.5in_pipe": 5.0,
}


def helical_torque_check(
    torque_ft_lbs: float,
    shaft_size: str = "1.75in_sq",
    FS: float = 2.0,
) -> HelicalQCResult:
    """Helical pile capacity from installation torque.

    Q_ult = K_t * T

    Args:
        torque_ft_lbs: Installation torque (ft-lbs).
        shaft_size: Shaft designation (key into HELICAL_KT).
        FS: Factor of safety.
    """
    K_t = HELICAL_KT.get(shaft_size, 9.0)
    Q_ult = K_t * torque_ft_lbs
    return HelicalQCResult(
        Q_ult_lbs=Q_ult,
        K_t=K_t,
        torque_ft_lbs=torque_ft_lbs,
        Q_allow_lbs=Q_ult / FS,
        FS=FS,
        shaft_size=shaft_size,
        notes=[f"K_t={K_t} 1/ft for {shaft_size}, FS={FS}"],
    )
