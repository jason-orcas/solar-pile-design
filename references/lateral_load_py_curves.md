# Lateral Load Analysis & p-y Curve Formulas

## 1. Governing Differential Equation

The lateral behavior of a pile is governed by:

```
EI * (d^4 y / dz^4) + P_axial * (d^2 y / dz^2) - p(y) = 0
```

| Symbol | Description | Units |
|--------|-------------|-------|
| EI | Flexural rigidity of pile | lb-in^2 or kN-m^2 |
| y | Lateral deflection | in or m |
| z | Depth below ground surface | in or m |
| P_axial | Axial load on pile | lbs or kN |
| p(y) | Soil resistance per unit length (from p-y curve) | lb/in or kN/m |

---

## 2. Pile Classification: Long vs. Short

### Characteristic Length (Clay — Matlock)

```
T = (EI / E_s)^(1/5)
```

For constant soil modulus:
```
R = (EI / k_h)^(1/4)
```

| Symbol | Description |
|--------|-------------|
| T | Relative stiffness factor (linearly increasing modulus) |
| R | Relative stiffness factor (constant modulus) |
| E_s | Soil modulus (increases with depth for sand) |
| k_h | Horizontal subgrade reaction modulus |

### Classification Criteria

| Condition | Classification | Behavior |
|-----------|---------------|----------|
| L / T >= 4 or L / R >= 4 | Long (flexible) | Toe fixity irrelevant |
| 2 < L / T < 4 | Intermediate | Both head and toe conditions matter |
| L / T <= 2 | Short (rigid) | Rotates as rigid body |

---

## 3. Subgrade Reaction Modulus (k_h)

### Terzaghi Recommendations

**Cohesionless soils (modulus increases linearly with depth):**

```
k_h = n_h * z / B
```

| Relative Density | n_h (dry/moist) lb/in^3 | n_h (submerged) lb/in^3 |
|-----------------|------------------------|------------------------|
| Loose | 7 | 4 |
| Medium | 21 | 14 |
| Dense | 56 | 34 |

**Cohesive soils (constant modulus):**

| Consistency | c_u (psf) | k_h (lb/in^3) |
|------------|-----------|---------------|
| Soft | 250 - 500 | 4 - 10 |
| Medium | 500 - 1000 | 10 - 30 |
| Stiff | 1000 - 2000 | 30 - 100 |
| Very stiff | 2000 - 4000 | 100 - 300 |
| Hard | > 4000 | 300 - 800 |

---

## 4. Matlock p-y Curves — Soft Clay (Undrained, Static)

Reference: Matlock, H. (1970)

### Static Loading

```
p / p_ult = 0.5 * (y / y_50)^(1/3)
```

For y > 8 * y_50:
```
p = p_ult
```

### Ultimate Soil Resistance (p_ult)

Near surface (z < z_r):
```
p_ult = [3 + gamma' * z / c_u + J * z / B] * c_u * B
```

At depth (z >= z_r):
```
p_ult = 9 * c_u * B
```

Transition depth:
```
z_r = 6 * B / (gamma' * B / c_u + J)
```

| Symbol | Description | Typical Value |
|--------|-------------|---------------|
| c_u | Undrained shear strength | site-specific |
| gamma' | Effective unit weight | site-specific |
| B | Pile width/diameter | pile-specific |
| J | Empirical constant | 0.5 (stiff clay) to 0.25 (soft clay) |
| epsilon_50 | Strain at 50% of ultimate stress | see table below |
| y_50 | 2.5 * epsilon_50 * B | |

### epsilon_50 Values

| Clay Consistency | c_u (psf) | epsilon_50 |
|-----------------|-----------|-----------|
| Soft | < 500 | 0.020 |
| Medium | 500 - 1000 | 0.010 |
| Stiff | 1000 - 2000 | 0.007 |
| Very stiff | 2000 - 4000 | 0.005 |
| Hard | > 4000 | 0.004 |

