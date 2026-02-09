# Axial Pile Capacity Formulas

## 1. General Framework

### Ultimate Axial Capacity (Compression)

```
Q_ult = Q_s + Q_b
```

| Symbol | Description | Units |
|--------|-------------|-------|
| Q_ult | Ultimate pile capacity (compression) | lbs or kN |
| Q_s | Total skin (shaft) friction resistance | lbs or kN |
| Q_b | End bearing (tip) resistance | lbs or kN |

### Ultimate Axial Capacity (Tension / Uplift)

```
Q_uplift = Q_s_tension
```

> Tension capacity uses shaft friction only (no end bearing). A reduction factor of 0.75 to 1.0 is typically applied to the compression skin friction value depending on the method and soil type.

### Allowable Capacity (ASD)

```
Q_allow = Q_ult / FS
```

| Condition | Typical FS |
|-----------|-----------|
| Compression (static) | 2.0 - 3.0 |
| Compression (with load test) | 1.5 - 2.0 |
| Tension / Uplift | 2.5 - 3.0 |
| Seismic / Transient | 1.5 - 2.0 (may use 75% increase) |

### LRFD Factored Resistance

```
phi * R_n >= sum(gamma_i * Q_i)
```

| Condition | Resistance Factor (phi) | Reference |
|-----------|------------------------|-----------|
| Driven piles - skin friction (clay, alpha method) | 0.35 | AASHTO |
| Driven piles - skin friction (sand, Nordlund) | 0.45 | AASHTO |
| Driven piles - end bearing | 0.40 - 0.50 | AASHTO |
| Driven piles - with PDA/CAPWAP | 0.65 | AASHTO |
| Driven piles - with static load test | 0.75 - 0.80 | AASHTO |
| Helical piles - compression | 0.40 - 0.60 | ICC-ES / local |
| Helical piles - tension | 0.50 | ICC-ES / local |

---

## 2. Skin Friction Methods

### 2a. Alpha Method (Total Stress — Cohesive Soils)

Used for clays and silts under undrained conditions.

```
Q_s = sum( alpha * c_u * A_s )
```

| Symbol | Description |
|--------|-------------|
| alpha | Adhesion factor (dimensionless) |
| c_u | Undrained shear strength (psf or kPa) |
| A_s | Surface area of pile shaft in the layer = perimeter * layer_thickness |

**Alpha Correlations (Tomlinson, API):**

| c_u (psf) | c_u (kPa) | alpha |
|-----------|-----------|-------|
| < 500 | < 25 | 1.00 |
| 500 - 1000 | 25 - 50 | 1.00 - 0.80 |
| 1000 - 2000 | 50 - 100 | 0.80 - 0.50 |
| 2000 - 4000 | 100 - 200 | 0.50 - 0.35 |
| > 4000 | > 200 | 0.35 - 0.25 |

**API RP 2A simplified:**
```
alpha = 0.5 * (c_u / sigma'_v)^(-0.5)    for c_u / sigma'_v <= 1.0
alpha = 0.5 * (c_u / sigma'_v)^(-0.25)   for c_u / sigma'_v > 1.0
alpha <= 1.0
```

### 2b. Beta Method (Effective Stress — Cohesionless & Cohesive Soils)

```
Q_s = sum( beta * sigma'_v * A_s )
```

| Symbol | Description |
|--------|-------------|
| beta | Shaft friction coefficient = K_s * tan(delta) |
| sigma'_v | Effective vertical stress at midpoint of layer (psf or kPa) |
| K_s | Lateral earth pressure coefficient on shaft |
| delta | Pile-soil interface friction angle |

**Beta Values (Typical Ranges):**

| Soil Type | beta Range | Notes |
|-----------|-----------|-------|
| Soft clay (NC) | 0.15 - 0.35 | Normally consolidated |
| Stiff clay (OC) | 0.30 - 0.80 | Overconsolidated |
| Loose sand | 0.20 - 0.40 | |
| Medium dense sand | 0.30 - 0.60 | |
| Dense sand | 0.50 - 1.00 | |
| Gravel | 0.60 - 1.20 | |

**K_s Estimation:**

| Pile Type | K_s / K_0 Ratio |
|-----------|----------------|
| Driven displacement (H-pile, closed-end) | 1.0 - 2.0 |
| Driven low-displacement (open-end) | 0.75 - 1.25 |
| Drilled shaft | 0.70 - 1.00 |
| Helical pile | 0.50 - 1.00 |

