# Load Combinations & Environmental Loading

## 1. ASCE 7 Load Combinations (LRFD — Strength Design)

### Basic Combinations (ASCE 7-22, Section 2.3.1)

| LC # | Combination |
|------|------------|
| 1 | 1.4 * D |
| 2 | 1.2 * D + 1.6 * L + 0.5 * (L_r or S or R) |
| 3 | 1.2 * D + 1.6 * (L_r or S or R) + (1.0 * L or 0.5 * W) |
| 4 | 1.2 * D + 1.0 * W + 1.0 * L + 0.5 * (L_r or S or R) |
| 5 | 1.2 * D + 1.0 * E + 1.0 * L + 0.2 * S |
| 6 | 0.9 * D + 1.0 * W |
| 7 | 0.9 * D + 1.0 * E |

| Symbol | Description |
|--------|-------------|
| D | Dead load |
| L | Live load |
| L_r | Roof live load |
| S | Snow load |
| R | Rain load |
| W | Wind load |
| E | Earthquake load |

### Critical Combinations for Solar Piles

| Design Check | Governing Combination | Notes |
|-------------|----------------------|-------|
| Compression (gravity) | LC 2 or LC 3 | Dead + live + snow |
| Compression (wind downward) | LC 4 | Dead + wind (downforce component) |
| Uplift / Tension | **LC 6: 0.9D + 1.0W** | **Usually governs for solar** |
| Lateral | LC 4 or LC 6 | Wind lateral component |
| Seismic | LC 5 or LC 7 | Earthquake zones |

> **LC 6 (0.9D + 1.0W) almost always governs solar pile design** because dead loads are very light and wind uplift/lateral forces are large relative to gravity.

---

## 2. ASCE 7 Load Combinations (ASD)

### Basic Combinations (ASCE 7-22, Section 2.4.1)

| LC # | Combination |
|------|------------|
| 1 | D |
| 2 | D + L |
| 3 | D + (L_r or S or R) |
| 4 | D + 0.75 * L + 0.75 * (L_r or S or R) |
| 5 | D + 0.6 * W |
| 6a | D + 0.75 * L + 0.75 * (0.6 * W) + 0.75 * (L_r or S or R) |
| 7 | 0.6 * D + 0.6 * W |
| 8 | D + 0.7 * E |
| 9 | D + 0.75 * L + 0.75 * (0.7 * E) + 0.75 * S |
| 10 | 0.6 * D + 0.7 * E |

### Critical ASD Combination for Solar

```
LC 7: 0.6 * D + 0.6 * W    (uplift/lateral governs)
```

---

## 3. IBC Load Combinations

IBC references ASCE 7 load combinations. Additional considerations:

### IBC Special Flood Provisions (Section 1612)

```
1.0 * F_a    (flood loads)
```

Added to applicable combinations in flood hazard areas.

### IBC Foundation-Specific

- Minimum lateral load for foundation design: 0.5 kip (IBC 1809.5)
- Minimum depth: 12 in below frost line (IBC 1809.5)

---

## 4. Wind Load on Solar Arrays

### ASCE 7-22 Chapter 29 — Solar Panel Wind Loads

#### Ground-Mounted Arrays (ASCE 7-22 Section 29.4.3)

```
F = q_h * GC_rn * A
```

| Symbol | Description |
|--------|-------------|
| F | Design wind force |
| q_h | Velocity pressure at mean roof height |
| GC_rn | Net pressure coefficient (from ASCE 7 figures/tables) |
| A | Tributary area of panels |

#### Velocity Pressure

```
q_z = 0.00256 * K_z * K_zt * K_d * K_e * V^2    (psf, V in mph)
```

| Symbol | Description | Typical Solar Value |
|--------|-------------|-------------------|
| K_z | Velocity pressure exposure coefficient | 0.57 - 0.85 (Exp C, z < 15ft) |
| K_zt | Topographic factor | 1.0 (flat terrain) |
| K_d | Wind directionality factor | 0.85 |
| K_e | Ground elevation factor | 1.0 (sea level) |
| V | Basic wind speed (3-sec gust, MRI) | Site-specific |

#### Exposure Category (Typical Solar)

| Category | Description | Solar Application |
|----------|-------------|-------------------|
| B | Urban/suburban | Rare for utility solar |
| C | Open terrain, scattered obstructions | **Most common for solar** |
| D | Flat, unobstructed coastal | Coastal solar farms |

#### K_z Values (Exposure C)