### Cyclic Loading (Matlock)

For z < z_r:
```
p / p_ult = 0.5 * (y / y_50)^(1/3)       for y <= 3 * y_50
p / p_ult = 0.72 * (z / z_r)              for y > 3 * y_50
```

For z >= z_r:
```
p / p_ult = 0.5 * (y / y_50)^(1/3)       for y <= 3 * y_50
p / p_ult = 0.72                           for y > 3 * y_50
```

---

## 5. Reese p-y Curves — Stiff Clay Below Water Table (Static)

Reference: Reese, L.C., Cox, W.R., Koop, F.D. (1975)

### Static Loading Curve Construction

The curve is defined by four segments:

**Segment 1 (initial):**
```
p = k_s * z * y                 for 0 <= y <= y_A
```

**Segment 2 (parabolic transition):**
```
p = 0.5 * p_c * (y / y_50)^0.5    for y_A <= y <= A_s * y_50
```

**Segment 3 (linear):**
```
p = 0.5 * p_c - 0.055 * p_c * ((y - A_s * y_50) / (A_s * y_50))
```

**Segment 4 (residual):**
```
p = p_c * [1.225 - 0.75 * (z / B)] * 0.5        (minimum 0.5 * p_c * 0.225)
```

### Ultimate Resistance

```
p_ca = [2 * c_u + gamma' * z + 2.83 * c_u * z / B] * B
p_cb = 11 * c_u * B
p_c = min(p_ca, p_cb)
```

### Constants

| Parameter | Value |
|-----------|-------|
| A_s (static) | 0.35 to 2.0 (function of z/B) |
| A_c (cyclic) | 0.102 to 0.20 (function of z/B) |

---

## 6. Reese p-y Curves — Sand (Static)

Reference: Reese, L.C., Cox, W.R., Koop, F.D. (1974)

### Ultimate Resistance

Near surface (wedge failure):
```
p_us = gamma * z * [K_0 * z * tan(phi') * sin(beta) / tan(beta - phi') * cos(alpha) +
       tan(beta) / tan(beta - phi') * (B + z * tan(beta) * tan(alpha)) +
       K_0 * z * tan(beta) * (tan(phi') * sin(beta) - tan(alpha)) - K_a * B]
```

At depth (flow-around failure):
```
p_ud = K_a * B * gamma * z * (tan^8(beta) - 1) + K_0 * B * gamma * z * tan(phi') * tan^4(beta)
```

```
p_ult = min(p_us, p_ud)
```

Where:
```
alpha = phi' / 2
beta = 45 + phi' / 2
K_0 = 0.4    (typical for driven piles in sand)
K_a = tan^2(45 - phi'/2)
```

### Curve Shape — Three Segments

**Segment 1 (linear):**
```
p = k * z * y
```

**Segment 2 (parabolic):**
```
p = C * y^(1/n)
```

**Segment 3 (ultimate):**
```
p = p_ult
```

### Initial Modulus of Subgrade Reaction (k)

| phi' (degrees) | k (above water) lb/in^3 | k (below water) lb/in^3 |
|----------------|------------------------|------------------------|
| 25 | 25 | 5 |
| 28 | 28 | 10 |
| 30 | 60 | 25 |
| 32 | 90 | 35 |
| 34 | 115 | 45 |
| 36 | 150 | 60 |
| 38 | 200 | 80 |
| 40 | 300 | 100 |

---

## 7. API RP 2A p-y Curves — Sand

Reference: API RP 2GEO / API RP 2A-WSD

### Ultimate Lateral Resistance

Shallow:
```
p_us = (C_1 * z + C_2 * B) * gamma' * z
```

Deep:
```
p_ud = C_3 * B * gamma' * z
```

```
p_ult = min(p_us, p_ud)
```

**API Coefficients C_1, C_2, C_3:**