Where K_0 = 1 - sin(phi') for normally consolidated soils.

**Interface Friction Angle (delta):**

| Pile Material | delta / phi' |
|--------------|-------------|
| Steel (smooth) | 0.50 - 0.70 |
| Steel (rusted/corrugated) | 0.70 - 0.90 |
| Concrete (precast) | 0.80 - 1.00 |
| Concrete (CIP) | 1.00 |
| Timber | 0.80 - 0.90 |

### 2c. Meyerhof SPT Method (Cohesionless Soils)

```
f_s = N_avg / 50    (tsf)
f_s = N_avg * 2     (kPa)
```

```
Q_s = f_s * A_s
```

Where N_avg is the average uncorrected SPT N-value along the shaft.

**Limiting skin friction:**

| Soil Type | Maximum f_s (tsf) | Maximum f_s (kPa) |
|-----------|-------------------|-------------------|
| Sand | 1.0 | 100 |
| Silt | 0.6 | 60 |

### 2d. Nordlund Method (Cohesionless Soils — Driven Piles)

```
Q_s = sum( K_delta * C_F * sigma'_v * sin(delta) / cos(omega) * C_d * delta_z )
```

| Symbol | Description |
|--------|-------------|
| K_delta | Coefficient of lateral earth pressure (from Nordlund charts, function of phi' and pile taper angle omega) |
| C_F | Correction factor for K_delta (function of displaced volume) |
| sigma'_v | Effective overburden pressure at depth z |
| delta | Pile-soil friction angle (from Nordlund charts) |
| omega | Pile taper angle (0 for uniform section) |
| C_d | Pile perimeter |
| delta_z | Layer thickness increment |

> For straight-sided piles (omega = 0), the formula simplifies to:
> Q_s = sum( K_delta * C_F * sigma'_v * sin(delta) * C_d * delta_z )

---

## 3. End Bearing Methods

### 3a. General End Bearing Formula

```
Q_b = q_b * A_b
```

| Symbol | Description |
|--------|-------------|
| q_b | Unit end bearing resistance (psf or kPa) |
| A_b | Cross-sectional area of pile tip |

### 3b. Cohesive Soils (Undrained)

```
q_b = N_c * c_u
```

Where N_c = 9.0 (for deep foundations, depth/diameter > 4).

For shallow embedment:
```
N_c = 6.0 * [1 + 0.2 * (D/B)]    <= 9.0
```

| Symbol | Description |
|--------|-------------|
| D | Embedment depth |
| B | Pile width or diameter |

### 3c. Cohesionless Soils — Meyerhof SPT Method

```
q_b = 4 * N_corr * (D/B)    (tsf)    <= limiting q_b
```

**Limiting end bearing (Meyerhof):**

```
q_b_max = 4 * N_corr    (tsf)    for driven piles
q_b_max = 1.3 * N_corr  (tsf)    for drilled shafts
```

Where N_corr = corrected SPT N-value near the pile tip (average over 1B above to 4B below tip).

### 3d. Cohesionless Soils — Bearing Capacity Theory

```
q_b = sigma'_v * N_q * (correction factors)
```

**Meyerhof N_q values (driven piles):**

| phi' (degrees) | N_q |
|----------------|-----|
| 25 | 12.5 |
| 26 | 14.5 |
| 28 | 21 |
| 30 | 30 |
| 32 | 44 |
| 34 | 65 |
| 36 | 100 |
| 38 | 150 |
| 40 | 225 |

**Limiting unit end bearing:**

| phi' (degrees) | q_b_max (tsf) | q_b_max (kPa) |
|----------------|--------------|---------------|
| 25 | 50 | 5000 |
| 28 | 75 | 7500 |
| 30 | 100 | 10000 |
| 32 | 125 | 12500 |
| 34 | 175 | 17500 |
| 36 | 250 | 25000 |
| 38 | 350 | 35000 |
| 40 | 500 | 50000 |

### 3e. Nordlund End Bearing (Cohesionless)

```
q_b = alpha_t * N_q * sigma'_v    <= q_L
```

| Symbol | Description |
|--------|-------------|
| alpha_t | Dimensionless coefficient (from Nordlund chart, function of phi' and pile diameter) |
| N_q | Bearing capacity factor |
| q_L | Limiting unit tip resistance (from Nordlund chart) |

---

## 4. Helical Pile Capacity

### Individual Bearing Method

```
Q_ult = sum( q_h * A_h ) + Q_s_shaft
```

| Symbol | Description |
|--------|-------------|
| q_h | Bearing capacity at each helix plate |
| A_h | Projected area of each helix plate = pi/4 * (D_h^2 - d_s^2) |
| Q_s_shaft | Shaft friction above the uppermost helix (if applicable) |

**Cohesionless soil:**
```
q_h = sigma'_v * N_q
```

**Cohesive soil:**
```
q_h = c_u * N_c + sigma'_v
```

Where N_c = 9.0 for deep helices (H/D_h >= 5).

### Torque Correlation Method

```
Q_ult = K_t * T
```

| Symbol | Description |
|--------|-------------|
| K_t | Empirical torque factor (1/ft or 1/m) |
| T | Installation torque (ft-lbs or N-m) |

**Typical K_t values:**

| Shaft Size | K_t (1/ft) | K_t (1/m) |
|-----------|-----------|-----------|
| 1.5" square | 10 | 33 |
| 1.75" square | 9 | 30 |
| 2.875" OD pipe | 7 | 23 |
| 3.5" OD pipe | 6 | 20 |
| 4.5" OD pipe | 5 | 16 |

---

## 5. Solar Pile Specific Considerations

### Typical Solar Pile Sections

| Section | Perimeter (in) | Area (in^2) | Weight (plf) |
|---------|----------------|-------------|--------------|
| W6x7 | 14.7 | 2.05 | 7.0 |
| W6x9 | 14.9 | 2.64 | 9.0 |
| W6x12 | 15.5 | 3.55 | 12.0 |
| W6x15 | 15.9 | 4.43 | 15.0 |
| W8x10 | 17.9 | 2.96 | 10.0 |
| W8x13 | 18.3 | 3.84 | 13.0 |
| C4x5.4 | 12.6 | 1.59 | 5.4 |
| C4x7.25 | 13.1 | 2.13 | 7.25 |

### Embedment Depth Considerations

- Typical solar pile embedment: 6 ft to 15 ft
- Minimum embedment for lateral stability: 4 * pile width or 4 ft (whichever governs)
- Frost depth: embedment must extend below frost line
- Critical depth for skin friction: typically 15B to 20B (after which sigma'_v is capped)

### Cyclic Loading Reduction

For solar piles subject to wind-induced cyclic loading:

| Condition | Reduction Factor |
|-----------|-----------------|
| Static loading | 1.00 |
| Moderate cyclic (wind gusts) | 0.85 - 0.95 |
| Severe cyclic (seismic) | 0.70 - 0.85 |
| Tension under cyclic loading | 0.60 - 0.80 |
