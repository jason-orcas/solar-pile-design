# Solar Pile Design Tool

A professional-grade foundation analysis application for utility-scale solar pile design. Performs axial capacity, lateral load (p-y curve), and pile group analysis using established geotechnical engineering methods.

**Two frontends** are maintained in parallel—choose whichever fits your deployment:

| Frontend | Stack | Best For |
|----------|-------|----------|
| **Streamlit** | Python + Plotly | Local use, quick sharing via Streamlit Cloud |
| **Next.js** | React + Recharts + Vercel Python Functions | Production web deployment on Vercel |

Both frontends share the same Python calculation engine (`core/`).

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start — Streamlit](#quick-start--streamlit)
- [Quick Start — Next.js / Vercel](#quick-start--nextjs--vercel)
- [Project Structure](#project-structure)
- [Shared Calculation Engine](#shared-calculation-engine)
- [API Reference (Vercel)](#api-reference-vercel)
- [Deployment](#deployment)
- [Engineering Methodology](#engineering-methodology)
- [References](#references)
- [License](#license)

---

## Features

- **Project Setup** — Create, export, and import projects as JSON
- **Soil Profile Builder** — Define layered soil profiles with SPT N-values, unit weights, friction angles, cohesion; auto-correlates missing parameters
- **Pile Property Selection** — AISC W-shape and C-shape sections with full section properties; configurable embedment, installation method, head condition, and bending axis
- **ASCE 7-22 Load Combinations** — Automatic LRFD and ASD combination generation from dead, live, snow, wind, and seismic inputs
- **Axial Capacity Analysis** — Alpha (API RP 2A), Beta (effective stress), Meyerhof, and Nordlund methods; helical pile torque correlation; LRFD/ASD factored results
- **Lateral Load Analysis** — Nonlinear p-y curve generation (Matlock soft clay, Reese sand, API RP 2A) with finite difference method solver; deflection, moment, and shear profiles
- **Pile Group Analysis** — Converse-Labarre efficiency, AASHTO/FHWA p-multipliers, block failure check, plan-view layout diagram

---

## Architecture

```
Solar_Pile_Design/
│
├── core/                  ← Shared Python calculation engine (root)
│   ├── soil.py            ← Soil model, SPT correlations, effective stress
│   ├── sections.py        ← Steel section database (AISC properties)
│   ├── axial.py           ← Axial capacity methods
│   ├── lateral.py         ← p-y curves + FDM solver
│   ├── group.py           ← Group efficiency + block failure
│   └── loads.py           ← ASCE 7-22 load combinations
│
├── streamlit_app/         ← Streamlit frontend
│   ├── streamlit_app.py   ← Entry point
│   ├── pages/             ← 8 Streamlit pages (01–08)
│   ├── core/              ← Local copy of calculation engine
│   └── projects/          ← Saved project JSON files
│
├── src/                   ← Next.js frontend
│   ├── app/               ← App Router pages (7 routes)
│   ├── components/        ← ProjectProvider (React context)
│   └── lib/               ← api.ts (TypeScript API client)
│
├── api/                   ← Vercel Python serverless functions
│   ├── axial.py           ← POST /api/axial
│   ├── lateral.py         ← POST /api/lateral
│   ├── group.py           ← POST /api/group
│   └── loads.py           ← POST /api/loads
│
├── references/            ← Engineering formula reference library
│   ├── axial_capacity_formulas.md
│   ├── lateral_load_py_curves.md
│   ├── soil_parameter_correlations.md
│   ├── pile_group_efficiency.md
│   └── load_combinations.md
│
├── requirements.txt       ← Python dependencies (Streamlit + core)
├── package.json           ← Node dependencies (Next.js frontend)
├── vercel.json            ← Vercel deployment config
├── next.config.mjs        ← Next.js configuration
├── tailwind.config.ts     ← Tailwind CSS configuration
├── tsconfig.json          ← TypeScript configuration
└── CLAUDE.md              ← Claude Code agent instructions
```

---

## Quick Start — Streamlit

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

## Quick Start — Next.js / Vercel

### Prerequisites

- Node.js 18+
- npm
- Python 3.10+ (for local API function testing)

### Install & Run

```bash
# Clone the repository
git clone https://github.com/jason-orcas/solar-pile-design.git
cd solar-pile-design

# Install Node dependencies
npm install

# Install Python dependencies (for API functions)
pip install -r requirements.txt

# Start the Next.js dev server
npm run dev
```

The app opens at **http://localhost:3000**. Analysis pages call the Python API routes under `/api/`.

> **Note:** In local development, the Python API routes require the Vercel CLI (`vercel dev`) or a separate Python server. For full local testing, use the Streamlit frontend. For production, deploy to Vercel.

---

## Project Structure

### Streamlit Pages

| Page | File | Description |
|------|------|-------------|
| Project Setup | `streamlit_app/pages/01_Project_Setup.py` | Create/load/save projects |
| Soil Profile | `streamlit_app/pages/02_Soil_Profile.py` | Define soil layers, water table |
| Pile Properties | `streamlit_app/pages/03_Pile_Properties.py` | Select steel section, embedment |
| Loading | `streamlit_app/pages/04_Loading.py` | Enter loads, generate combinations |
| Axial Capacity | `streamlit_app/pages/05_Axial_Capacity.py` | Run axial analysis with charts |
| Lateral Analysis | `streamlit_app/pages/06_Lateral_Analysis.py` | p-y curves, deflection profiles |
| Group Analysis | `streamlit_app/pages/07_Group_Analysis.py` | Group efficiency, block failure |
| FEM Analysis | `streamlit_app/pages/08_FEM_Analysis.py` | BNWF combined axial+lateral FEM |

### Next.js Routes

| Route | File | Description |
|-------|------|-------------|
| `/` | `src/app/page.tsx` | Project setup, import/export |
| `/soil-profile` | `src/app/soil-profile/page.tsx` | Soil layer input table |
| `/pile-properties` | `src/app/pile-properties/page.tsx` | Section selection + properties |
| `/loading` | `src/app/loading/page.tsx` | Load input + combination tables |
| `/axial-capacity` | `src/app/axial-capacity/page.tsx` | Axial results + bar charts |
| `/lateral-analysis` | `src/app/lateral-analysis/page.tsx` | Deflection/moment line charts |
| `/group-analysis` | `src/app/group-analysis/page.tsx` | Efficiency + plan view diagram |

---

## Shared Calculation Engine

The `core/` directory contains all engineering logic. Both frontends import from it.

### `core/soil.py`

- `SoilLayer` — Dataclass with field data and derived parameters
- `SoilProfile` — Layer management, water table, effective/total stress profiles
- SPT correlations: `correct_N_overburden()`, `n_to_phi_hatanaka()`, `n_to_cu()`, `n_to_Es_sand()`

### `core/sections.py`

- `SteelSection` — AISC section database (W6, W8, C4 shapes)
- Computed properties: `perimeter`, `tip_area`, `EI_strong`, `EI_weak`, `Mp_strong`

### `core/axial.py`

- `axial_capacity()` — Master function: skin friction + end bearing
- Methods: Alpha (API RP 2A), Beta (effective stress), Meyerhof, Nordlund
- `helical_capacity_torque()` — K_t torque correlation
- Returns `AxialResult` with compression/tension capacity breakdown

### `core/lateral.py`

- p-y curve generators: `py_matlock_soft_clay()`, `py_api_sand()`, `py_api_soft_clay()`
- `solve_lateral()` — Nonlinear FDM solver (100 elements, iterative)
- `broms_cohesionless()`, `broms_cohesive()` — Simplified capacity checks
- Returns `LateralResult` with depth profiles and p-y curves

### `core/group.py`

- `converse_labarre()` — Axial efficiency factor
- `p_multipliers_table()` — AASHTO/FHWA lateral multipliers
- `block_failure_cohesive()` — Block failure capacity
- `group_analysis()` — Complete analysis returning `GroupResult`

### `core/loads.py`

- `generate_lrfd_combinations()` — 7 LRFD load cases (ASCE 7-22)
- `generate_asd_combinations()` — 8 ASD load cases
- Helper functions: `wind_velocity_pressure()`, `seismic_base_shear_coeff()`, `snow_load()`

---

## API Reference (Vercel)

All API routes accept `POST` requests with JSON body and return JSON.

### `POST /api/axial`

Runs axial capacity analysis.

**Request body:**
```json
{
  "soil_layers": [
    { "top_depth": 0, "thickness": 5, "soil_type": "Sand", "N_spt": 15, ... }
  ],
  "water_table_depth": null,
  "pile_section": "W6x9",
  "embedment_depth": 8,
  "pile_type": "driven",
  "bending_axis": "strong",
  "axial_method": "Beta",
  "FS_compression": 2.5,
  "FS_tension": 3.0,
  "design_method": "LRFD"
}
```

**Response:** Compression/tension capacities, layer breakdown, factored results.

### `POST /api/lateral`

Runs lateral p-y analysis with FDM solver.

**Request body:** Same project fields plus `head_condition`, `bending_axis`.

**Response:** Deflection, moment, shear, and rotation profiles at each depth node; p-y curve data; convergence info; DCR check.

### `POST /api/group`

Runs pile group efficiency analysis.

**Request body:** Includes `group_rows`, `group_cols`, `group_spacing`, `Q_single`.

**Response:** Converse-Labarre efficiency, p-multipliers per row, block failure capacity, group capacity.

### `POST /api/loads`

Generates ASCE 7-22 load combinations.

**Request body:** Dead, live, snow, wind (down/up/lateral/moment), seismic loads, `lever_arm`, `design_method`.

**Response:** Arrays of LRFD and/or ASD load cases with V_comp, V_tens, H_lat, M_ground.

---

## Deployment

### Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect the repository
4. Set **Main file path** to `streamlit_app/streamlit_app.py`
5. Deploy

### Vercel

1. Push to GitHub
2. Import the repository on [vercel.com](https://vercel.com)
3. Vercel auto-detects Next.js + Python functions from `vercel.json`
4. Deploy

> The `vercel.json` configures Python runtime `@vercel/python@4.5.1` with 30-second max duration for serverless functions.

---

## Engineering Methodology

### Axial Capacity

| Method | Soil Type | Reference |
|--------|-----------|-----------|
| Alpha (adhesion) | Clay | API RP 2A; Tomlinson |
| Beta (effective stress) | Sand, Silt | Das (7th Ed.) |
| Meyerhof | Sand | Meyerhof (1976) |
| Nordlund | Sand | Nordlund (1963) |
| Torque correlation | Helical | ICC-ES AC358 |

### Lateral Analysis (p-y Methods)

| Method | Soil Type | Reference |
|--------|-----------|-----------|
| Matlock | Soft clay | Matlock (1970) |
| Reese | Sand | Reese et al. (1974) |
| API RP 2A | Sand and soft clay | API RP 2GEO |

### Group Efficiency

| Method | Application |
|--------|-------------|
| Converse-Labarre | Axial group efficiency |
| AASHTO p-multipliers | Lateral group reduction |
| Block failure | Cohesive soil group capacity |

### Load Combinations

Per ASCE 7-22, Chapters 2, 26–31 (wind), 12/15 (seismic), 7 (snow).

---

## References

- Das, B.M. — *Principles of Foundation Engineering* (7th Ed.)
- Rajapakse, R. — *Pile Design and Construction Rule of Thumb* (2nd Ed.)
- Tomlinson, M.J. — *Pile Design and Construction Practice* (4th Ed.)
- API RP 2GEO — *Geotechnical and Foundation Design Considerations*
- ASCE 7-22 — *Minimum Design Loads and Associated Criteria*
- AASHTO LRFD Bridge Design Specifications (p-multipliers)
- Matlock, H. (1970) — Correlations for design of laterally loaded piles in soft clay
- Reese, L.C. et al. (1974) — Analysis of laterally loaded piles in sand

See the `references/` directory for detailed formula sheets used by the calculation engine.

---

## License

Private repository. All rights reserved.