| phi' (deg) | C_1 | C_2 | C_3 |
|------------|-----|-----|-----|
| 25 | 1.22 | 2.88 | 12.7 |
| 28 | 1.78 | 3.29 | 20.8 |
| 30 | 2.46 | 3.81 | 31.4 |
| 32 | 3.39 | 4.47 | 47.9 |
| 34 | 4.68 | 5.30 | 73.9 |
| 36 | 6.50 | 6.37 | 115.4 |
| 38 | 9.10 | 7.78 | 182.5 |
| 40 | 12.85 | 9.64 | 292.0 |

### p-y Curve (Hyperbolic Tangent)

**Static:**
```
p = A * p_ult * tanh(k * z * y / (A * p_ult))
```

**Cyclic:**
```
p = 0.9 * p_ult * tanh(k * z * y / (0.9 * p_ult))
```

Where:
```
A = max(0.9, 3.0 - 0.8 * z / B)     (for static loading)
A = 0.9                                (for cyclic loading)
```

---

## 8. API RP 2A p-y Curves — Soft Clay

### Static

```
p = 0.5 * p_ult * (y / y_50)^(1/3)       for y <= 8 * y_50
p = p_ult                                  for y > 8 * y_50
```

### Cyclic (z >= z_r)

```
p = 0.5 * p_ult * (y / y_50)^(1/3)       for y <= 3 * y_50
p = 0.72 * p_ult                           for y > 3 * y_50
```

---

## 8a. Stiff Clay Without Free Water (Welch & Reese, 1975)

Reference: Welch, R.C. and Reese, L.C. (1975)

### Static Loading

Power curve:
```
p = 0.5 * p_ult * (y / y_50)^0.25       for y <= 16 * y_50
p = p_ult                                for y > 16 * y_50
```

Ultimate resistance uses Matlock formulation (Section 4).

### Cyclic Loading

Deflection expanded by cyclic degradation factor:
```
y_c = y_s + y_50 * 9.6 * (p / p_ult)^4 * log10(N)
```

---

## 8b. Modified Stiff Clay (Brown, 2002)

Same 0.25-power curve as Welch & Reese, but with a user-defined initial
stiffness k providing a linear segment at small deflections:

```
p = k * z * y                            for y <= y_A (intersection)
p = 0.5 * p_ult * (y / y_50)^0.25       for y_A < y <= 16 * y_50
p = p_ult                                for y > 16 * y_50
```

---

## 8c. Small-Strain Sand (Hanssen, 2015)

Reference: LPile Technical Manual Section 3.4.4

Hardin-Drnevich degradation overlay on API sand. Uses G_max (maximum
shear modulus) to provide stiffer initial response at small deflections.

### Degradation Model

```
G / G_max = 1 / (1 + |y / y_r|)
```

Reference deflection:
```
y_r = A * p_ult / (4 * G_max)
```

Small-strain resistance:
```
p_small = 4 * G_max * (G / G_max) * y
```

Final curve: `p = max(p_small, p_api)`, capped at `A * p_ult`.

### G_max Estimation

If not measured (e.g., from crosshole/SASW testing):
```
G_max = 1000 * K2 * (sigma_m')^0.5    (psi)
K2 ~ 30 + 2 * (phi - 25)
```

---

## 8d. Liquefied Sand (Rollins et al., 2005)

Reference: Rollins, K.M. et al. (2005)

Concave-upward empirical curve for fully liquefied sand:
```
p = P_d * A * (B_coeff * y)^C
```

Depth-dependent coefficients (z in meters, y in mm):
```
A = 3e-7 * (z + 1)^6.05
B = 2.80 * (z + 1)^0.11
C = 2.85 * (z + 1)^(-0.41)
```

Diameter correction P_d for pile diameter b (meters):
```
P_d = 1.0129 * (b / 0.3)              for b < 0.3 m
P_d = 3.81 * ln(b) + 5.6              for 0.3 <= b <= 2.6 m
P_d = 9.24                             for b > 2.6 m
```

