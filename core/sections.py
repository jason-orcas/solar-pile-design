"""Steel section database for solar pile foundations."""

import math
from dataclasses import dataclass


@dataclass
class SteelSection:
    name: str
    type: str           # "W" or "C"
    depth: float        # in
    width: float        # in (flange width)
    area: float         # in^2
    weight: float       # plf
    Ix: float           # in^4 (strong axis)
    Iy: float           # in^4 (weak axis)
    Sx: float           # in^3 (strong axis)
    Sy: float           # in^3 (weak axis)
    Zx: float           # in^3 (plastic, strong)
    Zy: float           # in^3 (plastic, weak)
    tf: float           # in (flange thickness)
    tw: float           # in (web thickness)
    fy: float = 50.0    # ksi (default A572 Gr 50)

    @property
    def perimeter(self) -> float:
        """Approximate exposed perimeter (in) for skin friction."""
        if self.type == "W":
            return 2 * self.depth + 4 * self.width - 2 * self.tw
        else:  # C-shape
            return 2 * self.depth + 2 * self.width

    @property
    def tip_area(self) -> float:
        """Cross-sectional area at tip (in^2) for end bearing."""
        return self.depth * self.width

    @property
    def EI_strong(self) -> float:
        """Flexural rigidity about strong axis (lb-in^2)."""
        return 29000.0 * 1000.0 * self.Ix  # E = 29000 ksi -> 29e6 psi

    @property
    def EI_weak(self) -> float:
        """Flexural rigidity about weak axis (lb-in^2)."""
        return 29000.0 * 1000.0 * self.Iy

    @property
    def Mp_strong(self) -> float:
        """Plastic moment capacity, strong axis (kip-in)."""
        return self.fy * self.Zx

    @property
    def Mp_weak(self) -> float:
        """Plastic moment capacity, weak axis (kip-in)."""
        return self.fy * self.Zy

    @property
    def My_strong(self) -> float:
        """Yield moment, strong axis (kip-in)."""
        return self.fy * self.Sx

    @property
    def My_weak(self) -> float:
        """Yield moment, weak axis (kip-in)."""
        return self.fy * self.Sy

    def fiber_patches(self) -> list[dict]:
        """Return fiber patch geometry for W-shape cross-section.

        Returns list of dicts describing rectangular patches (2 flanges + 1 web)
        for use with OpenSeesPy ops.patch('rect', ...).
        Each dict has: y_min, y_max, z_min, z_max, n_y, n_z (fiber counts).
        """
        d = self.depth
        bf = self.width
        tf = self.tf
        tw = self.tw
        return [
            {"y_min": -d / 2, "y_max": -d / 2 + tf,
             "z_min": -bf / 2, "z_max": bf / 2, "n_y": 10, "n_z": 1},
            {"y_min": d / 2 - tf, "y_max": d / 2,
             "z_min": -bf / 2, "z_max": bf / 2, "n_y": 10, "n_z": 1},
            {"y_min": -d / 2 + tf, "y_max": d / 2 - tf,
             "z_min": -tw / 2, "z_max": tw / 2, "n_y": 1, "n_z": 20},
        ]