| Height z (ft) | K_z |
|---------------|-----|
| 0 - 15 | 0.85 |
| 20 | 0.90 |
| 25 | 0.94 |
| 30 | 0.98 |

### Wind Speed Reference (ASCE 7-22, Risk Category II)

| Region | V (mph) MRI 700-yr | V (mph) MRI 300-yr |
|--------|--------------------|--------------------|
| Interior US (typical) | 105 - 115 | 95 - 105 |
| Gulf Coast | 130 - 170 | 115 - 150 |
| Atlantic Coast | 110 - 180 | 100 - 160 |
| Hurricane-prone | 130 - 180+ | 115 - 170 |
| Western US | 95 - 110 | 85 - 100 |

---

## 5. Solar Tracker Wind Load Coefficients

### Single-Axis Tracker Loads (Manufacturer-Specific)

Typical load output from tracker manufacturers (varies by system):

| Load Case | Description | Typical Range |
|-----------|-------------|---------------|
| Dead (D) | Self-weight of tracker + modules | 3 - 6 psf |
| Wind Down (W_down) | Downward wind pressure | 15 - 40 psf |
| Wind Up (W_up) | Uplift wind pressure | 15 - 45 psf |
| Wind Lateral (W_lat) | Horizontal force along tracker torque tube | Varies |
| Snow (S) | Uniform snow load | Per ASCE 7, stow position |

### Tracker Stow Positions

| Condition | Stow Angle | Notes |
|-----------|-----------|-------|
| Normal operation | 0 to +/- 55 deg | Varies by tracker |
| High wind stow | 0 deg (flat) | Reduces wind exposure |
| Snow stow | 0 to 30 deg | Allows snow shedding |
| Night/maintenance stow | 0 deg | Default position |
| Hail stow | 60 - 90 deg | Module protection |

### Resolving Tracker Loads to Pile Reactions

For a single pile supporting a tracker torque tube:

```
V_pile = (D * A_trib) + (W_down or W_up) * A_trib    (vertical)
H_pile = W_lateral_force / n_piles                      (horizontal)
M_pile = H_pile * h_load                                (moment at ground)
```

| Symbol | Description |
|--------|-------------|
| A_trib | Tributary area per pile |
| n_piles | Number of piles along tracker |
| h_load | Height from ground to point of lateral load application |

### Typical Pile Reactions (Per Pile, Utility-Scale Tracker)

| Load Case | Vertical (lbs) | Lateral (lbs) | Moment at Ground (ft-lbs) |
|-----------|----------------|---------------|--------------------------|
| Dead only | 200 - 600 (comp) | ~0 | ~0 |
| Dead + wind (max compression) | 1500 - 5000 | 500 - 2500 | 1000 - 10000 |
| Dead + wind (max uplift) | -500 to -3000 (tension) | 500 - 2500 | 1000 - 10000 |
| Dead + wind (max lateral) | Varies | 1000 - 4000 | 3000 - 20000 |
| Dead + seismic | Varies | 200 - 1500 | 500 - 6000 |

> Actual values depend on tracker system, wind speed, exposure, and site geometry. Always use manufacturer-provided load tables.

---

## 6. Seismic Loading

### ASCE 7-22 Chapter 15 — Nonbuilding Structures

Solar trackers are typically classified as nonbuilding structures.

#### Equivalent Lateral Force (Simplified)

```
V_base = C_s * W
```

Where:
```
C_s = S_DS / (R / I_e)
```

But not less than:
```
C_s_min = max(0.044 * S_DS * I_e, 0.01)
```

And for S_1 >= 0.6g:
```
C_s_min = 0.5 * S_1 / (R / I_e)
```

| Symbol | Description | Typical Solar Value |
|--------|-------------|-------------------|
| S_DS | Design spectral acceleration (short period) | Site-specific |
| S_D1 | Design spectral acceleration (1-sec period) | Site-specific |
| R | Response modification coefficient | 1.5 - 3.0 (solar structures) |
| I_e | Importance factor | 1.0 (Risk Cat II) |
| W | Effective seismic weight | Dead load |

#### Seismic Design Category

| S_DS Range | SDC (Risk Cat II) |
|-----------|-------------------|
| < 0.167 | A |
| 0.167 - 0.33 | B |
| 0.33 - 0.50 | C |
| >= 0.50 | D |

> Many solar sites in the western US are SDC D. Sites in SDC A or B may be exempt from detailed seismic analysis per ASCE 7.

#### Overturning Moment for Solar Piles

