"""Steel section database for solar pile foundations."""

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
