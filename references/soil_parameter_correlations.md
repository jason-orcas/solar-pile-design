# Soil Parameter Correlations

## 1. SPT N-Value Corrections

### Energy Correction to N_60

```
N_60 = N_field * (E_r / 60)
```

Where E_r = hammer energy ratio (%).

| Hammer Type | Country | E_r (%) | Correction (E_r/60) |
|------------|---------|---------|---------------------|
| Safety hammer | USA | 60 | 1.00 |
| Donut hammer | USA | 45 | 0.75 |
| Automatic trip | USA | 80-100 | 1.33-1.67 |
| Donut hammer | Japan | 67 | 1.12 |

### Overburden Correction (N1)_60

```
(N1)_60 = C_N * N_60
```

**Liao & Whitman (1986):**
```
C_N = (Pa / sigma'_v)^0.5     <= 2.0
```

**Skempton (1986):**
```
C_N = 2 / (1 + sigma'_v / Pa)
```

Where Pa = atmospheric pressure = 2116 psf = 1 atm = 100 kPa.

### Full SPT Correction

```
(N1)_60 = N_field * C_N * C_E * C_B * C_R * C_S
```

| Factor | Symbol | Condition | Value |
|--------|--------|-----------|-------|
| Energy | C_E | Safety hammer | 1.00 |
| | | Automatic | 1.10-1.60 |
| Borehole diameter | C_B | 2.5 - 4.5 in | 1.00 |
| | | 6 in | 1.05 |
| | | 8 in | 1.15 |
| Rod length | C_R | < 10 ft | 0.75 |
| | | 10 - 13 ft | 0.85 |
| | | 13 - 20 ft | 0.95 |
| | | > 20 ft | 1.00 |
| Sampler | C_S | Standard split spoon | 1.00 |
| | | Without liner | 1.10-1.30 |

---

## 2. SPT N-Value to Relative Density

### Meyerhof (1957)

```
D_r (%) = 21 * [(N1)_60]^0.5
```

### Skempton (1986)

| (N1)_60 | Relative Density D_r (%) | Description |
|---------|-------------------------|-------------|
| 0 - 3 | 0 - 15 | Very loose |
| 3 - 8 | 15 - 35 | Loose |
| 8 - 25 | 35 - 65 | Medium dense |
| 25 - 42 | 65 - 85 | Dense |
| 42 - 58 | 85 - 100 | Very dense |

---

## 3. SPT N-Value to Friction Angle (phi')

### Peck, Hanson, Thornburn (1974)

```
phi' = 27.1 + 0.3 * (N1)_60 - 0.00054 * [(N1)_60]^2
```

### Hatanaka & Uchida (1996)

```
phi' = (20 * (N1)_60)^0.5 + 20       (degrees)
```

### Wolff (1989)

```
phi' = 27.1 + 0.3 * N_60 - 0.00054 * N_60^2
```

### Tabulated Correlation (Das)

| (N1)_60 | Soil Description | phi' (degrees) |
|---------|-----------------|----------------|
| < 4 | Very loose | < 28 |
| 4 - 10 | Loose | 28 - 30 |
| 10 - 30 | Medium dense | 30 - 36 |
| 30 - 50 | Dense | 36 - 41 |
| > 50 | Very dense | 41 - 45 |

---

## 4. SPT N-Value to Undrained Shear Strength (c_u)

### Terzaghi & Peck

```
c_u (psf) = N_60 * 125            (approximate)
c_u (kPa) = N_60 * 6.0            (approximate)
```

### Hara et al. (1971)

```
c_u (kPa) = 29 * N_60^0.72
```

### Tabulated Correlation

| N_60 | Consistency | c_u (psf) | c_u (kPa) |
|------|------------|-----------|-----------|
| < 2 | Very soft | < 250 | < 12 |
| 2 - 4 | Soft | 250 - 500 | 12 - 25 |
| 4 - 8 | Medium | 500 - 1000 | 25 - 50 |
| 8 - 15 | Stiff | 1000 - 2000 | 50 - 100 |
| 15 - 30 | Very stiff | 2000 - 4000 | 100 - 200 |
| > 30 | Hard | > 4000 | > 200 |

---

## 5. SPT N-Value to Soil Modulus (E_s)