# Solar pile section database (AISC values)
SECTIONS = {
    "W6x7": SteelSection(
        name="W6x7", type="W", depth=5.80, width=3.94, area=2.05, weight=7.0,
        Ix=12.2, Iy=1.41, Sx=4.21, Sy=0.716, Zx=4.83, Zy=1.12,
        tf=0.230, tw=0.170,
    ),
    "W6x9": SteelSection(
        name="W6x9", type="W", depth=5.90, width=3.94, area=2.64, weight=9.0,
        Ix=16.4, Iy=1.83, Sx=5.56, Sy=0.929, Zx=6.23, Zy=1.44,
        tf=0.215, tw=0.170,
    ),
    "W6x12": SteelSection(
        name="W6x12", type="W", depth=6.03, width=4.00, area=3.55, weight=12.0,
        Ix=22.1, Iy=2.99, Sx=7.31, Sy=1.50, Zx=8.30, Zy=2.32,
        tf=0.280, tw=0.230,
    ),
    "W6x15": SteelSection(
        name="W6x15", type="W", depth=5.99, width=5.99, area=4.43, weight=15.0,
        Ix=29.1, Iy=9.32, Sx=9.72, Sy=3.11, Zx=10.8, Zy=4.75,
        tf=0.260, tw=0.230,
    ),
    "W8x10": SteelSection(
        name="W8x10", type="W", depth=7.89, width=3.94, area=2.96, weight=10.0,
        Ix=30.8, Iy=1.99, Sx=7.81, Sy=1.01, Zx=8.87, Zy=1.58,
        tf=0.205, tw=0.170,
    ),
    "W8x13": SteelSection(
        name="W8x13", type="W", depth=7.99, width=4.00, area=3.84, weight=13.0,
        Ix=39.6, Iy=2.73, Sx=9.91, Sy=1.37, Zx=11.4, Zy=2.13,
        tf=0.255, tw=0.230,
    ),
    "W8x15": SteelSection(
        name="W8x15", type="W", depth=8.11, width=4.01, area=4.44, weight=15.0,
        Ix=48.0, Iy=3.41, Sx=11.8, Sy=1.70, Zx=13.6, Zy=2.64,
        tf=0.315, tw=0.245,
    ),
    "W8x18": SteelSection(
        name="W8x18", type="W", depth=8.14, width=5.25, area=5.26, weight=18.0,
        Ix=61.9, Iy=7.97, Sx=15.2, Sy=3.04, Zx=17.0, Zy=4.66,
        tf=0.330, tw=0.230,
    ),
    "C4x5.4": SteelSection(
        name="C4x5.4", type="C", depth=4.00, width=1.58, area=1.59, weight=5.4,
        Ix=3.85, Iy=0.319, Sx=1.93, Sy=0.283, Zx=2.35, Zy=0.547,
        tf=0.296, tw=0.184,
    ),
    "C4x7.25": SteelSection(
        name="C4x7.25", type="C", depth=4.00, width=1.72, area=2.13, weight=7.25,
        Ix=4.59, Iy=0.432, Sx=2.29, Sy=0.343, Zx=2.88, Zy=0.668,
        tf=0.296, tw=0.321,
    ),
}


def get_section(name: str) -> SteelSection:
    """Look up a section by name. Raises KeyError if not found."""
    return SECTIONS[name]


def list_sections() -> list[str]:
    """Return sorted list of available section names."""
    return sorted(SECTIONS.keys())


@dataclass
class CustomPileSection:
    """For non-standard pile shapes (pipe, HSS, etc.)."""
    name: str
    perimeter: float    # in
    tip_area: float     # in^2
    area: float         # in^2
    EI: float           # lb-in^2
    My: float           # kip-in (yield moment)
    depth: float        # in (outer dimension)
    width: float        # in (outer dimension)

    @property
    def EI_strong(self) -> float:
        return self.EI

    @property
    def EI_weak(self) -> float:
        return self.EI

    @property
    def My_strong(self) -> float:
        return self.My

    @property
    def My_weak(self) -> float:
        return self.My


def make_pipe_section(
    name: str, OD: float, wall: float, fy: float = 50.0
) -> CustomPileSection:
    """Create a round pipe pile section.

    Args:
        OD: outer diameter (in)
        wall: wall thickness (in)
        fy: yield stress (ksi)
    """
    import math
    ID = OD - 2 * wall
    area = math.pi / 4 * (OD**2 - ID**2)
    I = math.pi / 64 * (OD**4 - ID**4)
    S = I / (OD / 2)
    Z = (OD**3 - ID**3) / 6
    EI = 29000.0 * 1000.0 * I
    My = fy * S
    return CustomPileSection(
        name=name,
        perimeter=math.pi * OD,
        tip_area=math.pi / 4 * OD**2,
        area=area,
        EI=EI,
        My=My,
        depth=OD,
        width=OD,
    )


# ============================================================================
# Corrosion Analysis (FHWA/AASHTO guidance)
# ============================================================================

# Corrosion rates in mils/year per environment (FHWA/AASHTO)
CORROSION_RATES: dict[str, dict[str, float]] = {
    "Atmospheric":          {"low": 1.0, "high": 2.0, "typical": 1.5},
    "Splash zone":          {"low": 3.0, "high": 5.0, "typical": 4.0},
    "Buried (disturbed)":   {"low": 0.5, "high": 2.0, "typical": 1.25},
    "Buried (undisturbed)": {"low": 0.5, "high": 1.0, "typical": 0.75},
    "Fill / aggressive":    {"low": 2.0, "high": 4.0, "typical": 3.0},
}

