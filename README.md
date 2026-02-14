# SPORK — Solar Pile Optimization & Report Kit

A professional-grade foundation analysis application for utility-scale solar pile design. Performs axial capacity, lateral load (p-y curve), pile group, FEM, structural, and liquefaction analyses using established geotechnical and structural engineering methods.

Built with **Streamlit** (Python + Plotly). A legacy Next.js frontend exists but is not actively maintained.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Streamlit Pages](#streamlit-pages)
- [Calculation Engine](#calculation-engine)
- [Deployment](#deployment)
- [Engineering Methodology](#engineering-methodology)
- [References](#references)
- [License](#license)

---

## Features

- **Project Setup** — Create, export, and import projects as JSON; TOPL file import (ATI, Nevados, Nextracker)
- **Soil Profile Builder** — Layered soil profiles with SPT N-values, unit weights, friction angles, cohesion; per-layer p-y model selection from 18 LPile v2022 models; auto-correlates missing parameters from N-values
- **Pile Property Selection** — AISC W-shape and C-shape sections with full section properties; configurable embedment, installation method, head condition, bending axis; corrosion allowance analysis
- **ASCE 7-22 Load Combinations** — Automatic LRFD and ASD combination generation from dead, live, snow, wind, and seismic inputs; built-in wind/seismic/snow calculators
- **Pile Optimization** — Section family sweep across embedment ranges with automatic pass/fail checks
- **Axial Capacity Analysis** — Alpha (API RP 2A), Beta (effective stress), and Meyerhof methods; LRFD/ASD factored results with capacity vs. depth profiles
- **Lateral Load Analysis** — Nonlinear p-y curve generation (18 LPile v2022 models) with finite difference method solver; Broms simplified check; service deflection check; minimum embedment for lateral stability
- **Pile Group Analysis** — Converse-Labarre efficiency, AASHTO/FHWA p-multipliers, block failure check
- **BNWF Finite Element Analysis** — Beam-on-nonlinear-Winkler-foundation model with t-z/q-z axial springs, pushover curves, eigenvalue analysis, and pile head stiffness matrix
- **AISC 360-22 Structural Check** — H1-1 combined axial + bending interaction with depth of fixity and interaction diagrams
- **Liquefaction Screening** — Boulanger & Idriss (2014) SPT-based simplified procedure with CSR/CRR and factor of safety profiles
- **Installation QC** — Dynamic driving formulas (ENR, Gates, FHWA Modified Gates) for driven piles; torque correlation for helical piles
- **Frost Depth Check** — IBC 1809.5 compliance, Stefan equation, regional lookup
- **PDF Report Export** — Professional multi-section PDF report with section properties, soil profiles, depth profile plots, load combinations, and analysis summaries (fpdf2 + kaleido)

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Install & Run

```bash
# Clone the repository
git clone https://github.com/jason-orcas/solar-pile-design.git
cd solar-pile-design

# Install Python dependencies
pip install -r requirements.txt

# Launch the Streamlit app
streamlit run streamlit_app/streamlit_app.py --server.headless true
```

The app opens at **http://localhost:8501**. Use the sidebar to navigate through each analysis step.

---

## Project Structure

```
Solar_Pile_Design/
├── core/                        ← Shared Python calculation engine (authoritative source)
│   ├── soil.py                  ← SoilLayer, SoilProfile, SoilType, p-y curves (18 models)
│   ├── sections.py              ← SteelSection database, families, corrosion analysis
│   ├── loads.py                 ← LoadInput, LRFD/ASD load combinations (ASCE 7-22)
│   ├── axial.py                 ← Axial capacity (alpha, beta, Meyerhof methods)
│   ├── lateral.py               ← Lateral FDM p-y solver, Broms, min embedment
│   ├── group.py                 ← Pile group efficiency and block failure
│   ├── bnwf.py                  ← Beam-on-Nonlinear-Winkler-Foundation (FEM)
│   ├── tz_qz.py                 ← t-z / q-z axial spring curves
│   ├── optimization.py          ← Section x embedment sweep optimizer
│   ├── structural.py            ← AISC 360-22 structural check (H1-1 interaction)
│   ├── frost.py                 ← Frost depth check (IBC 1809.5, Stefan equation)
│   ├── liquefaction.py          ← Liquefaction screening (Boulanger & Idriss 2014)
│   ├── installation.py          ← Installation QC (ENR, Gates, FHWA; helical torque)
│   ├── topl_parser.py           ← TOPL file parser (ATI, Nevados, Nextracker)
│   ├── pdf_export.py            ← PDF report generation (fpdf2, 20+ sections)
│   └── bnwf_opensees.py         ← OpenSeesPy BNWF solver (optional)
│
├── streamlit_app/               ← Streamlit frontend
│   ├── streamlit_app.py         ← Landing page
│   ├── assets/                  ← Static assets (logo)
│   ├── core/                    ← Synced copy of calculation engine
│   └── pages/                   ← 13 Streamlit pages (01–14)
│
├── docs/                        ← Documentation
│   ├── SPORK_User_Manual.md     ← User manual (markdown source)
│   ├── SPORK_User_Manual.docx   ← User manual (Word format)
│   └── build_manual_docx.py     ← Markdown → DOCX conversion script
│
├── references/                  ← Engineering formula reference library (5 files)
│   ├── axial_capacity_formulas.md
│   ├── lateral_load_py_curves.md
│   ├── soil_parameter_correlations.md
│   ├── pile_group_efficiency.md
│   └── load_combinations.md
│
├── src/                         ← Next.js frontend (legacy, not actively maintained)
├── api/                         ← Vercel Python serverless functions (legacy)
├── requirements.txt             ← Python dependencies
└── CLAUDE.md                    ← Claude Code agent instructions
```

---

## Streamlit Pages

| Page | File | Description |
|------|------|-------------|
| 01 — Project Setup | `pages/01_Project_Setup.py` | Project info, TOPL import, JSON save/load |
| 02 — Soil Profile | `pages/02_Soil_Profile.py` | Soil layers, SPT, p-y model selection, frost depth |
| 03 — Pile Properties | `pages/03_Pile_Properties.py` | Section selection, corrosion analysis |
| 04 — Loading | `pages/04_Loading.py` | ASCE 7-22 loads, LRFD/ASD combinations |
| 05 — Pile Optimization | `pages/05_Pile_Optimization.py` | Section family sweep optimizer |
| 06 — Axial Capacity | `pages/06_Axial_Capacity.py` | Alpha, Beta, Meyerhof with depth profiles |
| 07 — Lateral Analysis | `pages/07_Lateral_Analysis.py` | FDM p-y solver, Broms, service deflection, min embedment |
| 08 — Group Analysis | `pages/08_Group_Analysis.py` | Converse-Labarre, p-multipliers, block failure |
| 09 — FEM Analysis | `pages/09_FEM_Analysis.py` | BNWF with t-z/q-z springs, pushover, eigenvalue |
| 11 — Structural Check | `pages/11_Structural_Check.py` | AISC 360-22 H1-1 unity check |
| 12 — Liquefaction | `pages/12_Liquefaction.py` | Boulanger & Idriss SPT-based screening |
| 13 — Installation QC | `pages/13_Installation_QC.py` | Dynamic driving formulas, helical torque |
| 14 — Export Report | `pages/14_Export_Report.py` | PDF report generation and download |

---

## Calculation Engine

The `core/` directory contains all engineering logic. The Streamlit app imports from a synced copy at `streamlit_app/core/`.

> **Maintenance rule:** Always edit `core/` (root) first, then copy changes to `streamlit_app/core/`. Never edit the synced copy directly.

### Soil Model (`soil.py`)

- `SoilType` enum — Sand, Clay, Silt, Gravel, Organic; drives parameter estimation, axial method selection, Broms checks, liquefaction screening
- `PYModel` enum — AUTO + 18 LPile v2022 p-y curve models (Matlock soft clay, Reese stiff clay, API sand, etc.)
- `SoilLayer`, `SoilProfile` — Layer management, water table, effective/total stress profiles
- SPT correlations — N₆₀, (N₁)₆₀, N-to-φ′, N-to-cᵤ, N-to-γ auto-estimation

### Sections (`sections.py`)

- `SteelSection` — AISC W-shape and C-shape database with full section properties
- Section families for optimization sweeps
- Corrosion analysis — environment-based wall thickness loss over design life

### Axial Capacity (`axial.py`)

- Alpha (API RP 2A) — adhesion method for clay
- Beta (effective stress) — for sand, silt, and mixed profiles
- Meyerhof — SPT-based bearing capacity for sand
- Compression and tension capacity with LRFD/ASD factors

### Lateral Analysis (`lateral.py`)

- 18 p-y curve models from LPile v2022
- Nonlinear FDM solver (iterative, 100 elements)
- Broms simplified capacity check (cohesionless and cohesive)
- Service deflection evaluation
- Minimum embedment for lateral stability

### Group Analysis (`group.py`)

- Converse-Labarre axial efficiency
- AASHTO/FHWA p-multipliers for lateral group reduction
- Block failure capacity for cohesive soils

### BNWF FEM (`bnwf.py`, `tz_qz.py`)

- Beam-on-nonlinear-Winkler-foundation with p-y lateral springs and t-z/q-z axial springs
- Static, pushover, and eigenvalue analyses
- Pile head stiffness matrix extraction
- Optional OpenSeesPy backend (`bnwf_opensees.py`)

### Structural Check (`structural.py`)

- AISC 360-22 Section H1-1 combined axial + bending interaction
- Depth of fixity and unbraced length calculation
- Interaction diagram generation

### Liquefaction Screening (`liquefaction.py`)

- Boulanger & Idriss (2014) SPT-based simplified procedure
- CSR, CRR, magnitude scaling factor, factor of safety per layer

### Installation QC (`installation.py`)

- Driven piles: ENR, Gates, FHWA Modified Gates dynamic formulas
- Helical piles: K_t torque correlation (ICC-ES AC358)

### Other Modules

- `frost.py` — IBC 1809.5 frost depth check, Stefan equation
- `optimization.py` — Section family × embedment sweep with pass/fail criteria
- `topl_parser.py` — TOPL file import (ATI, Nevados, Nextracker)
- `loads.py` — ASCE 7-22 LRFD/ASD load combinations, wind/seismic/snow calculators
- `pdf_export.py` — 20+ section PDF report generation with fpdf2

---

## Deployment

### Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect the repository
4. Set **Main file path** to `streamlit_app/streamlit_app.py`
5. Deploy

---

## Engineering Methodology

### Axial Capacity

| Method | Soil Type | Reference |
|--------|-----------|-----------|
| Alpha (adhesion) | Clay | API RP 2A; Tomlinson (4th Ed.) |
| Beta (effective stress) | Sand, Silt | Das (7th Ed.) |
| Meyerhof | Sand | Meyerhof (1976) |

### Lateral Analysis (p-y Methods)

| Model | Soil Type | Reference |
|-------|-----------|-----------|
| Matlock soft clay | Soft clay (c_u) | Matlock (1970) |
| Reese stiff clay below WT | Stiff clay below water table | Reese et al. (1975) |
| Reese stiff clay above WT | Stiff clay above water table | Welch & Reese (1972) |
| API sand | Sand (φ′) | API RP 2GEO (2011) |
| Reese sand | Sand | Reese, Cox & Koop (1974) |
| Cemented c-φ soil | Mixed soils | Reese & Van Impe (2001) |
| Weak rock | Weak rock | Reese (1997) |

Plus 11 additional LPile v2022 models for loess, silt, liquefied sand, and other conditions.

### Structural Check

| Check | Standard | Reference |
|-------|----------|-----------|
| Combined axial + bending | AISC 360-22 H1-1a/b | AISC (2022) |
| Depth of fixity | Davisson & Robinson | Davisson (1965) |

### Liquefaction Screening

| Method | Reference |
|--------|-----------|
| SPT-based simplified procedure | Boulanger & Idriss (2014) |

### Group Efficiency

| Method | Application | Reference |
|--------|-------------|-----------|
| Converse-Labarre | Axial efficiency | Das (7th Ed.) |
| AASHTO p-multipliers | Lateral group reduction | AASHTO LRFD (2020) |
| Block failure | Cohesive soil group capacity | Das (7th Ed.) |

### Load Combinations

Per ASCE 7-22: Chapters 2 (combinations), 26–31 (wind), 12/15 (seismic), 7 (snow).

---

## References

- AISC 360-22 — *Specification for Structural Steel Buildings*
- API RP 2GEO — *Geotechnical and Foundation Design Considerations*
- ASCE 7-22 — *Minimum Design Loads and Associated Criteria*
- AASHTO LRFD Bridge Design Specifications (2020) — p-multipliers
- Boulanger, R.W. & Idriss, I.M. (2014) — *CPT and SPT Based Liquefaction Triggering Procedures*
- Das, B.M. — *Principles of Foundation Engineering* (7th Ed.)
- Davisson, M.T. (1965) — Estimating buckling loads for piles
- IBC (2021) — *International Building Code*, Section 1809.5 (frost protection)
- ICC-ES AC358 — Acceptance criteria for helical pile foundations
- Matlock, H. (1970) — Correlations for design of laterally loaded piles in soft clay
- Rajapakse, R. — *Pile Design and Construction Rule of Thumb* (2nd Ed.)
- Reese, L.C. et al. (1974) — Analysis of laterally loaded piles in sand
- Reese, L.C. et al. (1975) — Laterally loaded piles in stiff clay
- Reese, L.C. (1997) — Analysis of laterally loaded piles in weak rock
- Reese, L.C. & Van Impe, W.F. (2001) — *Single Piles and Pile Groups Under Lateral Loading*
- Tomlinson, M.J. — *Pile Design and Construction Practice* (4th Ed.)
- Welch, R.C. & Reese, L.C. (1972) — Laterally loaded behavior of drilled shafts

See the `references/` directory for detailed formula sheets and the `docs/` directory for the user manual.

---

## License

Private repository. All rights reserved.