### Cohesionless Soils

**Webb (1969) / D'Appolonia (1970):**
```
E_s (tsf) = 5 * (N_60 + 15)                for normally consolidated sand
E_s (tsf) = 10 * (N_60 + 5)                for preloaded sand
E_s (kPa) = 500 * (N_60 + 15)              (NC, SI)
```

**Bowles (1996) — General:**
```
E_s (kPa) = 7000 * N_60^0.5                for sand
E_s (kPa) = 6000 * N_60                    for gravelly sand
E_s (kPa) = 320 * (N_60 + 15)              for clayey sand
```

### Cohesive Soils

```
E_s = (200 to 500) * c_u      for normally consolidated clay
E_s = (750 to 1200) * c_u     for overconsolidated clay
```

---

## 6. Unit Weight Correlations

### Cohesionless Soils (from SPT)

| N_60 | Description | gamma_dry (pcf) | gamma_sat (pcf) | gamma (kN/m^3) |
|------|------------|----------------|-----------------|----------------|
| < 4 | Very loose | 70 - 90 | 100 - 115 | 14 - 16 |
| 4 - 10 | Loose | 90 - 100 | 110 - 120 | 16 - 17.5 |
| 10 - 30 | Medium dense | 100 - 115 | 115 - 130 | 17.5 - 19 |
| 30 - 50 | Dense | 110 - 125 | 125 - 140 | 19 - 20.5 |
| > 50 | Very dense | 120 - 135 | 130 - 145 | 20.5 - 22 |

### Cohesive Soils (from SPT)

| N_60 | Description | gamma (pcf) | gamma (kN/m^3) |
|------|------------|------------|----------------|
| < 2 | Very soft | 90 - 105 | 14 - 16.5 |
| 2 - 4 | Soft | 100 - 115 | 15.5 - 18 |
| 4 - 8 | Medium | 105 - 120 | 16.5 - 19 |
| 8 - 15 | Stiff | 110 - 130 | 17.5 - 20 |
| 15 - 30 | Very stiff | 115 - 135 | 18 - 21 |
| > 30 | Hard | 120 - 140 | 19 - 22 |

### Common Soil Unit Weights (Reference)

| Soil Type | gamma_moist (pcf) | gamma_sat (pcf) | gamma' (submerged) (pcf) |
|-----------|------------------|-----------------|-------------------------|
| Loose sand | 95 - 110 | 115 - 125 | 52 - 63 |
| Dense sand | 110 - 130 | 125 - 140 | 63 - 78 |
| Soft clay | 95 - 110 | 100 - 120 | 38 - 58 |
| Stiff clay | 110 - 130 | 115 - 135 | 53 - 73 |
| Gravel | 110 - 130 | 125 - 145 | 63 - 83 |
| Silt | 90 - 110 | 105 - 125 | 43 - 63 |
| Organic soil | 60 - 90 | 80 - 105 | 18 - 43 |

> gamma' = gamma_sat - gamma_w, where gamma_w = 62.4 pcf = 9.81 kN/m^3

---

## 7. CPT Correlations

### CPT to SPT Approximation

```
N_60 = q_c / (C_f * Pa)
```

**Robertson & Campanella (1983):**

| Soil Type | q_c / N_60 | D_50 (mm) |
|-----------|-----------|-----------|
| Clay | 1 - 2.5 | - |
| Silty clay | 2 - 4 | - |
| Sandy silt | 3 - 5 | 0.02 - 0.05 |
| Silty sand | 4 - 6 | 0.05 - 0.2 |
| Sand | 5 - 8 | 0.2 - 2.0 |
| Gravelly sand | 6 - 10 | > 2.0 |

### CPT to Friction Angle

**Robertson & Campanella (1983):**
```
phi' = arctan(0.1 + 0.38 * log10(q_c / sigma'_v))
```

### CPT to Undrained Shear Strength

```
c_u = (q_c - sigma_v) / N_kt
```

Where N_kt = cone factor, typically 10 to 20 (average ~15).

---

## 8. USCS Soil Classification Reference