# Coating reduction factors applied to the base corrosion rate
COATING_REDUCTION: dict[str, float] = {
    "None":              1.0,
    "Galvanized (G90)":  0.50,
    "Galvanized (G185)": 0.35,
}


@dataclass
class CorrosionParams:
    """Computed corrosion parameters."""
    design_life: float        # years
    environment: str
    coating: str
    corrosion_rate: float     # mils/year (after coating reduction)
    t_loss_per_side: float    # in (thickness loss per exposed face)


def compute_corrosion_params(
    design_life: float, environment: str, coating: str
) -> CorrosionParams:
    """Compute corrosion thickness loss from FHWA/AASHTO tables.

    Args:
        design_life: Project design life in years.
        environment: Key into CORROSION_RATES.
        coating: Key into COATING_REDUCTION.

    Returns:
        CorrosionParams with computed rate and thickness loss.
    """
    base_rate = CORROSION_RATES[environment]["typical"]  # mils/year
    effective_rate = base_rate * COATING_REDUCTION[coating]
    t_loss = effective_rate * design_life / 1000.0  # mils -> inches
    return CorrosionParams(
        design_life=design_life,
        environment=environment,
        coating=coating,
        corrosion_rate=effective_rate,
        t_loss_per_side=t_loss,
    )


def corroded_section(
    nominal: SteelSection, t_loss_per_side: float
) -> SteelSection:
    """Create a new SteelSection with reduced dimensions due to corrosion.

    Corrosion is applied to BOTH exposed faces of flanges and web:
        tf_corroded = tf - 2 * t_loss_per_side
        tw_corroded = tw - 2 * t_loss_per_side

    Section properties (A, Ix, Iy, Sx, Sy, Zx, Zy) are recomputed from
    first-principles W-shape formulas with the reduced thicknesses.

    Args:
        nominal: Original AISC SteelSection.
        t_loss_per_side: Thickness loss per exposed surface (in).

    Returns:
        New SteelSection with corroded properties.

    Raises:
        ValueError: If corroded tf or tw would be <= 0.
    """
    if t_loss_per_side <= 0:
        return nominal

    tf_c = nominal.tf - 2 * t_loss_per_side
    tw_c = nominal.tw - 2 * t_loss_per_side

    if tf_c <= 0 or tw_c <= 0:
        raise ValueError(
            f"Corrosion loss {t_loss_per_side:.4f} in/side exceeds half of "
            f"tf={nominal.tf:.3f} in or tw={nominal.tw:.3f} in. "
            f"Section is fully consumed."
        )

    d = nominal.depth
    bf = nominal.width
    h_w = d - 2 * tf_c  # clear web height

    # Area
    area = 2 * bf * tf_c + h_w * tw_c

    # Weight (scale proportionally)
    weight = nominal.weight * (area / nominal.area)

    # Strong axis moment of inertia (Ix)
    Ix = (2 * (bf * tf_c**3 / 12 + bf * tf_c * ((d - tf_c) / 2)**2)
          + tw_c * h_w**3 / 12)

    # Weak axis moment of inertia (Iy)
    Iy = 2 * tf_c * bf**3 / 12 + h_w * tw_c**3 / 12

    # Elastic section moduli
    Sx = Ix / (d / 2)
    Sy = Iy / (bf / 2)

    # Plastic section moduli
    Zx = 2 * bf * tf_c * (d - tf_c) / 2 + tw_c * h_w**2 / 4
    Zy = 2 * tf_c * bf**2 / 4 + h_w * tw_c**2 / 4

    return SteelSection(
        name=f"{nominal.name} (corroded)",
        type=nominal.type,
        depth=d,
        width=bf,
        area=area,
        weight=weight,
        Ix=Ix, Iy=Iy,
        Sx=Sx, Sy=Sy,
        Zx=Zx, Zy=Zy,
        tf=tf_c, tw=tw_c,
        fy=nominal.fy,
    )
