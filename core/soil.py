"""Soil profile model, SPT correlations, and parameter derivation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class SoilType(str, Enum):
    SAND = "Sand"
    SILT = "Silt"
    CLAY = "Clay"
    GRAVEL = "Gravel"
    ORGANIC = "Organic"


class PYModel(str, Enum):
    """LPile v2022 p-y curve model selection."""
    AUTO = "Auto"
    # Clay models
    SOFT_CLAY_MATLOCK = "Soft Clay (Matlock)"
    API_SOFT_CLAY_USER_J = "API Soft Clay w/ User J"
    STIFF_CLAY_FREE_WATER = "Stiff Clay w/ Free Water (Reese)"
    STIFF_CLAY_NO_FREE_WATER = "Stiff Clay w/o Free Water (Reese)"
    MOD_STIFF_CLAY = "Modified Stiff Clay w/o Free Water"
    # Sand models
    SAND_REESE = "Sand (Reese)"
    API_SAND = "API Sand (O'Neill)"
    SMALL_STRAIN_SAND = "Small Strain Sand"
    LIQUEFIED_SAND_ROLLINS = "Liquefied Sand (Rollins)"
    LIQUEFIED_SAND_HYBRID = "Liquefied Sand Hybrid"
    # Rock models
    WEAK_ROCK = "Weak Rock (Reese)"
    STRONG_ROCK = "Strong Rock (Vuggy)"
    MASSIVE_ROCK = "Massive Rock"
    # Special soils
    PIEDMONT_RESIDUAL = "Piedmont Residual Soil"
    LOESS = "Loess"
    SILT_CEMENTED = "Silt (Cemented c-phi)"
    ELASTIC_SUBGRADE = "Elastic Subgrade"
    USER_INPUT = "User-Input p-y"


# Required parameters for each p-y model (drives UI field visibility)
PY_MODEL_PARAMS: dict[str, list[str]] = {
    PYModel.AUTO: [],
    PYModel.SOFT_CLAY_MATLOCK: ["gamma", "c_u", "epsilon_50"],
    PYModel.API_SOFT_CLAY_USER_J: ["gamma", "c_u", "epsilon_50", "J"],
    PYModel.STIFF_CLAY_FREE_WATER: ["gamma", "c_u", "epsilon_50", "k_py"],
    PYModel.STIFF_CLAY_NO_FREE_WATER: ["gamma", "c_u", "epsilon_50"],
    PYModel.MOD_STIFF_CLAY: ["gamma", "c_u", "epsilon_50"],
    PYModel.SAND_REESE: ["gamma", "phi", "k_py"],
    PYModel.API_SAND: ["gamma", "phi", "k_py"],
    PYModel.SMALL_STRAIN_SAND: ["gamma", "phi", "k_py", "G_max", "poissons_ratio",
                                 "void_ratio", "C_u_uniformity"],
    PYModel.LIQUEFIED_SAND_ROLLINS: ["gamma", "phi"],
    PYModel.LIQUEFIED_SAND_HYBRID: ["gamma", "phi"],
    PYModel.WEAK_ROCK: ["gamma", "q_u", "E_ir", "RQD", "k_rm"],
    PYModel.STRONG_ROCK: ["gamma", "q_u"],
    PYModel.MASSIVE_ROCK: ["gamma", "sigma_ci", "m_i", "poissons_ratio", "GSI", "E_rock"],
    PYModel.PIEDMONT_RESIDUAL: ["gamma", "c_u", "phi", "epsilon_50"],
    PYModel.LOESS: ["gamma", "c_u", "epsilon_50"],
    PYModel.SILT_CEMENTED: ["gamma", "c_u", "phi", "epsilon_50", "k_py"],
    PYModel.ELASTIC_SUBGRADE: ["gamma", "k_py"],
    PYModel.USER_INPUT: ["gamma", "user_py_data"],
}


GAMMA_WATER = 62.4  # pcf


@dataclass
class SoilLayer:
    """Single soil layer with properties."""
    top_depth: float        # ft (depth below ground surface)
    thickness: float        # ft
    soil_type: SoilType
    description: str = ""

    # Field data (at least N_spt should be provided)
    N_spt: float | None = None          # Raw SPT blow count

    # Derived or user-provided parameters
    gamma: float | None = None          # Total unit weight (pcf)
    phi: float | None = None            # Friction angle (degrees)
    c_u: float | None = None            # Undrained shear strength (psf)
    cohesion: float | None = None       # Effective cohesion c' (psf)

    # Water table
    is_submerged: bool = False

    # SPT corrections
    energy_ratio: float = 60.0          # Hammer energy ratio (%)
    C_B: float = 1.0                    # Borehole diameter correction
    C_R: float = 1.0                    # Rod length correction
    C_S: float = 1.0                    # Sampler correction

    # Advanced p-y model selection (None or AUTO = auto-select by SoilType)
    py_model: PYModel | None = None

    # Model-specific parameter overrides
    J: float | None = None               # Matlock J factor (0.25-0.5)
    k_py: float | None = None            # Subgrade reaction modulus override (lb/in^3)
    epsilon_50: float | None = None      # Explicit epsilon_50 override

    # Rock parameters
    q_u: float | None = None             # Unconfined compressive strength (psf)
    E_ir: float | None = None            # Initial modulus of rock mass (psi)
    RQD: float | None = None             # Rock Quality Designation (%)
    k_rm: float | None = None            # Weak rock strain factor (dimensionless)
    sigma_ci: float | None = None        # Intact rock UCS (psi, Hoek-Brown)
    m_i: float | None = None             # Hoek-Brown material index
    GSI: float | None = None             # Geological Strength Index (0-100)
    E_rock: float | None = None          # Rock mass modulus (psi)

    # Small strain sand parameters
    G_max: float | None = None           # Maximum shear modulus (psi)
    poissons_ratio: float | None = None  # Poisson's ratio
    void_ratio: float | None = None      # Void ratio
    C_u_uniformity: float | None = None  # Coefficient of uniformity (D60/D10)

    # User-input p-y curve data
    user_py_data: list | None = None     # [{"y": [...], "p": [...], "depth_ft": ...}, ...]

    @property
    def bottom_depth(self) -> float:
        return self.top_depth + self.thickness

    @property
    def mid_depth(self) -> float:
        return self.top_depth + self.thickness / 2

    @property
    def N_60(self) -> float | None:
        """Energy-corrected SPT value."""
        if self.N_spt is None:
            return None
        C_E = self.energy_ratio / 60.0
        return self.N_spt * C_E * self.C_B * self.C_R * self.C_S

    @property
    def gamma_effective(self) -> float:
        """Effective unit weight (pcf). Uses gamma_water if submerged."""
        g = self.gamma or self._estimate_gamma()
        if self.is_submerged:
            return g - GAMMA_WATER
        return g

    def _estimate_gamma(self) -> float:
        """Estimate unit weight from SPT N-value and soil type."""
        n = self.N_60 or 10
        if self.soil_type in (SoilType.SAND, SoilType.GRAVEL):
            if n < 4:
                return 105.0 if self.is_submerged else 95.0
            elif n < 10:
                return 115.0 if self.is_submerged else 105.0
            elif n < 30:
                return 125.0 if self.is_submerged else 110.0
            elif n < 50:
                return 135.0 if self.is_submerged else 120.0
            else:
                return 140.0 if self.is_submerged else 130.0
        else:  # Clay, Silt, Organic
            if n < 2:
                return 100.0
            elif n < 4:
                return 110.0
            elif n < 8:
                return 115.0
            elif n < 15:
                return 120.0
            elif n < 30:
                return 125.0
            else:
                return 130.0

    def get_phi(self, sigma_v: float = 0) -> float:
        """Get or estimate friction angle (degrees)."""
        if self.phi is not None:
            return self.phi
        n = self.N_60 or 10
        if self.soil_type in (SoilType.SAND, SoilType.GRAVEL):
            # Hatanaka & Uchida (1996)
            return min(45.0, math.sqrt(20.0 * n) + 20.0)
        elif self.soil_type == SoilType.SILT:
            return min(34.0, 24.0 + 0.25 * n)
        else:
            return 0.0  # Clay — phi=0 for undrained

    def get_cu(self) -> float:
        """Get or estimate undrained shear strength (psf)."""
        if self.c_u is not None:
            return self.c_u
        if self.soil_type in (SoilType.SAND, SoilType.GRAVEL):
            return 0.0
        n = self.N_60 or 5
        # Terzaghi & Peck: c_u ≈ 125 * N_60 (psf)
        return 125.0 * n

    @property
    def effective_py_model(self) -> PYModel:
        """Resolve the actual p-y model (handles AUTO / None)."""
        if self.py_model is not None and self.py_model != PYModel.AUTO:
            return self.py_model
        # Auto-select based on SoilType (existing behavior)
        if self.soil_type in (SoilType.CLAY, SoilType.SILT, SoilType.ORGANIC):
            return PYModel.SOFT_CLAY_MATLOCK
        else:
            return PYModel.API_SAND

    def get_epsilon_50(self) -> float:
        """Strain at 50% of ultimate stress for p-y curves."""
        if self.epsilon_50 is not None:
            return self.epsilon_50
        cu = self.get_cu()
        if cu < 500:
            return 0.020
        elif cu < 1000:
            return 0.010
        elif cu < 2000:
            return 0.007
        elif cu < 4000:
            return 0.005
        else:
            return 0.004

    def get_k_h(self) -> float:
        """Horizontal subgrade reaction modulus (lb/in^3) for p-y curves."""
        if self.k_py is not None:
            return self.k_py
        if self.soil_type in (SoilType.SAND, SoilType.GRAVEL):
            phi = self.get_phi()
            if phi <= 25:
                return 5.0 if self.is_submerged else 25.0
            elif phi <= 28:
                return 10.0 if self.is_submerged else 28.0
            elif phi <= 30:
                return 25.0 if self.is_submerged else 60.0
            elif phi <= 32:
                return 35.0 if self.is_submerged else 90.0
            elif phi <= 34:
                return 45.0 if self.is_submerged else 115.0
            elif phi <= 36:
                return 60.0 if self.is_submerged else 150.0
            elif phi <= 38:
                return 80.0 if self.is_submerged else 200.0
            else:
                return 100.0 if self.is_submerged else 300.0
        else:  # Cohesive
            cu = self.get_cu()
            if cu < 500:
                return 7.0
            elif cu < 1000:
                return 20.0
            elif cu < 2000:
                return 65.0
            elif cu < 4000:
                return 200.0
            else:
                return 500.0


@dataclass
class SoilProfile:
    """Soil profile consisting of stacked layers."""
    layers: list[SoilLayer] = field(default_factory=list)
    water_table_depth: float | None = None  # ft below ground surface

    def __post_init__(self):
        self._apply_water_table()

    def _apply_water_table(self):
        """Mark layers below water table as submerged."""
        if self.water_table_depth is None:
            return
        for layer in self.layers:
            if layer.mid_depth >= self.water_table_depth:
                layer.is_submerged = True
            else:
                layer.is_submerged = False

    def add_layer(self, layer: SoilLayer):
        self.layers.append(layer)
        self.layers.sort(key=lambda l: l.top_depth)
        self._apply_water_table()

    @property
    def total_depth(self) -> float:
        if not self.layers:
            return 0.0
        return max(l.bottom_depth for l in self.layers)

    def layer_at_depth(self, depth: float) -> SoilLayer | None:
        """Return the layer at a given depth (ft)."""
        for layer in self.layers:
            if layer.top_depth <= depth < layer.bottom_depth:
                return layer
        # If depth equals bottom of last layer, return last layer
        if self.layers and abs(depth - self.layers[-1].bottom_depth) < 0.01:
            return self.layers[-1]
        return None

    def effective_stress_at(self, depth: float) -> float:
        """Compute effective vertical stress (psf) at a given depth."""
        sigma_v = 0.0
        current_depth = 0.0
        for layer in self.layers:
            if current_depth >= depth:
                break
            layer_top = max(current_depth, layer.top_depth)
            layer_bot = min(depth, layer.bottom_depth)
            if layer_bot <= layer_top:
                continue

            dz = layer_bot - layer_top
            gamma = layer.gamma or layer._estimate_gamma()

            if self.water_table_depth is not None:
                # Portion above water table
                wt = self.water_table_depth
                if layer_top < wt:
                    dz_dry = min(dz, wt - layer_top)
                    sigma_v += gamma * dz_dry
                    dz -= dz_dry
                    layer_top += dz_dry
                # Portion below water table
                if dz > 0:
                    sigma_v += (gamma - GAMMA_WATER) * dz
            else:
                sigma_v += gamma * dz

            current_depth = layer_bot

        return sigma_v

    def total_stress_at(self, depth: float) -> float:
        """Compute total vertical stress (psf) at a given depth."""
        sigma_v = 0.0
        current_depth = 0.0
        for layer in self.layers:
            if current_depth >= depth:
                break
            layer_top = max(current_depth, layer.top_depth)
            layer_bot = min(depth, layer.bottom_depth)
            if layer_bot <= layer_top:
                continue
            dz = layer_bot - layer_top
            gamma = layer.gamma or layer._estimate_gamma()
            sigma_v += gamma * dz
            current_depth = layer_bot
        return sigma_v

    def discretize(self, dz: float = 0.5) -> list[dict]:
        """Discretize the profile into uniform increments.

        Returns list of dicts with depth, layer properties, and stresses.
        """
        if not self.layers:
            return []
        max_depth = self.total_depth
        depths = np.arange(0, max_depth + dz, dz)
        nodes = []
        for d in depths:
            layer = self.layer_at_depth(d)
            if layer is None:
                continue
            nodes.append({
                "depth_ft": float(d),
                "depth_in": float(d) * 12.0,
                "layer": layer,
                "sigma_v_eff": self.effective_stress_at(d),
                "sigma_v_total": self.total_stress_at(d),
            })
        return nodes


# --- Soil Layer Construction Helper ---

def build_soil_layer_from_dict(ld: dict) -> SoilLayer:
    """Build a SoilLayer from a session-state dict.

    Handles backward compatibility: missing keys default to None.
    Used by all Streamlit pages to avoid duplicating construction logic.
    """
    _py_model_val = ld.get("py_model")
    _py_model = PYModel(_py_model_val) if _py_model_val else None

    return SoilLayer(
        top_depth=ld["top_depth"],
        thickness=ld["thickness"],
        soil_type=SoilType(ld["soil_type"]),
        description=ld.get("description", ""),
        N_spt=ld.get("N_spt"),
        gamma=ld.get("gamma"),
        phi=ld.get("phi"),
        c_u=ld.get("c_u"),
        cohesion=ld.get("cohesion"),
        py_model=_py_model,
        J=ld.get("J"),
        k_py=ld.get("k_py"),
        epsilon_50=ld.get("epsilon_50"),
        q_u=ld.get("q_u"),
        E_ir=ld.get("E_ir"),
        RQD=ld.get("RQD"),
        k_rm=ld.get("k_rm"),
        sigma_ci=ld.get("sigma_ci"),
        m_i=ld.get("m_i"),
        GSI=ld.get("GSI"),
        E_rock=ld.get("E_rock"),
        G_max=ld.get("G_max"),
        poissons_ratio=ld.get("poissons_ratio"),
        void_ratio=ld.get("void_ratio"),
        C_u_uniformity=ld.get("C_u_uniformity"),
        user_py_data=ld.get("user_py_data"),
    )


# --- SPT Correction Utilities ---

def correct_N_overburden(N_60: float, sigma_v: float) -> float:
    """Apply Liao & Whitman overburden correction.

    Args:
        N_60: Energy-corrected SPT value
        sigma_v: Effective vertical stress (psf)

    Returns:
        (N1)_60
    """
    Pa = 2116.0  # psf (1 atm)
    if sigma_v <= 0:
        C_N = 2.0
    else:
        C_N = min(2.0, math.sqrt(Pa / sigma_v))
    return C_N * N_60


def n_to_phi_hatanaka(N1_60: float) -> float:
    """Hatanaka & Uchida (1996): phi' from (N1)_60."""
    return min(45.0, math.sqrt(20.0 * max(N1_60, 1)) + 20.0)


def n_to_phi_peck(N1_60: float) -> float:
    """Peck, Hanson, Thornburn (1974): phi' from (N1)_60."""
    return 27.1 + 0.3 * N1_60 - 0.00054 * N1_60**2


def n_to_cu(N_60: float) -> float:
    """Terzaghi & Peck: c_u (psf) from N_60."""
    return 125.0 * N_60


def n_to_Es_sand(N_60: float, preloaded: bool = False) -> float:
    """Soil modulus E_s (tsf) from N_60 for sand."""
    if preloaded:
        return 10.0 * (N_60 + 5)
    return 5.0 * (N_60 + 15)
