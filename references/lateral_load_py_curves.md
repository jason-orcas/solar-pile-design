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