Cap: 15 kN/m for 0.3 m reference pile.

---

## 8e. Liquefied Sand Hybrid (Franke & Rollins, 2013)

Combines Rollins dilative curve with Matlock soft clay using
the residual shear strength of the liquefied soil:

```
p_hybrid(y) = min(p_rollins(y), p_matlock_residual(y))
```

The Matlock residual curve uses:
- c_u = residual undrained shear strength
- epsilon_50 = 0.02
- Cyclic = True

---

## 8f. Weak Rock (Reese, 1997)

Reference: LPile Technical Manual Section 3.8.4

Three-branch model for weak rock (q_ur < ~1000 psi):

**Branch 1 (linear):**
```
p = M_ir * y                            for y <= y_A
```

**Branch 2 (power curve):**
```
p = (p_ur / 2) * (y / y_rm)^0.25       for y_A < y <= 16 * y_rm, p <= p_ur
```

**Branch 3 (ultimate):**
```
p = p_ur                                for y > 16 * y_rm
```

### Parameters

Ultimate resistance:
```
p_ur = alpha_r * q_ur * b * (1 + 1.4 * x_r / b)    for x_r <= 3b
p_ur = 5.2 * alpha_r * q_ur * b                     for x_r > 3b
```

Strength reduction factor (RQD-dependent):
```
alpha_r = 1 - (2/3) * (RQD / 100)
```

Initial modulus:
```
M_ir = k_ir * E_ir
k_ir = 100 + 400 * x_r / (3b)     for x_r <= 3b
k_ir = 500                         for x_r > 3b
```

Strain parameter and intersection point:
```
y_rm = epsilon_rm * b              (epsilon_rm ~ 0.0005)
y_A = (p_ur / (2 * y_rm^0.25 * M_ir))^1.333
```

| Symbol | Description | Typical Range |
|--------|-------------|---------------|
| q_ur | Uniaxial compressive strength | 100 - 1000 psi |
| E_ir | Initial rock mass modulus | 10,000 - 500,000 psi |
| RQD | Rock Quality Designation | 0 - 100% |
| epsilon_rm | Strain factor | 0.00005 - 0.0005 |

---

## 8g. Strong Rock — Vuggy Limestone

Reference: LPile Technical Manual Section 3.8.3

Bilinear p-y curve for strong rock (q_ur >= 1000 psi / 6.9 MPa):

```
p = 2000 * s_u * y                      for y <= 0.0004 * b
p = p_1 + 100 * s_u * (y - 0.0004b)    for y > 0.0004 * b, p <= p_u
```

Where:
```
s_u = q_ur / 2     (shear strength = half UCS)
p_u = b * s_u      (ultimate resistance)
```

Brittle fracture assumed if deflection exceeds 0.0004b.

---

## 8h. Massive Rock (Liang et al., 2009)

Reference: LPile Technical Manual Section 3.9

Hyperbolic p-y curve using Hoek-Brown strength criterion:

```
p = y / (1/K_i + y/p_u)
```

### Hoek-Brown Parameters

```
m_b = m_i * exp((GSI - 100) / (28 - 14*D_r))
s = exp((GSI - 100) / (9 - 3*D_r))
sigma_1 = sigma_3 + sigma_ci * (m_b * sigma_3/sigma_ci + s)^0.5
```

Mohr-Coulomb equivalent:
```
phi' = 90 - arcsin(2*tau / (sigma_1 - sigma_3))
c' = tau - sigma_n * tan(phi')
```

Rock mass modulus:
```
E_m = E_i * exp(GSI / 21.7) / 100
```

| Rock Quality | sigma_ci (psi) | m_i | GSI |
|-------------|---------------|-----|-----|
| Good quality | 21,750 | 25 | 75 |
| Average | 11,600 | 12 | 50 |
| Very poor | 2,900 | 8 | 30 |

