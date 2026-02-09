# Pile Group Efficiency & Interaction

## 1. General Framework

### Group Capacity

```
Q_group = eta * n * Q_single
```

| Symbol | Description |
|--------|-------------|
| Q_group | Capacity of the pile group |
| eta | Group efficiency factor (0 to 1+) |
| n | Number of piles in the group |
| Q_single | Capacity of a single isolated pile |

### Governing Check

The group capacity is the **lesser** of:
1. Sum of individual pile capacities (modified by efficiency factor)
2. Block failure capacity of the group

```
Q_group = min(eta * n * Q_single, Q_block)
```

---

## 2. Efficiency Factors — Axial Loading

### 2a. Converse-Labarre Formula

Most widely used for driven piles in cohesionless soils.

```
eta = 1 - theta * [(n_1 - 1) * n_2 + (n_2 - 1) * n_1] / (90 * n_1 * n_2)
```

Where:
```
theta = arctan(d / s)     (degrees)
```

| Symbol | Description |
|--------|-------------|
| n_1 | Number of piles in a row |
| n_2 | Number of rows |
| d | Pile diameter or width |
| s | Center-to-center pile spacing |

**Example:** 2x2 group, W6 piles (d = 6 in), spacing = 36 in:
```
theta = arctan(6/36) = 9.46 degrees
eta = 1 - 9.46 * [(2-1)*2 + (2-1)*2] / (90 * 2 * 2)
eta = 1 - 9.46 * 4 / 360 = 0.895
```

### 2b. Feld's Rule (Simplified)

Each pile in the group is reduced by 1/16 for each adjacent pile.

| Configuration | Efficiency |
|--------------|-----------|
| Single pile | 1.00 |
| 2-pile group | 0.94 |
| 3-pile row | 0.88 - 0.91 |
| 2x2 group | 0.81 |
| 3x3 group | 0.67 - 0.72 |

### 2c. AASHTO / FHWA Guidance

**Cohesionless soils (driven piles):**

| Spacing (s/d) | Efficiency (eta) |
|---------------|-----------------|
| < 3.0 | 0.65 - 0.80 |
| 3.0 | 0.70 - 0.85 |
| 4.0 | 0.80 - 0.90 |
| 5.0 | 0.85 - 0.95 |
| 6.0 | 0.90 - 1.00 |
| >= 8.0 | 1.00 |

> For driven piles in loose to medium sand, compaction effects during installation can result in eta > 1.0 at spacings > 3d.

**Cohesive soils:**

| Spacing (s/d) | Efficiency (eta) | Notes |
|---------------|-----------------|-------|
| < 3.0 | Not recommended | |
| 3.0 | 0.65 - 0.70 | Check block failure |
| 4.0 | 0.70 - 0.80 | |
| 5.0 | 0.80 - 0.90 | |
| 6.0 | 0.85 - 0.95 | |
| >= 8.0 | 1.00 | |

---

## 3. Block Failure Analysis

### Cohesive Soils — Axial Compression

The block failure treats the pile group as a single large foundation:

```
Q_block = 2 * (B_g + L_g) * D * c_u_avg + B_g * L_g * N_c * c_u_base
```

| Symbol | Description |
|--------|-------------|
| B_g | Width of the pile group block = (n_1 - 1) * s + d |
| L_g | Length of the pile group block = (n_2 - 1) * s + d |
| D | Embedded depth of piles |
| c_u_avg | Average undrained shear strength along the block sides |
| c_u_base | Undrained shear strength at the base of the block |
| N_c | Bearing capacity factor for the block |

**N_c for Block Failure:**
```
N_c = 5.0 * [1 + 0.2 * (B_g / L_g)] * [1 + 0.2 * (D / B_g)]    <= 9.0
```

### Cohesionless Soils — Block Failure (Rarely Governs)

```
Q_block = 2 * (B_g + L_g) * K_s * sigma'_v_avg * tan(delta) * D + B_g * L_g * sigma'_v_base * N_q
```

> Block failure in sand rarely governs at spacings >= 3d.

---

## 4. Lateral Load — Group Effects

### 4a. p-Multiplier Method (Brown et al., NCHRP 461)

The p-y curves for piles in a group are reduced by a factor f_m:

```
p_group(y) = f_m * p_single(y)
```

**Recommended p-multipliers (AASHTO/FHWA):**