```
M_seismic = V_base * h_cg
```

Where h_cg = height of center of gravity of the solar array above ground.

---

## 7. Snow Loading

### ASCE 7-22 Chapter 7

```
p_f = 0.7 * C_e * C_t * I_s * p_g    (flat roof / ground-mount snow load)
```

| Symbol | Description | Typical Value |
|--------|-------------|---------------|
| p_g | Ground snow load | Site-specific (maps + local data) |
| C_e | Exposure factor | 0.8 (open terrain) to 1.2 (sheltered) |
| C_t | Thermal factor | 1.2 (unheated structure) |
| I_s | Importance factor | 1.0 (Risk Cat II) |

### Solar-Specific Snow Considerations

- Panels at tilt shed snow; flat panels accumulate more
- Unbalanced snow loading can create asymmetric pile loads
- Drifting against panel edges is typically not significant for ground-mount
- Tracker stow angle affects snow accumulation

### Ground Snow Load Reference (Selected)

| Region | p_g (psf) | Notes |
|--------|----------|-------|
| Southern US | 0 - 5 | Minimal snow |
| Mid-Atlantic | 15 - 30 | |
| Midwest | 20 - 40 | |
| Mountain West | 30 - 100+ | Elevation dependent |
| Northeast | 30 - 80 | |
| Pacific Northwest | 10 - 40 | Lower elevations |

---

## 8. Thermal Loading

### Temperature Differential

```
delta_L = alpha * L * delta_T
```

| Symbol | Description | Value |
|--------|-------------|-------|
| alpha | Coefficient of thermal expansion (steel) | 6.5 x 10^-6 /degF |
| L | Length of structural member | ft |
| delta_T | Temperature range | 100-150 degF typical |

### Solar Pile Thermal Considerations

- Torque tube expansion/contraction transfers loads to piles
- Bearing connections accommodate movement; fixed connections transfer thermal force
- Typical tracker torque tube expansion: 0.5 - 2.0 in over full length
- Pile lateral load from thermal restraint: typically small (< 200 lbs) unless pile is at a fixed point

---

## 9. Other Environmental Loads

### Scour

For piles in flood-prone or drainage areas:
```
Effective embedment = Total embedment - Scour depth
```

Local scour depth estimation (simplified):
```
d_s = 2.0 * K_1 * K_2 * K_3 * B^0.65 * y_1^0.35 * Fr^0.43
```

Where Fr = Froude number of approach flow.

> Scour removes effective embedment and lateral soil resistance. All capacity calculations must use the post-scour soil profile.

### Frost Heave / Freeze-Thaw

- Piles must extend below maximum frost depth
- Frost heave forces on pile shaft (adfreeze):
  ```
  F_heave = tau_af * A_s_frost
  ```
  Where tau_af = adfreeze bond strength (typically 5 - 15 psi for steel in frozen soil)
- Embedment below frost zone must resist uplift from frost heave on the shaft above

### Flooding / High Water Table

- Use submerged unit weight (gamma') below water table
- Reduce effective stress and therefore skin friction and end bearing
- Check hydrostatic uplift on pile cap (if applicable)
- Verify stability against buoyancy for shallow systems

### Expansive / Collapsible Soils

- Expansive clay: negative skin friction on upper portion during wetting
- Collapsible soil (loess): capacity reduction upon saturation
- May require pre-drilled holes, chemical treatment, or deeper embedment

---

## 10. Load Combination Summary Table for Solar Piles

| Design Check | LRFD Combination | ASD Combination | Key Loads |
|-------------|-----------------|-----------------|-----------|
| Max compression | 1.2D + 1.6S + 0.5W_down | D + S + 0.6W_down | Gravity + snow + wind down |
| Max uplift (tension) | **0.9D + 1.0W_up** | **0.6D + 0.6W_up** | **Governs most solar piles** |
| Max lateral | 1.2D + 1.0W_lat | D + 0.6W_lat | Wind lateral |
| Max overturning | 0.9D + 1.0W | 0.6D + 0.6W | Combined V + H + M |
| Seismic compression | 1.2D + 1.0E + 0.2S | D + 0.7E | Seismic vertical + horizontal |
| Seismic uplift | 0.9D + 1.0E | 0.6D + 0.7E | Net uplift from seismic |
| Serviceability | 1.0D + 1.0W (service) | D + 0.6W | Deflection check |

> Always verify with project-specific structural loads from the tracker/racking manufacturer and the geotechnical report.