---

## 8i. Loess (Johnson et al., 2006)

Reference: LPile Technical Manual Section 3.6

Hyperbolic degradation model for loess soils using CPT data:

### Ultimate Resistance

```
p_u0 = N_CPT * q_c              (N_CPT = 0.409)
p_u = p_u0 * b / (1 + C_N * log|N|)    (C_N = 0.24)
```

Depth reduction: q_c reduced by 50% at surface, linearly increasing
to full value at depth = 2 * b (passive wedge effect).

### Secant Modulus Degradation

```
E_i = p_u / y_ref               (y_ref = 0.117 in)
E_s = E_i / (1 + y'_h)
y'_h = (y / y_ref) * [1 + 0.10 * exp(-y / y_ref)]
p = E_s * y
```

---

## 8j. Cemented c-phi Soil

Reference: LPile Technical Manual Section 3.7

Four-segment p-y curve for soils with both cohesion and friction.

### Ultimate Resistance

Frictional component (same as Reese sand):
```
p_u_phi = min(p_phi_s, p_phi_d)
```

Cohesive component:
```
p_cs = (3 + gamma'/c * x + J/b * x) * c * b       (J = 0.5)
p_cd = 9 * c * b
p_c = min(p_cs, p_cd)
```

### Curve Construction

```
y_u = 3b/80,    p_u = A * p_u_phi
y_m = b/60,     p_m = B * p_u_phi + p_uc
```

**4 segments:** initial (p = kx * y), parabolic (p = S * y^(1/n)),
straight line (p_m to p_u), residual (p = A * p_u_phi, frictional only).

Initial stiffness:
```
k = k_c + k_phi    (cemented sand)
k = k_phi           (non-cemented silt)
```

---

## 8k. Piedmont Residual Soil (Simpson & Brown, 2006)

Modified stiff clay approach for residual soils of the Piedmont
geologic province:

```
p = 0.5 * p_ult * (y / y_50)^0.25    (with 0.85 reduction on p_ult)
```

Uses epsilon_50 = 0.007 (default for residual soils) and optional
initial k stiffness.

---

## 8l. Elastic Subgrade

Linear elastic p-y spring (no ultimate cap):

```
p = k * z * y
```

Useful for preliminary analysis or very stiff soils where nonlinear
response is not expected within the working load range.

---

## 8m. Available p-y Models Summary

| # | Model | Function | Curve Shape | Key Inputs |
|---|-------|----------|-------------|------------|
| 1 | Soft Clay (Matlock) | `py_matlock_soft_clay` | 1/3-power | c_u, epsilon_50, J |
| 2 | API Soft Clay w/ User J | `py_api_soft_clay` | 1/3-power | c_u, epsilon_50, J |
| 3 | Stiff Clay w/ Free Water | `py_stiff_clay_free_water` | 5-segment | c_u, epsilon_50, k |
| 4 | Stiff Clay w/o Free Water | `py_stiff_clay_no_free_water` | 1/4-power | c_u, epsilon_50 |
| 5 | Modified Stiff Clay | `py_mod_stiff_clay` | Linear + 1/4-power | c_u, epsilon_50, k |
| 6 | Sand (Reese) | `py_reese_sand` | 4-point | phi, k |
| 7 | API Sand | `py_api_sand` | tanh | phi |
| 8 | Small-Strain Sand | `py_small_strain_sand` | Hardin-Drnevich + API | phi, G_max |
| 9 | Liquefied Sand (Rollins) | `py_liquefied_sand_rollins` | Concave-up | depth only |
| 10 | Liquefied Sand Hybrid | `py_liquefied_sand_hybrid` | min(Rollins, Matlock) | c_u_residual |
| 11 | Weak Rock (Reese) | `py_weak_rock` | 3-branch | q_ur, E_ir, RQD |
| 12 | Strong Rock (Vuggy) | `py_strong_rock` | Bilinear | q_ur |
| 13 | Massive Rock | `py_massive_rock` | Hyperbolic | sigma_ci, m_i, GSI |
| 14 | Piedmont Residual | `py_piedmont_residual` | Modified 1/4-power | c_u, epsilon_50 |
| 15 | Loess | `py_loess` | Hyperbolic degrad. | q_c or c_u |
| 16 | Cemented c-phi | `py_silt_cemented` | 4-segment | phi, c, k |
| 17 | Elastic Subgrade | `py_elastic_subgrade` | Linear | k |
| 18 | User-Input | (placeholder) | User-defined | y, p data |

