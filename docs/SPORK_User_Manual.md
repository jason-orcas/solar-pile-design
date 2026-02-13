# SPORK User Manual

**Solar Pile Optimization & Report Kit**

Version 1.0 | February 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Project Setup (Page 01)](#2-project-setup)
3. [Soil Profile (Page 02)](#3-soil-profile)
4. [Pile Properties (Page 03)](#4-pile-properties)
5. [Loading (Page 04)](#5-loading)
6. [Pile Optimization (Page 05)](#6-pile-optimization)
7. [Axial Capacity (Page 06)](#7-axial-capacity)
8. [Lateral Analysis (Page 07)](#8-lateral-analysis)
9. [Group Analysis (Page 08)](#9-group-analysis)
10. [FEM Analysis (Page 09)](#10-fem-analysis)
11. [Structural Check (Page 11)](#11-structural-check)
12. [Liquefaction Screening (Page 12)](#12-liquefaction-screening)
13. [Installation QC (Page 13)](#13-installation-qc)
14. [Export Report (Page 14)](#14-export-report)
15. [Limitations and Assumptions](#15-limitations-and-assumptions)
16. [References](#16-references)

---

## 1. Introduction

SPORK (Solar Pile Optimization & Report Kit) is a web-based engineering tool for designing and analyzing driven, drilled, and helical steel pile foundations for utility-scale solar projects. It performs axial capacity, lateral load (p-y curve), pile group, finite element, structural capacity, liquefaction screening, and installation QC analyses, then exports a professional PDF report.

### Intended Audience

Practicing civil, structural, and geotechnical engineers performing pile foundation design for solar tracker and fixed-tilt racking systems.

### Recommended Workflow

Work through pages sequentially. Each page builds on data entered in prior pages:

1. **Project Setup** -- Enter project info, optionally import a TOPL document
2. **Soil Profile** -- Define soil layers, SPT data, water table, frost depth
3. **Pile Properties** -- Select steel section, embedment, installation method
4. **Loading** -- Enter per-pile loads, review load combinations
5. **Pile Optimization** *(optional)* -- Sweep sections and embedments to find the lightest passing design
6. **Axial Capacity** -- Compute compression and tension capacity
7. **Lateral Analysis** -- Run p-y curve analysis, Broms check, deflection checks
8. **Group Analysis** *(if applicable)* -- Evaluate pile group efficiency
9. **FEM Analysis** *(optional)* -- BNWF finite element model for combined loading
10. **Structural Check** -- AISC 360 combined axial + bending interaction
11. **Liquefaction Screening** *(if seismic zone)* -- SPT-based liquefaction assessment
12. **Installation QC** -- Dynamic formula or torque correlation acceptance criteria
13. **Export Report** -- Generate and download a PDF summary

---

## 2. Project Setup

*Page 01: Project Setup*

### Project Information

| Field | Description |
|-------|-------------|
| **Project Name** | Descriptive name for the project. Used in the PDF report header and JSON filename. |
| **Site Location** | City, state, or geographic description. For record-keeping and report identification. |
| **Project Notes** | Free-text field for design basis notes, assumptions, or references. Included in the PDF report. |

### TOPL Import

SPORK can auto-populate loading data from manufacturer Top-of-Pile-Load (TOPL) documents. TOPL documents specify the unfactored loads that the tracker or racking system delivers to each pile.

| Field | Description |
|-------|-------------|
| **Manufacturer** | Select the tracker manufacturer: ATI, Nevados, or Nextpower. This determines the parser used. |
| **Upload TOPL Document** | Upload the manufacturer's TOPL file. ATI and Nevados use PDF format; Nextpower uses XLSX. |
| **Select Column / Post Type** | After parsing, select which pile position (interior post, motor post, end post, etc.) to import loads for. Different positions have different load magnitudes. |

After parsing, SPORK displays the extracted loads in an editable table. You can adjust any value before clicking **Apply TOPL Loads to Project**, which populates the Loading page (Page 04).

### Save and Load Projects

| Feature | Description |
|---------|-------------|
| **Download Project File** | Exports all current session data (soil layers, pile properties, loads, analysis settings) to a JSON file. |
| **Upload Project File** | Restores a previously saved project from a JSON file. All session state is overwritten with the file contents. |

Project files are backward-compatible: older files missing newer fields (such as p-y model selections) will load correctly with default values.

---

## 3. Soil Profile

*Page 02: Soil Profile*

This page defines the subsurface conditions used in all downstream analyses. At minimum, each layer requires a soil type and SPT N-value.

### Water Table

| Field | Description |
|-------|-------------|
| **Water table present?** | Checkbox. If checked, a depth input appears. |
| **Water table depth (ft)** | Depth below ground surface to the groundwater level. Affects effective stress calculations, buoyant unit weights, and liquefaction screening. |

When the water table is above a layer's midpoint, that layer is flagged as submerged and its effective unit weight is reduced by the unit weight of water (62.4 pcf).

### Layer Inputs

Each layer is defined by the following fields:

#### Row 1: Depth and Classification

| Field | Units | Description |
|-------|-------|-------------|
| **Top Depth** | ft | Depth from ground surface to the top of this layer. |
| **Bottom Depth** | ft | Depth from ground surface to the bottom of this layer. Must be greater than top depth. |
| **Soil Type** | -- | Classification of the layer: Sand, Clay, Silt, Gravel, or Organic. See the Soil Type section below for how this affects calculations. |

#### Row 2: p-y Curve Model and Description

| Field | Description |
|-------|-------------|
| **p-y Curve Model** | Selects the lateral soil response model for this layer. Default is "Auto." See the p-y Curve Model section below for all 18 options. |
| **Description** | Optional free-text label (e.g., "Brown silty sand, medium dense"). Appears in the layer table and on the soil profile visualization. |

#### Row 3: Soil Parameters

| Field | Units | Default | Description |
|-------|-------|---------|-------------|
| **SPT N-value** | blows/ft | 15 | Raw Standard Penetration Test blow count from the field boring log. This is the primary input for all auto-estimated parameters. |
| **gamma** | pcf | 0 (auto) | Total unit weight. Enter 0 to auto-estimate from SPT N-value and soil type. |
| **phi** | degrees | 0 (auto) | Drained friction angle. Enter 0 to auto-estimate from N-value. Only meaningful for granular soils (Sand, Gravel, Silt). Clay layers use phi = 0 (undrained). |
| **c_u** | psf | 0 (auto) | Undrained shear strength. Enter 0 to auto-estimate from N-value. Only meaningful for cohesive soils (Clay, Silt, Organic). Sand/Gravel layers return c_u = 0. |

### How "Auto" (0) Estimation Works

When a parameter is left at zero, SPORK estimates it from the SPT N-value using widely accepted correlations:

**Unit weight (gamma):**
Estimated from N_60 using Terzaghi & Peck (1967) ranges, differentiated by soil type and whether the layer is submerged.

**Friction angle (phi):**
- Sand/Gravel: Hatanaka & Uchida (1996): phi = sqrt(20 * N_60) + 20, capped at 45 degrees
- Silt: phi = 24 + 0.25 * N_60, capped at 34 degrees
- Clay: Returns 0 (undrained, phi = 0 assumption)

**Undrained shear strength (c_u):**
- Clay/Silt/Organic: c_u = 125 * N_60 (psf), after Terzaghi & Peck
- Sand/Gravel: Returns 0 (no undrained strength)

### SPT Corrections

SPORK automatically applies the following corrections to the raw N-value:

| Correction | Symbol | Default | Description |
|------------|--------|---------|-------------|
| Energy ratio | C_E | 60% | Hammer energy correction. N_60 = N_spt * (ER / 60) |
| Borehole diameter | C_B | 1.0 | Correction for borehole size |
| Rod length | C_R | 1.0 | Correction for short rod lengths |
| Sampler correction | C_S | 1.0 | Correction for liner presence |

The displayed values in the layer table:
- **N_60** = N_spt * C_E * C_B * C_R * C_S
- **(N1)_60** = N_60 * C_N, where C_N is the overburden correction factor per Liao & Whitman (1986)

### Soil Type -- What It Controls

The Soil Type classification (Sand, Clay, Silt, Gravel, Organic) is used throughout SPORK in the following ways:

| Downstream Use | How Soil Type Affects It |
|----------------|--------------------------|
| **Auto p-y model** | Clay/Silt/Organic -> Matlock Soft Clay; Sand/Gravel -> API Sand |
| **Unit weight estimation** | Different lookup tables for granular vs. cohesive |
| **Friction angle** | Returns 0 for Clay (undrained); estimates from N for Sand/Silt/Gravel |
| **Undrained shear strength** | Returns 0 for Sand/Gravel; estimates from N for Clay/Silt/Organic |
| **Axial capacity method** | Alpha method (total stress) for cohesive; Beta method (effective stress) for granular |
| **Broms lateral check** | Cohesive vs. cohesionless formulation |
| **Subgrade reaction modulus** | Different k_h lookup tables for sand vs. clay |
| **Liquefaction screening** | Only evaluates granular layers (Sand, Gravel) below the water table |
| **Profile visualization** | Color-coded by soil type |

Soil Type is independent of the p-y Curve Model. You must always select a Soil Type for each layer, even if you override the p-y model.

### p-y Curve Model

The p-y Curve Model controls the lateral soil resistance model used during lateral load analysis (Pages 07 and 09). The default "Auto" mode selects the model based on Soil Type. Alternatively, you can select a specific model from the 18 LPile v2022 formulations.

#### Auto Mode (Default)

When set to "Auto":
- Clay, Silt, Organic layers -> **Matlock Soft Clay** (Matlock, 1970)
- Sand, Gravel layers -> **API Sand** (O'Neill & Murchison, 1983)

This is appropriate for most routine solar pile designs.

#### Available Models

| Model | Typical Soil | Key Reference |
|-------|-------------|---------------|
| Soft Clay (Matlock) | Soft to medium clay | Matlock (1970) |
| API Soft Clay w/ User J | Soft clay with explicit J factor | API RP 2A |
| Stiff Clay w/ Free Water (Reese) | Stiff clay above water table or with free water | Reese, Cox & Koop (1975) |
| Stiff Clay w/o Free Water (Reese) | Stiff clay below water table, no free water | Welch & Reese (1972) |
| Modified Stiff Clay w/o Free Water | Modified stiff clay with initial modulus | Brown (2002) |
| Sand (Reese) | Clean sand | Reese, Cox & Koop (1974) |
| API Sand (O'Neill) | Sand (API/industry standard) | O'Neill & Murchison (1983) |
| Small Strain Sand | Sand with small-strain stiffness | Hanssen (2015), Hardin & Drnevich (1972) |
| Liquefied Sand (Rollins) | Fully liquefied sand | Rollins et al. (2005) |
| Liquefied Sand Hybrid | Partially liquefied sand | Franke & Rollins (2013) |
| Weak Rock (Reese) | Weak/weathered rock | Reese (1997) |
| Strong Rock (Vuggy) | Strong rock / vuggy limestone | LPile (Ensoft) |
| Massive Rock | Competent rock mass | Liang et al. (2009), Hoek-Brown |
| Piedmont Residual Soil | Residual soils (SE United States) | Simpson & Brown (2006) |
| Loess | Wind-deposited silt (loess) | Johnson et al. (2006) |
| Silt (Cemented c-phi) | Cemented silt with both c and phi | LPile Section 3.7 |
| Elastic Subgrade | Linear spring (no ultimate cap) | Winkler model |
| User-Input p-y | User-defined curve data | -- |

#### When to Change from Auto

Select a specific model when:

- Your geotechnical report recommends a particular p-y formulation
- The soil is stiff clay (the Matlock soft clay model may significantly underpredict stiffness)
- You are designing in rock or cemented soils
- You have small-strain shear modulus data (G_max) and want a more accurate sand model
- You are evaluating post-liquefaction pile performance
- You want to match results with LPile or similar commercial software

#### Model-Specific Parameters

When you select a non-Auto model, additional parameter fields may appear. These fields are model-specific:

| Parameter | Units | Models That Use It | Description |
|-----------|-------|--------------------|-------------|
| epsilon_50 | -- | All clay models | Strain at 50% of ultimate soil resistance. 0 = auto from c_u. Typical range: 0.004 (stiff) to 0.02 (soft). |
| J | -- | API Soft Clay w/ User J | Matlock empirical constant. 0.25 for shallow, 0.5 for deep (Matlock, 1970). |
| k (lb/in^3) | lb/in^3 | Stiff Clay w/ Free Water, Sand (Reese), API Sand, Silt (Cemented) | Initial modulus of subgrade reaction. 0 = auto from soil type. |
| q_u (psf) | psf | Weak Rock, Strong Rock | Unconfined compressive strength of rock. |
| E_ir (psi) | psi | Weak Rock | Initial modulus of the rock mass. |
| RQD (%) | % | Weak Rock | Rock Quality Designation, used for strength reduction. |
| k_rm | -- | Weak Rock | Strain wedge factor for the weak rock model. |
| sigma_ci (psi) | psi | Massive Rock | Intact rock uniaxial compressive strength (Hoek-Brown criterion). |
| m_i | -- | Massive Rock | Hoek-Brown material constant (depends on rock type; typical 5-35). |
| GSI | -- | Massive Rock | Geological Strength Index (0-100). Describes rock mass quality. |
| E_rock (psi) | psi | Massive Rock | Rock mass deformation modulus. |
| G_max (psi) | psi | Small Strain Sand | Maximum (small-strain) shear modulus. From resonant column, crosshole, or correlation. |
| Poisson's ratio | -- | Small Strain Sand, Massive Rock | Soil or rock Poisson's ratio. |
| Void ratio | -- | Small Strain Sand | Soil void ratio. |
| C_u (uniformity) | -- | Small Strain Sand | Coefficient of uniformity (D60 / D10). Not to be confused with undrained shear strength c_u. |

### Frost Depth Check

Located at the bottom of the Soil Profile page. Verifies that pile embedment extends below the frost line per IBC 1809.5: "The bottom of footings shall extend below the frost line unless otherwise protected."

SPORK requires embedment to exceed the frost depth plus 12 inches.

| Field | Description |
|-------|-------------|
| **Frost depth method** | Choose from: Regional lookup, Stefan equation, or Manual entry. |
| **US Region** *(Regional lookup)* | Approximate frost depths by US region (Southern states, Mid-Atlantic, Midwest, Northern states, Alaska). |
| **Freezing Index** *(Stefan equation)* | Cumulative degree-days of freezing. Used in the modified Berggren (Stefan) equation: d = C * sqrt(F_I), where C depends on soil type. |
| **Frost depth (in)** *(Manual)* | Direct entry of the local frost depth in inches. |

**Outputs:**
- Frost depth (in and ft)
- Minimum required embedment (ft) = frost depth + 12 in
- Pass/Fail against the current pile embedment from Page 03
- Estimated adfreeze uplift force (if pile perimeter is available)

---

## 4. Pile Properties

*Page 03: Pile Properties*

### Section Selection

| Field | Description |
|-------|-------------|
| **Steel Section** | Dropdown of all available W-shapes and C-shapes in the database. Common solar pile sections include W6x7, W6x9, W6x12, W6x15, W8x10, W8x13, W8x18, etc. |

After selecting a section, SPORK displays all section properties: depth, flange width, area, weight (plf), moment of inertia (Ix, Iy), section modulus (Sx, Sy), plastic modulus (Zx, Zy), perimeter, and tip area.

### Installation and Geometry

| Field | Units | Default | Description |
|-------|-------|---------|-------------|
| **Embedment Depth** | ft | 10.0 | Length of pile below ground surface. This is the primary design variable. |
| **Installation Method** | -- | driven | How the pile is installed: driven, drilled, or helical. Affects axial capacity reduction factors and Installation QC page behavior. |
| **Pile Head Condition** | -- | free | Boundary condition at the ground surface for lateral analysis: "free" (rotation allowed, typical for solar) or "fixed" (rotation restrained). |
| **Bending Axis** | -- | strong | Which axis resists lateral load: "strong" (bending about x-axis, load on flanges) or "weak" (bending about y-axis, load on web). Solar trackers typically load the strong axis. |

**Pile head condition guidance:**
- **Free head**: Use for most solar pile applications. The pile is embedded in the ground with the tracker torque tube connection above grade providing minimal rotational restraint.
- **Fixed head**: Use when a rigid pile cap or concrete grade beam provides full moment fixity at the ground surface.

### Corrosion Allowance

Optional analysis that reduces section properties to account for steel loss over the design life.

| Field | Description |
|-------|-------------|
| **Enable corrosion analysis** | Checkbox. When enabled, downstream analyses use the corroded section properties. |
| **Design Life (years)** | Project service life. Typical: 25-35 years for solar. |
| **Environment** | Exposure condition: Atmospheric (rural), Atmospheric (industrial), Buried (undisturbed), Buried (disturbed), Immersed (fresh water), or Immersed (salt water). Each has a different corrosion rate in mils/year. |
| **Coating** | Protective coating: None, Hot-dip galvanized, Epoxy, or Zinc-rich primer. Coatings apply a reduction factor to the base corrosion rate. |

SPORK computes the total thickness loss per side over the design life, then reduces flange and web thicknesses to produce a corroded section. A comparison table shows the nominal vs. corroded section properties and percent reductions.

### Computed Design Properties

Displayed at the bottom of the page using the active section (nominal or corroded):

| Property | Description |
|----------|-------------|
| **EI** | Flexural rigidity (lb-in^2) for the selected bending axis. |
| **M_y** | Yield moment (kip-in). The moment at which the extreme fiber reaches F_y. |
| **M_p** | Plastic moment (kip-in). The moment when the full cross section has yielded. |
| **F_y** | Steel yield strength (default: 50 ksi for A572 Gr 50). |

---

## 5. Loading

*Page 04: Loading*

### Design Method

| Option | Description |
|--------|-------------|
| **LRFD** | Load and Resistance Factor Design per ASCE 7-22 Section 2.3. Uses factored loads and resistance factors. This is the recommended method. |
| **ASD** | Allowable Stress Design per ASCE 7-22 Section 2.4. Uses unfactored loads with safety factors on resistance. |
| **Both** | Generates both LRFD and ASD combination tables for comparison. |

### Per-Pile Loads

All loads are entered as unfactored (service-level) values per pile. SPORK generates the factored load combinations automatically.

#### Gravity Loads

| Field | Units | Default | Description |
|-------|-------|---------|-------------|
| **Dead load** | lbs | 400 | Self-weight of the tracker/racking, modules, and connections tributary to this pile. Acts as compression (downward). |
| **Live load** | lbs | 0 | Maintenance or access live load per pile. Typically zero for ground-mount solar. |
| **Snow load** | lbs | 0 | Snow load per pile. Enter the total snow force on the tributary area. |

#### Wind Loads

| Field | Units | Default | Description |
|-------|-------|---------|-------------|
| **Wind downward** | lbs | 0 | Wind-induced downward force per pile. Occurs when wind pushes down on the tracker modules (e.g., tilt angle creates downforce). |
| **Wind uplift** | lbs | 1500 | Wind-induced upward force per pile. Typically the largest load on a solar pile. This force acts to pull the pile out of the ground. |
| **Wind lateral** | lbs | 1500 | Horizontal wind force per pile. This is the lateral load that the pile must resist through soil-structure interaction. |
| **Wind moment at ground** | ft-lbs | 0 | Direct moment applied at the ground surface from wind. Enter 0 if the moment is entirely from the lateral load acting at the lever arm height (SPORK computes H * lever_arm automatically in the analysis). |

#### Seismic and Geometry

| Field | Units | Default | Description |
|-------|-------|---------|-------------|
| **Seismic lateral** | lbs | 0 | Horizontal seismic force per pile. |
| **Seismic vertical** | lbs | 0 | Vertical seismic force per pile (can be up or down). |
| **Seismic moment** | ft-lbs | 0 | Seismic moment at ground per pile. |
| **Lateral load height above ground** | ft | 4.0 | The height above the ground surface where the lateral load (wind or seismic) is applied. Also called the "lever arm" or "eccentricity." The moment at ground = H * lever_arm. Typical values for solar trackers: 3-6 ft. |

### Load Combination Tables

SPORK generates all applicable ASCE 7-22 load combinations. The table displays each combination with:

- **V_comp**: Factored vertical compression (lbs)
- **V_tens**: Factored vertical tension/uplift (lbs)
- **H_lat**: Factored lateral load (lbs)
- **M_ground**: Factored moment at the ground surface (ft-lbs)

**Key combinations for solar piles** (LRFD):

| Combination | Typical Governing Condition |
|-------------|---------------------------|
| LC1: 1.4D | Maximum gravity (rarely governs) |
| LC4a: 1.2D + 1.0W(down) + L + 0.5S | Maximum compression with wind |
| LC4b: 1.2D + 1.0W(up) + L + 0.5S | Uplift case |
| LC6: 0.9D + 1.0W | **Usually governs for solar** -- minimum gravity with full wind uplift and lateral |

LC6 (0.9D + 1.0W) almost always governs solar pile design because dead loads are very light and wind uplift/lateral forces are large relative to gravity.

### Optional Calculators

Three expandable calculators are provided for convenience:

**Wind Pressure Calculator (ASCE 7):** Computes velocity pressure q_z = 0.00256 * K_z * K_zt * K_d * K_e * V^2 (psf). Inputs: basic wind speed V, exposure coefficient K_z, topographic factor K_zt, directionality factor K_d, and elevation factor K_e.

**Seismic C_s Calculator:** Computes base shear coefficient C_s = S_DS / R per ASCE 7 simplified method. Inputs: spectral acceleration S_DS and response modification factor R.

**Snow Load Calculator:** Computes flat-roof snow load p_f = 0.7 * C_e * C_t * I_s * p_g per ASCE 7 Chapter 7. Inputs: ground snow load p_g, exposure factor C_e, thermal factor C_t, and importance factor I_s.

---

## 6. Pile Optimization

*Page 05: Pile Design Optimization*

This page sweeps across multiple steel sections and embedment depths to find the lightest pile design that passes all capacity checks.

**Prerequisites:** Soil layers (Page 02) and loads (Page 04) must be defined.

### Optimization Settings

| Field | Description |
|-------|-------------|
| **Section Family** | Which group of sections to include in the sweep (e.g., "W6", "W8", "W6+W8"). |
| **Min Embedment (ft)** | Starting embedment depth for the sweep. |
| **Max Embedment (ft)** | Ending embedment depth for the sweep. |
| **Embedment Step (ft)** | Increment between embedment depths. |
| **Deflection Limit (in)** | Maximum allowable ground-line deflection for the lateral analysis check. |

### What Is Checked

For each section-embedment combination, SPORK runs:

1. **Axial compression check** -- Ultimate compression capacity vs. factored demand (DCR <= 1.0)
2. **Axial tension check** -- Ultimate tension capacity vs. factored uplift (DCR <= 1.0)
3. **Lateral structural check** -- Maximum bending moment vs. yield moment (DCR <= 1.0)
4. **Lateral deflection check** -- Ground-line deflection vs. the specified limit

A combination passes only if all four checks pass.

### Outputs

- **Pass/Fail Heatmap:** A matrix of sections vs. embedment depths. Green = pass, red = fail. The optimal design (lightest passing combination) is annotated.
- **Detailed Results Table:** Every combination with its DCR values and deflection.
- **Apply Optimal Design:** Button to set the optimal section and embedment as the active design for downstream pages.

---

## 7. Axial Capacity

*Page 06: Axial Capacity Analysis*

### Analysis Settings

| Field | Default | Description |
|-------|---------|-------------|
| **Capacity Method** | auto | The method used to compute skin friction. "auto" selects Alpha for cohesive layers and Beta for granular layers. You can force a single method: alpha, beta, or meyerhof. |
| **FS Compression** | 2.5 | Factor of safety for allowable compression capacity (ASD). |
| **FS Tension** | 3.0 | Factor of safety for allowable tension capacity (ASD). Tension FS is higher because tension failure is more sudden and skin friction in uplift may be lower. |

### Calculation Methods

**Alpha Method (Total Stress)** -- Used for cohesive soils (Clay, Silt, Organic):

    Q_s = sum(alpha * c_u * perimeter * delta_L)

Where alpha is the adhesion factor from API RP 2A. Alpha decreases as c_u increases (alpha = 1.0 for soft clay, ~0.5 for stiff clay, ~0.3 for hard clay).

Reference: API RP 2A; Tomlinson (1957).

**Beta Method (Effective Stress)** -- Used for granular soils (Sand, Gravel):

    Q_s = sum(beta * sigma_v' * perimeter * delta_L)

Where beta = K_s * tan(delta). K_s is the lateral earth pressure coefficient (depends on OCR and installation method) and delta is the soil-pile interface friction angle (typically 0.7 * phi for smooth steel).

Reference: Burland (1973); Meyerhof (1976).

**Meyerhof SPT Method** -- Empirical method directly from SPT N-values:

    Q_s = sum(2 * N_60 * perimeter * delta_L)  (for sand, in psf)
    Q_b = 400 * N_60 * A_tip  (for sand, in psf)

Reference: Meyerhof (1976).

**End Bearing:**

    Q_b = q_b * A_tip

Where q_b depends on the soil type and method: for sand, q_b = N_q * sigma_v' (Meyerhof bearing capacity factor); for clay, q_b = 9 * c_u.

**Tension Capacity:**

    Q_ult_tension = 0.75 * Q_s  (skin friction only, reduced)

A 0.75 reduction factor is applied to skin friction for tension because the stress state reversal can reduce interface friction. End bearing does not contribute to tension capacity.

### LRFD Resistance Factors

| Condition | phi | Reference |
|-----------|-----|-----------|
| Driven piles, clay (alpha) | 0.35 | AASHTO LRFD |
| Driven piles, sand (beta/Nordlund) | 0.45 | AASHTO LRFD |
| Driven piles, end bearing | 0.40-0.50 | AASHTO LRFD |
| With PDA/CAPWAP verification | 0.65 | AASHTO LRFD |
| With static load test | 0.75-0.80 | AASHTO LRFD |
| Helical piles | 0.40-0.60 | ICC-ES |

### Outputs

- **Q_s:** Total skin friction (lbs)
- **Q_b:** End bearing (lbs)
- **Q_ult (Compression):** Q_s + Q_b
- **Q_allow (Compression):** Q_ult / FS_compression
- **Q_ult (Tension):** 0.75 * Q_s
- **Q_allow (Tension):** Q_ult_tension / FS_tension
- **phi*R_n (LRFD):** Factored resistance for both compression and tension
- **Layer-by-layer breakdown:** Table showing each layer's contribution to skin friction
- **Cumulative skin friction vs. depth plot**

---

## 8. Lateral Analysis

*Page 07: Lateral Load Analysis*

### Load Inputs

| Field | Units | Description |
|-------|-------|-------------|
| **Lateral load H** | lbs | Horizontal load applied at the ground surface. Defaults to wind lateral from Page 04. |
| **Moment at ground** | ft-lbs | Applied moment at ground. Defaults to H * lever_arm. |
| **Cyclic loading** | checkbox | If checked, p-y curves are degraded for cyclic loading. Matlock soft clay uses 0.72 * p_ult (static) for cyclic. Reese sand uses different coefficients. |

### FDM Lateral Analysis

The primary analysis uses a finite difference method (FDM) to solve the beam-on-elastic-foundation equation:

    EI * d^4y/dz^4 + p(y, z) = 0

The pile is discretized into elements. At each depth, p-y curves define the nonlinear relationship between lateral displacement (y) and soil resistance (p). The solver iterates using secant stiffness until convergence (typically 20-50 iterations).

**Outputs:**

| Result | Units | Description |
|--------|-------|-------------|
| **Ground Deflection** | in | Lateral displacement at the ground surface. The primary serviceability criterion. |
| **Max Moment** | ft-lbs | Maximum bending moment along the pile length. Occurs below ground. |
| **Depth of M_max** | ft | Depth at which the maximum moment occurs. |
| **Depth of Zero Deflection** | ft | Depth at which the pile deflection crosses zero. Below this depth, the pile is effectively "anchored." |
| **Structural DCR** | -- | M_max / M_y. Must be <= 1.0 to avoid yielding. |

**Plots:**
- Deflection, moment, shear, and soil reaction vs. depth (4-panel plot)
- p-y curves at selected depths (showing the nonlinear soil response)

### Broms Simplified Check

A closed-form method for estimating ultimate lateral capacity. Uses the top layer only.

- **Cohesive soils:** Broms (1964a) -- assumes uniform c_u, evaluates short-pile (soil failure) and long-pile (structural failure) modes.
- **Cohesionless soils:** Broms (1964b) -- assumes linear increase of passive pressure with depth (K_p * gamma * z).

Outputs: H_ult (ultimate lateral capacity), H_allow (= H_ult / 2.5), and governing failure mode (short pile vs. long pile).

### Service Load Deflection Check

Verifies that the pile head deflection under unfactored (service-level) loads stays within an acceptable limit.

| Field | Default | Description |
|-------|---------|-------------|
| **Wind ASD factor** | 0.6 | Reduction factor on wind lateral load for service conditions. Per ASCE 7 ASD, wind is factored by 0.6. |
| **Service lateral load** | 0.6 * wind_lateral | The actual lateral load used for the service check. |
| **Deflection limit** | 0.50 in | Maximum allowable ground-line deflection. Typical limits: 0.25-1.0 in for solar depending on tracker manufacturer requirements. |

### Minimum Embedment for Lateral Stability

Uses Broms method with bisection to find the shortest embedment at which the pile's ultimate lateral capacity meets the required demand.

| Field | Default | Description |
|-------|---------|-------------|
| **Factor of safety for lateral** | 2.0 | Safety factor applied to the required lateral load. |
| **H required** | H_applied * FS | The lateral capacity that must be achieved. |

---

## 9. Group Analysis

*Page 08: Pile Group Analysis*

Evaluates how closely spaced piles interact and reduce each other's capacity.

**Prerequisites:** Soil layers (Page 02). Axial capacity analysis (Page 06) is recommended for accurate group capacity.

### Group Configuration

| Field | Units | Default | Description |
|-------|-------|---------|-------------|
| **Number of rows** | -- | 1 | Rows of piles in the direction of lateral loading. |
| **Piles per row** | -- | 1 | Number of piles in each row, perpendicular to lateral loading. |
| **Center-to-center spacing** | in | 36 | Distance between pile centers. Must be >= 6 in. |

The s/d ratio (spacing divided by pile width) is computed and displayed. AASHTO recommends s/d >= 3. At s/d >= 8, group effects are negligible.

### Axial Group Efficiency

**Converse-Labarre Formula:**

    eta = 1 - theta * [(n1 - 1)*n2 + (n2 - 1)*n1] / (90 * n1 * n2)

where theta = arctan(d/s) in degrees.

Reference: Converse (1962); widely used in AASHTO and FHWA practice.

**Block Failure:** For cohesive soils, the group is also checked as a single large "block" foundation. The block capacity is the lesser of perimeter shear + base bearing. The governing group capacity is the minimum of the individual (efficiency-reduced) capacity and the block failure capacity.

### Lateral Group Effects -- p-Multipliers

When piles are closely spaced, "shadowing" reduces the lateral resistance of trailing piles. SPORK assigns p-multipliers (f_m) by row position per Brown et al. (2001):

| Row Position | s/d = 3 | s/d = 5 | s/d >= 8 |
|-------------|---------|---------|----------|
| Lead row | 0.80 | 0.90 | 1.00 |
| Second row | 0.40 | 0.60 | 1.00 |
| Third+ row | 0.30 | 0.50 | 1.00 |

The average lateral group efficiency = mean of all f_m values.

---

## 10. FEM Analysis

*Page 09: FEM Analysis (BNWF)*

Advanced finite element model for combined axial and lateral loading using a Beam on Nonlinear Winkler Foundation (BNWF) approach.

### Analysis Configuration

| Field | Description |
|-------|-------------|
| **Analysis type** | Static (single load step), Pushover Lateral (incremental lateral), or Pushover Axial (incremental axial). |
| **Solver** | Auto (uses OpenSeesPy if installed, otherwise Python), Python (always available), or OpenSeesPy (requires installation). |

### Applied Loads

| Field | Units | Description |
|-------|-------|-------------|
| **Axial load V** | lbs | Axial compression (positive) applied at the pile head. |
| **Lateral load H** | lbs | Horizontal load at the pile head. |
| **Moment at ground M** | ft-lbs | Applied moment at the ground surface. |

### Options

| Field | Default | Description |
|-------|---------|-------------|
| **Include P-delta effects** | Yes | Second-order effects from axial load acting through lateral displacement. Important for long, slender piles under combined loading. |
| **Cyclic loading** | From Page 07 | Degrades p-y curves for cyclic loading conditions. |
| **Pile type** | From Page 03 | Affects t-z curve selection (driven vs. drilled). |
| **Head condition** | From Page 03 | Free or fixed head boundary. |

### Pushover Settings (if pushover analysis)

| Field | Description |
|-------|-------------|
| **Number of load steps** | How many increments to apply between 0 and the maximum load. |
| **Max load multiplier** | Maximum load as a multiple of the input load. For example, 3.0 means the pushover goes up to 3x the input load. |

### Advanced (OpenSeesPy Only)

| Field | Description |
|-------|-------------|
| **Fiber section** | Use fiber discretization for nonlinear moment-curvature behavior instead of elastic EI. Captures gradual yielding. |
| **Eigenvalue analysis** | Compute natural frequencies and mode shapes of the pile-soil system. |
| **Number of modes** | Number of eigenvalues to extract (1-10). |

### Outputs

- **Lateral and axial deflections at ground**
- **Maximum moment and its depth**
- **P_critical (buckling load)** if P-delta is enabled
- **Pile head stiffness matrix** (3x3: axial, lateral, rotational)
- **Depth profiles** (6 plots): lateral deflection, axial deflection, moment, shear, axial force, lateral soil reaction
- **Pushover curve** (load vs. displacement at ground) if pushover analysis
- **Natural frequencies** if eigenvalue analysis
- **t-z curves** (skin friction transfer curves at selected depths)
- **q-z curve** (tip resistance transfer curve)
- **p-y curves** (lateral soil resistance at selected depths)

### Spring Models

The BNWF model uses three types of nonlinear springs:

- **p-y springs (lateral):** Same models as Page 07. Represent lateral soil resistance.
- **t-z springs (axial skin friction):** Represent load transfer along the pile shaft. Use API (1993) formulations: for clay, t_max = alpha * c_u; for sand, t_max = beta * sigma_v'.
- **q-z spring (tip bearing):** Represents end bearing. Uses API (1993) tip resistance curve: hyperbolic shape reaching q_ult at approximately 10% of pile diameter displacement.

---

## 11. Structural Check

*Page 11: AISC 360 Structural Capacity Check*

Evaluates the combined axial compression and bending interaction per AISC 360-22 Chapter H.

### Unbraced Length and Buckling Parameters

| Field | Units | Default | Description |
|-------|-------|---------|-------------|
| **Above-grade height** | ft | 4.0 | Height from ground surface to the point of lateral load application. This is the unsupported length above ground. |
| **Effective length factor K** | -- | 2.1 | Column buckling effective length factor. K = 2.1 is typical for a cantilever with partial base fixity (common for piles). K = 2.0 is an ideal cantilever. |

**Depth of Fixity (D_f):** Automatically computed from the top soil layer's subgrade reaction modulus. This represents the equivalent fixed point below ground for structural buckling analysis.

- For sand: D_f = 1.8 * (EI / n_h)^0.2, where n_h = coefficient of subgrade reaction
- For clay: D_f = 1.4 * (EI / k_h)^0.25

Reference: Davisson & Robinson (1965).

**Unbraced Length:** L_b = above-grade height + depth of fixity.

### Applied Loads

Two input modes:

- **From analysis results:** Auto-populates M_ux from the lateral analysis (Page 07) and P_u from load combinations. Edit as needed.
- **Manual entry:** Enter P_u, M_ux, and M_uy directly.

| Field | Units | Description |
|-------|-------|-------------|
| **P_u** | lbs | Factored axial compression. |
| **M_ux** | kip-in | Factored strong-axis bending moment. |
| **M_uy** | kip-in | Factored weak-axis bending moment. Typically 0 for single-axis lateral loading. |

### AISC H1-1 Interaction Check

SPORK evaluates the combined axial-flexural interaction using AISC 360-22 Equations H1-1a and H1-1b:

**When P_u / (phi_c * P_n) >= 0.2 (Eq. H1-1a):**

    P_u/(phi_c*P_n) + (8/9)*[M_ux/(phi_b*M_nx) + M_uy/(phi_b*M_ny)] <= 1.0

**When P_u / (phi_c * P_n) < 0.2 (Eq. H1-1b):**

    P_u/(2*phi_c*P_n) + M_ux/(phi_b*M_nx) + M_uy/(phi_b*M_ny) <= 1.0

Where:
- phi_c = 0.90 (compression)
- phi_b = 0.90 (flexure)
- P_n = F_cr * A_g (nominal compression capacity, based on flexural buckling with KL/r)
- M_nx = F_y * Z_x (nominal strong-axis moment capacity)
- M_ny = F_y * Z_y (nominal weak-axis moment capacity)

Reference: AISC 360-22, Chapter H.

### Outputs

- **Unity Ratio:** The governing interaction value. Must be <= 1.0 to pass.
- **Equation Used:** H1-1a or H1-1b (depends on axial ratio).
- **P_u / phi_c * P_n:** Axial demand-to-capacity ratio.
- **KL/r:** Governing slenderness ratio.
- **Interaction Diagram:** Plot of the H1-1a/H1-1b envelope with the demand point marked.
- **Detailed breakdown** of compression and flexural capacities.

---

## 12. Liquefaction Screening

*Page 12: Liquefaction Screening*

SPT-based simplified procedure per Boulanger & Idriss (2014) for evaluating whether sandy layers are susceptible to liquefaction during a design earthquake.

### Seismic Parameters

| Field | Units | Default | Description |
|-------|-------|---------|-------------|
| **PGA, a_max** | g | 0.2 | Peak ground acceleration at the site. Typically taken as SDS / 2.5 for the design earthquake, or from a site-specific seismic hazard analysis. |
| **Earthquake magnitude M_w** | -- | 7.5 | Moment magnitude of the design earthquake. Affects the magnitude scaling factor (MSF). |
| **Default fines content** | % | 15 | Percent passing the No. 200 sieve. Used to adjust the clean-sand CRR curve for fines. Higher fines content generally increases liquefaction resistance. |
| **Maximum screening depth** | ft | 65 | Depth below which liquefaction is not evaluated (typically 65-80 ft for the simplified procedure). |

### Methodology

For each granular soil layer below the water table:

1. **Compute CSR** (Cyclic Stress Ratio):

       CSR = 0.65 * (sigma_v / sigma_v') * (a_max / g) * r_d / MSF

   where r_d is the stress reduction factor (depth-dependent) and MSF is the magnitude scaling factor.

2. **Correct N-value:** Compute (N1)_60cs (overburden-corrected, energy-corrected, fines-adjusted blow count).

3. **Compute CRR** (Cyclic Resistance Ratio) from the Boulanger & Idriss (2014) CRR curve:

       CRR = exp[(N1)_60cs/14.1 + ((N1)_60cs/126)^2 - ((N1)_60cs/23.6)^3 + ((N1)_60cs/25.4)^4 - 2.8]

4. **Factor of Safety:**

       FS_liq = CRR / CSR

   FS < 1.0: Liquefiable. FS 1.0-1.3: Marginal. FS > 1.3: Non-liquefiable.

Reference: Boulanger & Idriss (2014), "CPT and SPT Based Liquefaction Triggering Procedures."

### Outputs

- **Summary banner:** Overall assessment (liquefiable layers found, marginal, or all safe)
- **Layer results table:** Depth, soil type, N_SPT, (N1)_60, (N1)_60cs, CSR, CRR, FS, and status for each evaluated layer
- **FS vs. depth plot:** Factor of safety profile with threshold lines at FS = 1.0 and 1.3

Cohesive layers and layers above the water table are reported as "N/A" (not susceptible).

---

## 13. Installation QC

*Page 13: Installation QC*

Provides acceptance criteria to verify that piles are achieving the required capacity during installation.

### Driven Piles -- Dynamic Formulas

When the installation method is "driven" (set on Page 03), three dynamic pile driving formulas are evaluated:

| Field | Units | Description |
|-------|-------|-------------|
| **Ram weight** | lbs | Weight of the hammer ram. |
| **Drop height** | ft | Height the ram falls before striking the pile. |
| **Set per blow** | in | Pile penetration per hammer blow, measured over the last 10 blows of driving. |

**Methods:**

| Formula | FS | Description |
|---------|-----|-------------|
| **ENR (Engineering News Record)** | 6.0 | R_u = (W_r * h * 12) / (s + c). Historically conservative. Not recommended for final design but widely used as a field check. |
| **Gates (1957)** | 3.0 | R_u = a * sqrt(E_h) * (b - log(s)). Empirical formula with better statistical correlation than ENR. |
| **FHWA Modified Gates** | 3.0 | R_u = 1.75 * sqrt(E_h) * log(10*N_b) - 100. **Generally considered the most reliable** of the three formulas. Recommended by FHWA for preliminary capacity assessment. |

Reference: FHWA HI-97-013; Hannigan et al. (2016).

### Helical Piles -- Torque Correlation

When the installation method is "helical," the page shows the torque-capacity correlation method.

| Field | Units | Description |
|-------|-------|-------------|
| **Shaft size** | -- | Helical pile shaft size (determines K_t). Options include standard round shaft and square shaft sizes. |
| **Installation torque** | ft-lbs | Measured installation torque at the final depth. |
| **Factor of safety** | -- | Applied to the torque-predicted ultimate capacity. Typical: 2.0. |

**Method:**

    Q_ult = K_t * T

Where K_t is the empirical torque correlation factor (1/ft) that depends on shaft size, and T is the installation torque (ft-lbs).

Reference: Hoyt & Clemence (1989); ICC-ES AC358.

---

## 14. Export Report

*Page 14: Export PDF Report*

Generates a professional PDF summarizing all analyses performed in the session.

### Analysis Status

Before generating the report, SPORK displays which analyses have been completed and which were skipped. At minimum, a soil profile and pile section must be defined.

### Report Settings

| Field | Description |
|-------|-------------|
| **Project Number** | Project identification number for the report header. |
| **Engineer of Record** | Name of the responsible engineer. |
| **Report Date** | Date printed on the report cover. |
| **Above-grade pile length** | Pile reveal height for the configuration diagram. |

### Design Limits

| Field | Default | Description |
|-------|---------|-------------|
| **Top Deflection Limit** | 4.0 in | Maximum allowable deflection at the pile top (above grade). |
| **Grade Deflection Limit** | 1.0 in | Maximum allowable deflection at the ground surface. |
| **Bottom Deflection Limit** | 0.1 in | Maximum allowable deflection at the pile tip. |

### Report Contents

The PDF includes all completed analyses, organized into sections:

1. Project information and design basis
2. Soil profile summary and parameters
3. Pile section properties (nominal and corroded if applicable)
4. TOPL import summary (if used)
5. Load combinations table
6. Optimization results (if run)
7. Axial capacity analysis
8. Lateral analysis results and p-y curves
9. Service deflection check
10. Minimum embedment check
11. BNWF FEM results (if run)
12. Pile group analysis (if run)
13. AISC structural check
14. Frost depth check
15. Liquefaction screening (if run)
16. Installation QC criteria

---

## 15. Limitations and Assumptions

### General

- SPORK is a design aid and does not replace engineering judgment. All results should be reviewed by a licensed professional engineer before use in construction.
- SPORK does not produce stamped or sealed design documents.
- All analyses use US customary units (lbs, ft, in, psf, psi, ksi).

### Soil Modeling

- Soil layers are assumed horizontal and of uniform properties within each layer.
- SPT-based correlations for gamma, phi, and c_u are approximate. Site-specific laboratory or field data should be used where available.
- The p-y curve approach models soil as independent springs at each depth (Winkler assumption). It does not capture soil continuity or arching effects between depths.
- Auto-estimated parameters use widely accepted but generalized correlations. Actual soil behavior can vary significantly from these estimates.

### Structural

- Steel sections are assumed to be A572 Grade 50 (F_y = 50 ksi) unless modified.
- Corrosion analysis assumes uniform thickness loss on both sides of flanges and the web.
- The AISC H1-1 check assumes compact sections (no local buckling check).

### Lateral Analysis

- The FDM solver assumes small deflections. For very large deflections, the secant stiffness approach may not capture geometric nonlinearity adequately; use the BNWF FEM analysis (Page 09) with P-delta effects for those cases.
- Cyclic degradation is applied using simplified reduction factors (Matlock 0.72 for soft clay). More rigorous cyclic degradation models are not included.
- The Broms method uses only the top layer for capacity estimation. It is a simplified check and may not be accurate for layered profiles.

### Axial Analysis

- No negative skin friction (downdrag) is computed.
- No setup or relaxation effects are modeled (capacity changes after installation).
- End bearing is based on the layer at the pile tip. Punching through a thin bearing layer into weaker soil is not checked automatically.

### Group Analysis

- The Converse-Labarre formula is an empirical approximation. It may not be appropriate for all group geometries.
- Block failure is only checked for groups with cohesive soil layers.
- p-multipliers are interpolated from published values (Brown et al., 2001) for limited spacing ratios.

### Liquefaction

- The simplified procedure (Boulanger & Idriss, 2014) is a screening tool. It uses magnitude-weighted cyclic stress ratios and empirical CRR curves. Site-specific analysis (effective stress, ground response) may be warranted for high-risk sites.
- Only SPT-based triggering is implemented. CPT-based methods are not included.

### Installation QC

- Dynamic formulas (ENR, Gates, FHWA Modified Gates) are empirical and provide approximate capacity estimates. They should be supplemented with PDA/CAPWAP or static load tests for critical applications.
- Helical torque correlation (K_t method) assumes the empirical relationship holds for the site soils. Verify with load testing.

---

## 16. References

### Design Standards

- AISC. (2022). *Specification for Structural Steel Buildings* (ANSI/AISC 360-22). American Institute of Steel Construction, Chicago, IL.

- ASCE. (2022). *Minimum Design Loads and Associated Criteria for Buildings and Other Structures* (ASCE/SEI 7-22). American Society of Civil Engineers, Reston, VA.

- ICC. (2021). *International Building Code* (IBC 2021). International Code Council, Washington, DC.

- AASHTO. (2020). *LRFD Bridge Design Specifications* (9th Ed.). American Association of State Highway and Transportation Officials, Washington, DC.

- API. (2014). *Recommended Practice for Planning, Designing and Constructing Fixed Offshore Platforms -- Working Stress Design* (API RP 2A-WSD, 22nd Ed.). American Petroleum Institute, Washington, DC.

### Textbooks

- Das, B.M. (2011). *Principles of Foundation Engineering* (7th Ed.). Cengage Learning, Stamford, CT.

- Tomlinson, M.J. (2004). *Pile Design and Construction Practice* (4th Ed.). E & FN Spon, London.

- Rajapakse, R. (2016). *Pile Design and Construction Rules of Thumb* (2nd Ed.). Butterworth-Heinemann.

### Axial Capacity

- Tomlinson, M.J. (1957). "The adhesion of piles driven in clay soils." *Proceedings, 4th International Conference on Soil Mechanics and Foundation Engineering*, Vol. 2, pp. 66-71.

- Burland, J.B. (1973). "Shaft friction of piles in clay -- A simple fundamental approach." *Ground Engineering*, 6(3), 30-42.

- Meyerhof, G.G. (1976). "Bearing capacity and settlement of pile foundations." *Journal of the Geotechnical Engineering Division*, ASCE, 102(GT3), 197-228.

### Lateral Load Analysis -- p-y Curves

- Matlock, H. (1970). "Correlations for design of laterally loaded piles in soft clay." *Proceedings, 2nd Offshore Technology Conference*, Houston, TX, OTC 1204, pp. 577-594.

- Reese, L.C., Cox, W.R., and Koop, F.D. (1974). "Analysis of laterally loaded piles in sand." *Proceedings, 6th Offshore Technology Conference*, Houston, TX, OTC 2080, pp. 473-483.

- Reese, L.C., Cox, W.R., and Koop, F.D. (1975). "Field testing and analysis of laterally loaded piles in stiff clay." *Proceedings, 7th Offshore Technology Conference*, Houston, TX, OTC 2312, pp. 671-690.

- Welch, R.C. and Reese, L.C. (1972). "Laterally loaded behavior of drilled shafts." *Research Report 3-5-65-89*, Center for Highway Research, University of Texas at Austin.

- O'Neill, M.W. and Murchison, J.M. (1983). "An evaluation of p-y relationships in sands." *Report to the American Petroleum Institute*, PRAC 82-41-1, University of Houston.

- Rollins, K.M., Gerber, T.M., Lane, J.D., and Ashford, S.A. (2005). "Lateral resistance of a full-scale pile group in liquefied sand." *Journal of Geotechnical and Geoenvironmental Engineering*, ASCE, 131(1), 115-125.

- Franke, B.W. and Rollins, K.M. (2013). "Lateral pile resistance in liquefied soil using the hybrid p-y approach." *Proceedings, GeoCongress 2013*, ASCE, pp. 1-10.

- Reese, L.C. (1997). "Analysis of laterally loaded piles in weak rock." *Journal of Geotechnical and Geoenvironmental Engineering*, ASCE, 123(11), 1010-1017.

- Liang, R., Yang, K., and Nusairat, J. (2009). "p-y criterion for rock mass." *Journal of Geotechnical and Geoenvironmental Engineering*, ASCE, 135(1), 26-36.

- Simpson, M. and Brown, D.A. (2006). *Development of p-y curves for Piedmont residual soils*. Highway Research Center, Auburn University.

- Johnson, J.T., Brown, D.A., and Reese, L.C. (2006). *Behavior of laterally loaded drilled shafts in loess*. Highway Research Center, Auburn University.

- Brown, D.A. (2002). "Effect of construction on laterally loaded piles in cohesive soils." *Proceedings, International Deep Foundations Congress*, ASCE, GSP 116, pp. 774-788.

- Hardin, B.O. and Drnevich, V.P. (1972). "Shear modulus and damping in soils: measurement and parameter effects." *Journal of Soil Mechanics and Foundations Division*, ASCE, 98(SM6), 603-624.

- Ensoft, Inc. (2022). *LPile v2022 Technical Manual*. Ensoft, Inc., Austin, TX.

### Lateral Load -- Broms Method

- Broms, B.B. (1964a). "Lateral resistance of piles in cohesive soils." *Journal of Soil Mechanics and Foundations Division*, ASCE, 90(SM2), 27-63.

- Broms, B.B. (1964b). "Lateral resistance of piles in cohesionless soils." *Journal of Soil Mechanics and Foundations Division*, ASCE, 90(SM3), 123-156.

- Davisson, M.T. and Robinson, K.E. (1965). "Bending and buckling of partially embedded piles." *Proceedings, 6th International Conference on Soil Mechanics and Foundation Engineering*, Vol. 2, pp. 243-246.

### Pile Groups

- Converse, F.J. (1962). "Foundations subjected to dynamic forces." *Foundation Engineering* (ed. G.A. Leonards), McGraw-Hill, New York.

- Brown, D.A., Morrison, C., and Reese, L.C. (2001). "Lateral load behavior of pile group in sand." *Journal of Geotechnical and Geoenvironmental Engineering*, ASCE, 114(11), 1261-1276.

### Liquefaction

- Boulanger, R.W. and Idriss, I.M. (2014). "CPT and SPT based liquefaction triggering procedures." *Report No. UCD/CGM-14/01*, Center for Geotechnical Modeling, University of California, Davis.

- Liao, S.S.C. and Whitman, R.V. (1986). "Overburden correction factors for SPT in sand." *Journal of Geotechnical Engineering*, ASCE, 112(3), 373-377.

### SPT Correlations

- Hatanaka, M. and Uchida, A. (1996). "Empirical correlation between penetration resistance and internal friction angle of sandy soils." *Soils and Foundations*, 36(4), 1-9.

- Terzaghi, K. and Peck, R.B. (1967). *Soil Mechanics in Engineering Practice* (2nd Ed.). John Wiley & Sons, New York.

### Frost Depth

- Modified Berggren (Stefan) equation as implemented in U.S. Army Corps of Engineers frost depth procedures.

### Installation QC

- Hannigan, P.J., Rausche, F., Likins, G.E., Robinson, B.R., and Becker, M.L. (2016). *Design and Construction of Driven Pile Foundations* (FHWA-NHI-16-009). Federal Highway Administration, Washington, DC.

- Gates, M. (1957). "Empirical formula for predicting pile bearing capacity." *Civil Engineering*, ASCE, 27(3), 65-66.

- Hoyt, R.M. and Clemence, S.P. (1989). "Uplift capacity of helical anchors in soil." *Proceedings, 12th International Conference on Soil Mechanics and Foundation Engineering*, Vol. 2, pp. 1019-1022.

### Helical Piles

- ICC-ES. (2017). *Acceptance Criteria for Helical Foundation Systems and Devices* (AC358). ICC Evaluation Service, Brea, CA.