| Row Position | s/d = 3 | s/d = 4 | s/d = 5 | s/d = 6 | s/d >= 8 |
|-------------|---------|---------|---------|---------|----------|
| Lead row (front) | 0.80 | 0.85 | 0.90 | 0.95 | 1.00 |
| 2nd row (trailing) | 0.40 | 0.55 | 0.65 | 0.75 | 1.00 |
| 3rd row | 0.30 | 0.45 | 0.55 | 0.65 | 1.00 |
| 4th+ row | 0.30 | 0.40 | 0.50 | 0.60 | 1.00 |

> **Lead row** = row facing the direction of lateral loading.
> **Trailing rows** = rows behind the lead row (in the "shadow" zone).

### 4b. Group Lateral Efficiency (Overall)

```
eta_lateral = (sum of all f_m values) / n
```

**Example:** 3x3 group at s/d = 3:
- Row 1 (lead): 3 piles * 0.80 = 2.40
- Row 2: 3 piles * 0.40 = 1.20
- Row 3: 3 piles * 0.30 = 0.90
- Total: 4.50 / 9 = eta_lateral = 0.50

### 4c. Shadowing Effect Explanation

Piles in trailing rows push into soil already displaced by front-row piles. This reduces the effective soil resistance (softer p-y curves). The effect:

- Is most severe at close spacings (s/d < 5)
- Diminishes with spacing (negligible at s/d >= 8)
- Affects trailing rows more than front rows
- Is direction-dependent (changes with load reversal)

For **cyclic/reversing loads** (common in solar applications under wind):
- Both directions must be checked
- The average of lead and trailing multipliers may be used for reversing loads
- Or conservatively, use the trailing-row multiplier for all rows

---

## 5. Load Distribution in Groups

### Rigid Cap Assumption

If the pile cap is rigid, loads distribute based on geometry:

**Axial load on pile i:**
```
P_i = V / n + M_x * y_i / sum(y_j^2) + M_y * x_i / sum(x_j^2)
```

| Symbol | Description |
|--------|-------------|
| V | Total vertical load |
| M_x, M_y | Moments about x and y axes |
| x_i, y_i | Coordinates of pile i from group centroid |
| n | Number of piles |

### Flexible Cap

For flexible caps, load distribution depends on relative stiffness of the cap, piles, and soil. Requires structural analysis or simplified tributary area methods.

---

## 6. Settlement of Pile Groups

### Cohesionless Soils — Meyerhof (1976)

```
S_group = S_single * sqrt(B_g / d)
```

### Vesic (1977)

```
S_group / S_single = sqrt(B_g / d)
```

### Cohesive Soils — Equivalent Raft Method

The group is replaced by an equivalent raft at 2/3 * D depth:

```
B_raft = B_g
L_raft = L_g
Depth of raft = 2/3 * D
```

Settlement computed using standard consolidation theory for the equivalent raft.

---

## 7. Solar Pile Group Configurations

### Typical Tracker Pile Layouts

| Tracker Type | Piles per Row | Spacing Along Tracker (ft) | Row Spacing (ft) |
|-------------|--------------|--------------------------|------------------|
| Single-axis (1P) | 10 - 30 | 8 - 15 | 15 - 25 (N-S) |
| Single-axis (2P) | 10 - 30 | 8 - 15 | 15 - 25 |
| Fixed tilt | 2 - 6 per table | 6 - 12 | 12 - 20 |

### Group Effects for Solar Arrays

For typical solar pile spacings:
- **Along-tracker spacing** (8-15 ft, s/d > 15): Group effects are **negligible** for individual pile capacity
- **Cross-row spacing** (15-25 ft): Group effects are **negligible**
- **Foundation pairs** (e.g., pier-type with 2-4 piles at s/d = 3-6): **Group effects apply** — use multipliers above

### When Group Effects Matter for Solar

| Condition | Group Effects? | Action |
|-----------|---------------|--------|
| Standard single-pile tracker posts | No | Analyze as individual piles |
| Pier foundations (2-4 pile clusters) | Yes | Apply Converse-Labarre + p-multipliers |
| Equipment pads (inverter, transformer) | Yes | Full group analysis |
| Substation foundations | Yes | Full group analysis |
| Closely spaced helical piles | Yes (if s/d < 6) | Check helix interaction |

---

## 8. Minimum Spacing Requirements

| Code / Reference | Minimum Spacing |
|-----------------|----------------|
| AASHTO | 3.0 * d (center-to-center) |
| IBC | 3.0 * d |
| ACI 318 (drilled shafts) | 3.0 * d |
| Helical piles (ICC-ES) | 3.0 * D_helix (largest helix diameter) |
| Practical minimum (driven) | 2.5 * d (with justification) |

> For solar pier foundations, maintaining s/d >= 5 eliminates most group reduction concerns.