---

## 9. Broms Method — Simplified Lateral Capacity

### Short Pile in Cohesionless Soil (Free Head)

```
H_ult = 0.5 * K_p * gamma * B * L^2 / (1 + e/L)
```

Where:
```
K_p = tan^2(45 + phi'/2)
e = eccentricity (height of lateral load above ground)
L = embedded length
```

### Short Pile in Cohesive Soil (Free Head)

```
H_ult = (9 * c_u * B * L) / (2 * (1 + 1.5 * e / L))
```

> Assumes 1.5B of zero resistance at top for Broms cohesive method.

### Long Pile — Governed by Pile Yield Moment

**Cohesionless soil (free head):**
```
H_ult = M_yield / (e + 0.67 * f)
```

Where f is the depth to maximum moment:
```
f = (H_ult / (K_p * gamma * B))^0.5
```

**Cohesive soil (free head):**
```
H_ult = M_yield / (e + 1.5 * B + 0.5 * f)
```

Where:
```
f = H_ult / (9 * c_u * B)
```

---

## 10. Lateral Deflection — Elastic Solutions

### Fixed-Head Pile (Constant Modulus)

```
y_0 = H / (k_h * B * R) * F_yH
```

### Free-Head Pile (Constant Modulus)

```
y_0 = H / (k_h * B * R) * F_yH + M / (k_h * B * R^2) * F_yM
```

**Nondimensional coefficients** depend on L/R ratio (available in Matlock & Reese charts).

### Maximum Bending Moment (Free-Head, Single Lateral Load)

For long piles:
```
M_max approximately = H * T * F_m
```

Where F_m is typically 0.6 to 0.77 depending on head fixity and soil type.

---

## 11. Solar Pile Lateral Load Considerations

### Typical Loading

| Load Case | Lateral Load Range | Moment at Ground | Notes |
|-----------|-------------------|-------------------|-------|
| Wind (operating) | 500 - 2000 lbs | Load * lever arm | Tracker dependent |
| Wind (stow) | 1000 - 4000 lbs | Load * lever arm | Maximum stow condition |
| Wind (extreme / survival) | 2000 - 8000 lbs | Load * lever arm | 3-sec gust |
| Seismic | Varies | Base shear * height | Pseudo-static |

### Moment Application

Lateral loads on solar piles typically act above ground level:

```
e = distance from ground surface to point of load application (typically 2 - 8 ft)
M_ground = H * e
```

The ground-line moment is critical for solar piles and often governs design.

### Deflection Limits

| Condition | Typical Limit |
|-----------|--------------|
| Serviceability (operational) | 0.5 - 1.0 in at ground line |
| Tracker tolerance | Per manufacturer (often 0.5 - 0.75 in) |
| Ultimate / strength check | Structural capacity governs |

### Depth of Fixity (Simplified)

Approximate depth to point of zero deflection:

**Cohesionless soil:**
```
D_f = 1.8 * T = 1.8 * (EI / n_h)^(1/5)
```

**Cohesive soil:**
```
D_f = 1.4 * R = 1.4 * (EI / k_h)^(1/4)
```

> The depth of fixity is used for simplified structural analysis of the above-ground pile as a cantilever fixed at depth D_f.