| Symbol | Description | Typical phi' (deg) | Typical c_u (psf) | Permeability |
|--------|-------------|--------------------|--------------------|--------------|
| GW | Well-graded gravel | 33 - 40 | - | High |
| GP | Poorly graded gravel | 32 - 38 | - | High |
| GM | Silty gravel | 30 - 36 | - | Medium |
| GC | Clayey gravel | 28 - 34 | - | Low |
| SW | Well-graded sand | 33 - 40 | - | Medium-High |
| SP | Poorly graded sand | 30 - 36 | - | Medium-High |
| SM | Silty sand | 28 - 34 | - | Low-Medium |
| SC | Clayey sand | 25 - 32 | - | Low |
| ML | Low plasticity silt | 24 - 32 | 200 - 1000 | Low |
| CL | Low plasticity clay | 18 - 28 | 300 - 2000 | Very Low |
| OL | Organic silt/clay | 20 - 25 | 200 - 800 | Very Low |
| MH | High plasticity silt | 20 - 28 | 300 - 1500 | Very Low |
| CH | High plasticity clay | 15 - 25 | 500 - 4000 | Very Low |
| OH | Organic clay | 15 - 22 | 200 - 1000 | Very Low |
| Pt | Peat | - | < 500 | Medium |

---

## 9. Coefficient of Earth Pressure at Rest (K_0)

### Normally Consolidated Soils

**Jaky (1944):**
```
K_0 = 1 - sin(phi')
```

### Overconsolidated Soils

**Mayne & Kulhawy (1982):**
```
K_0 = (1 - sin(phi')) * OCR^(sin(phi'))
```

| Soil Condition | K_0 Range |
|---------------|-----------|
| NC sand | 0.35 - 0.50 |
| NC clay | 0.50 - 0.70 |
| OC sand (OCR = 2-4) | 0.50 - 1.00 |
| OC clay (OCR = 2-8) | 0.60 - 2.50 |

---

## 10. Poisson's Ratio

| Soil Type | Poisson's Ratio (nu) |
|-----------|---------------------|
| Saturated clay (undrained) | 0.45 - 0.50 |
| Clay (drained) | 0.20 - 0.40 |
| Sandy clay | 0.20 - 0.35 |
| Silt | 0.30 - 0.40 |
| Sand (loose) | 0.20 - 0.35 |
| Sand (dense) | 0.30 - 0.40 |
| Gravel | 0.15 - 0.35 |
| Rock | 0.10 - 0.30 |

---

## 11. Frost Depth Reference (Approximate)

| Region (US) | Frost Depth (in) | Frost Depth (ft) |
|-------------|------------------|-------------------|
| Southern states | 0 - 12 | 0 - 1.0 |
| Mid-Atlantic | 24 - 36 | 2.0 - 3.0 |
| Midwest | 36 - 48 | 3.0 - 4.0 |
| Northern states | 48 - 72 | 4.0 - 6.0 |
| Alaska | 72 - 120+ | 6.0 - 10.0+ |

> Always verify with local building codes. Solar pile minimum embedment typically must extend 12 in below frost depth.

---

## 12. Corrosion Rates for Steel Piles

### FHWA / AASHTO Guidance

| Environment | Corrosion Rate (mils/year) | Corrosion Rate (mm/year) |
|------------|--------------------------|-------------------------|
| Atmospheric zone | 1.0 - 2.0 | 0.025 - 0.050 |
| Splash zone | 3.0 - 5.0 | 0.075 - 0.125 |
| Tidal zone | 1.0 - 3.0 | 0.025 - 0.075 |
| Submerged (seawater) | 2.0 - 4.0 | 0.050 - 0.100 |
| Buried (disturbed soil) | 0.5 - 2.0 | 0.013 - 0.050 |
| Buried (undisturbed) | 0.5 - 1.0 | 0.013 - 0.025 |
| Fill / aggressive soil | 2.0 - 4.0 | 0.050 - 0.100 |

### Sacrificial Steel Thickness for Design Life

```
t_loss = corrosion_rate * design_life
t_structural = t_nominal - t_loss
```

For solar piles (typical 25-35 year design life):
```
t_loss = 1.5 mil/yr * 35 yr = 52.5 mils = 0.053 in    (buried, moderate)
```

> Galvanized coatings (G90 or higher) significantly reduce loss rates. Verify with site-specific soil resistivity and pH data.
