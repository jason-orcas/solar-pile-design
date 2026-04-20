# SPORK Migration Brief — Streamlit → spork.borcas.ai

Handoff document for the Claude running on the garage server (superc2) to
port the Streamlit SPORK app to `spork.borcas.ai`. Paste the fenced block
below verbatim — it is self-contained.

Authoritative repo: https://github.com/jason-orcas/solar-pile-design
(master branch reflects production; all recent engineering changes are
committed there).

---

```
Task: Rebuild spork.borcas.ai to match the current Streamlit SPORK
(github.com/jason-orcas/solar-pile-design, master branch). Keep the
existing Alpine.js + Supabase + Plotly stack. The current site has 13
flat pages on a dark-green "matrix terminal" light theme — the LIGHT
theme is being replaced with Bowman brand colors (matching ARCADE's
light mode at arcade.borcas.ai). The DARK theme stays as-is — user
likes the existing dark palette and wants to keep that toggle as a
feature.

───────── THEME ─────────

LIGHT MODE — replace with ARCADE's Bowman palette (lifted from
arcade.borcas.ai/static/css/app.css):

  --brand-green:        #00593d   (primary — headers, buttons, links)
  --brand-blue:         #03425b   (secondary — table headers, hover)
  --brand-celedon:      #bbcbbe   (light accent)
  --brand-gray:         #767b81   (muted text, subtle borders)
  --brand-yellow:       #f5bb0e   (accent, sparingly)
  --brand-accent-green: #83bc43   (accent, sparingly)
  --text-dark:          #1b1b1f
  --text-muted:         #767b81
  --surface:            #ffffff
  --background:         #f3f5f8
  --border:             #d0d7e2
  --danger:             #b0363b

Font family: "Segoe UI", "Segoe UI Web", -apple-system, Helvetica,
Arial, sans-serif. Text is left-aligned (never justified). Link color
is brand green; hover swaps to brand blue (matches ARCADE's button
hover convention).

DARK MODE — keep the existing palette from the current
spork.borcas.ai CSS. Do NOT re-invent a Bowman-adapted dark theme;
the user prefers the existing look. Variables currently in use:

  --color-bg:          #0a0a0a
  --color-surface:     #111
  --color-surface-hover: #1a1a1a
  --color-text:        #34d399
  --color-text-secondary: #047857
  --color-muted:       #064e3b
  --color-border:      #064e3b
  --color-primary:     #10b981
  --color-primary-hover: #34d399
  --color-primary-text: #000
  --color-primary-bg:  rgba(16,185,129,0.1)
  --color-success:     #4ade80
  --color-danger:      #f87171
  --btn-glow:          0 0 10px rgba(16,185,129,0.3)
  --input-focus-ring:  0 0 0 2px rgba(16,185,129,0.3)
  --sidebar-bg:        #0d0d0d
  --sidebar-border:    #064e3b
  --font-family:       'JetBrains Mono', ui-monospace, monospace

TOGGLE — keep the existing mechanism. It uses:

  <script>(function(){var t=localStorage.getItem('theme')||'dark';
  document.documentElement.setAttribute('data-theme',t)})()</script>

with [data-theme="dark"] overriding the :root CSS custom properties.
Persist user choice in localStorage under "theme". Keep the theme
toggle button in the header and on the auth screen.

NAMESPACE NOTE: ARCADE's CSS uses hyphenated names like --brand-green,
--surface, --background. spork's current CSS uses --color-bg,
--color-surface, etc. Converge on ONE scheme — recommend adopting
ARCADE's naming for the new light variables and keeping spork's
existing names for dark, OR use a single set (e.g. --surface,
--text, --primary) shared by both themes. Pick whichever yields
fewer churned selectors.

───────── SIDEBAR: grouped navigation matching Streamlit ─────────

Replace the flat 13-pill sidebar with collapsible section headers.
Use these exact groups in this order:

  Home
  ── Inputs ──
    1. Project Setup
    2. Soil Profile
    3. Pile Properties
    4. Loading
  ── Design ──
    5. Pile Optimization
  ── Analysis ──
    6. Axial Capacity
    7. Lateral Analysis
    8. Group Analysis
    9. FEM Analysis (BNWF)
   10. Cable Management
  ── Checks ──
   11. Structural Check
   12. Liquefaction
   13. Installation QC
  ── Output ──
   14. Export Report

Sections are expanded by default; persist each section's expanded
state per-user in localStorage.

───────── FEATURE PARITY: items from Streamlit SPORK to port ─────────

High-impact items (reference SHAs on master):

  [engineering — highest priority]
  0f3e67a  Adfreeze rework: geotech f_s_uplift integration over frost
           depth replaces separate τ_af parameter. axial_capacity now
           has frost_depth_ft param that excludes frost zone from
           tension/uplift capacity. New adfreeze_service_check():
             skin_friction_below_frost + D_per_pile - adfreeze ≥ 0
           (service-level, no load factors; matches FHWA/CFEM practice)
  1b3ee5d  Adfreeze uplift added as a load input on the Loading page
           with new LC8: 0.9D + A_f (LRFD) and ASD-AF: 0.6D + A_f
  ff05b59  Cable Management (new page) — CAB/AWM messenger wire sag,
           tension, and ground-clearance analysis
  d630b5d  Axial Soil Zones — separate skin friction / end bearing
           per depth interval, independent of the lateral p-y profile
  9f71bc5  Explicit axial inputs, steel grade selector, ASCE 7
           version selector, optional N-value

  [UI / workflow — medium priority]
  52b22df  Optimizer auto-apply + downstream auto-populated indicator
  ee00996  Optimizer stores results for downstream pages
  b44c095  Optimizer unified with frost/adfreeze + governing summary
  706877b  Group plan view legend below chart (avoid overlap)

  [everything else: git log 2026-02-15..HEAD -- core/ streamlit_app/]

───────── PAGE-BY-PAGE SPEC (Streamlit) ─────────

Page 01 Project Setup: name, number, location, engineer, notes,
  TOPL import (ATI PDF / Nevados PDF / Nextpower XLSX) with
  manufacturer selector + column selector + editable preview +
  apply button; JSON save/load of full project state.

Page 02 Soil Profile: layers (top_depth, thickness, soil_type,
  description, N_spt, γ, φ, c_u, p-y model per layer), water
  table depth, axial soil zones (separate optional table with
  top/bottom/f_s_comp/f_s_uplift/q_b), frost depth check (Regional
  / Stefan / Manual), Adfreeze Uplift Source radio (Geotech
  f_s_uplift recommended / Manual τ_af override), τ_af input,
  service-level adfreeze check with pass/fail banner and margin.

Page 03 Pile Properties: W/HP/HSS section db, embedment,
  above-grade, pile type (driven/drilled/helical), head
  condition, bending axis, corrosion analysis (optional).

Page 04 Loading: LRFD/ASD/Both radio, ASCE 7 edition selector,
  per-pile gravity/wind/seismic/environmental inputs incl. new
  adfreeze_uplift. Auto-populate adfreeze from Page 02 frost
  check via a button. Generate LRFD+ASD combination tables
  incl. the new LC8 (LRFD) and ASD-AF (when adfreeze > 0).
  Optional calculators: wind q_z, seismic C_s, snow p_f.

Page 05 Optimization: section-family sweep × embedment sweep.
  Runs axial+lateral+structural per combination, produces
  heatmap + detailed table, identifies governing failure mode,
  "apply optimal design" button. Must pass frost_depth_ft
  through to axial_capacity. Preserves opt-in adfreeze hard-fail
  checkbox.

Page 06 Axial Capacity: Alpha/Beta/Meyerhof/auto method, FS
  comp/tens, reads axial zones if set, applies frost_depth_ft
  from Page 02. Layer-by-layer breakdown with "in_frost_zone"
  flag. Reports Q_s_below_frost.

Page 07 Lateral Analysis: FDM p-y solver, Broms simplified,
  service deflection check, min embedment finder.

Page 08 Group Analysis: grid generator, editable pile table,
  editable load table, Converse-Labarre efficiency, p-multiplier
  for lateral groups, block failure, load distribution.

Page 09 FEM (BNWF): OpenSeesPy-based if available, else pure
  Python FDM. p-y + t-z + q-z springs.

Page 10 Cable Management: CAB (HDR tables) or AWM (catenary)
  system type radio, span, wire weight, temperature range,
  bracket geometry, clearance requirements, pile reveal, AWM-
  specific inputs (stringing tension or allowable sag), wind
  speed. Computes sag, tension, pass/fail against ground
  clearance + flood freeboard.

Page 11 Structural Check: AISC 360 H1-1 interaction, depth of
  fixity calc, unbraced length, K factor, reports DCR + plot.

Page 12 Liquefaction: Boulanger & Idriss 2014 SPT triggering.
  Inputs: PGA, Mw, fines content. Output: FS_liq per layer
  table + plot.

Page 13 Installation QC: driven pile formulas (ENR, Gates,
  FHWA Modified Gates) OR helical torque-based capacity.

Page 14 Export Report: PDF generation via fpdf2 (core/
  pdf_export.py), with all sections from Pages 01-13 + the
  new service-level adfreeze check section. Bowman logo header
  on every page, cover page, auto-generated TOC.

───────── CORE ENGINE — REUSABLE, DO NOT REWRITE ─────────

All engineering lives in the SPORK repo's core/ directory and is
pure Python. Port these modules behind a REST API on the garage
server; call them from the Alpine.js frontend. Key modules:

  core/soil.py          SoilLayer, SoilProfile, SoilType, PYModel,
                        AxialSoilZone, SPT corrections, parameter
                        derivation
  core/axial.py         axial_capacity(..., frost_depth_ft=0.0)
                        Alpha/Beta/Meyerhof methods. AxialResult
                        exposes Q_s, Q_b, Q_ult_tension,
                        Q_s_below_frost, layer_contributions.
  core/lateral.py       FDM p-y solver, Broms, min embedment
  core/loads.py         LoadInput with adfreeze_uplift field,
                        generate_lrfd_combinations (incl. LC8),
                        generate_asd_combinations (incl. ASD-AF),
                        wind_velocity_pressure, seismic_Cs,
                        snow_load
  core/frost.py         FROST_DEPTH_TABLE, STEFAN_C,
                        frost_depth_regional, frost_depth_stefan,
                        frost_check(adfreeze_force_override_lbs=),
                        adfreeze_from_profile(profile, perim,
                          frost_depth_ft, axial_zones),
                        adfreeze_service_check(...)
  core/group.py         Converse-Labarre, block failure, p-mult
  core/bnwf.py          BNWF FEM (pure Python fallback)
  core/bnwf_opensees.py OpenSeesPy BNWF (if available)
  core/tz_qz.py         t-z / q-z spring curves
  core/optimization.py  section × embedment sweep optimizer, now
                        passes frost_depth_ft through to axial
  core/sections.py      Steel section database + corrosion
  core/structural.py    AISC 360 H1-1
  core/liquefaction.py  Boulanger & Idriss 2014
  core/installation.py  Driven pile formulas + helical torque
  core/pdf_export.py    fpdf2-based report generator; includes
                        _render_frost_check() which now renders
                        the service-level adfreeze check too
  core/topl_parser.py   TOPL PDF/XLSX parsers

───────── CRITICAL ENGINEERING SUBTLETIES ─────────

1. Adfreeze demand IS the geotech's uplift skin friction in the
   frozen zone. SPORK v1.3 made this the default (vs the older
   separate τ_af input). Integrate f_s_uplift_psf over frost
   depth × perimeter. Keep τ_af as manual override.

2. Skin friction resistance in uplift EXCLUDES the frost zone
   when computing tension capacity (otherwise double-counts
   against the adfreeze demand). Compression is UNAFFECTED —
   frozen soil still resists downward loads.

3. Three separate adfreeze checks run in parallel:
     a) Service-level (Page 02): skin_below_frost + D_per_pile
        − adfreeze ≥ 0. No load factors. Industry standard.
     b) LRFD LC8 (Page 04): 0.9D + A_f; runs through normal
        axial tension capacity check at factored level.
     c) Optimizer (Page 05): raw adfreeze vs Q_r_tension (no
        D credit) — strictest; opt-in via checkbox.
   Show all three; don't collapse into one.

4. dz integration artifact: default dz=0.5 ft in axial integration
   over-estimates skin friction by ~7% at layer boundaries because
   layer_at_depth(z) looks up the layer at the END of each chunk.
   Converges to closed-form at dz=0.05. Not fixing in this
   migration — document in manual/UI if user cares.

5. Unit gotcha: τ_af is in psi, geotech f_s_uplift is typically
   in ksf. Conversion: τ_af(psi) = f_s_uplift(ksf) × 1000/144.

6. LC6 (0.9D + 1.0W) almost always governs solar; LC8 only
   governs when wind uplift is modest and frost is severe. Both
   are independent; no concurrent wind in LC8.

───────── WIDGET BEHAVIOR (why we're moving off Streamlit) ─────────

The Streamlit version had chronic widget-state bugs on page nav:
widget-bound session_state is cleared on unmount, requiring a
"shadow-state" pattern. Alpine.js's x-model / x-show naturally
avoids this — state lives in the root component's x-data, and
pages are just x-show'd divs, not real routes. Do NOT reinvent
the Streamlit shadow-state pattern; it's not needed here. Just
keep form state in the top-level Alpine component or use a
store.

───────── OUT OF SCOPE / ASK USER ─────────

- Bowman brand logo placement: confirm with user/design team.
  ARCADE uses text "ARCADE" in brand green; probably do the same
  with "SPORK" unless the Bowman PNG logo should appear in headers.

- PDF report styling: the current Streamlit PDF uses generic
  slate palette (#4A5568) not Bowman green/blue. User has not
  decided whether to rebrand the PDF. Keep current palette OR
  switch to Bowman — ask user.

- User manual (docs/SPORK_User_Manual_v1.3.docx) already uses
  Bowman branding.

───────── REFERENCE CONTENT ─────────

Current Streamlit version lives at the Bowman Streamlit Cloud
deployment (ask user for URL). Keep it running as the reference
implementation during migration.

Engineering formula references live in the repo's references/
directory (5 markdown files covering axial, lateral p-y, soil
parameter correlations, pile group efficiency, load combinations).
These are the authoritative sources for all calcs.

The end-user spreadsheet that drove the adfreeze rework is in
references/Combiners.xlsx — it's the pattern to match for the
frost-heave check display.
```

---

## Notes for Jason

- **Current spork.borcas.ai dark CSS** was inspected at the time of
  writing and the variables above were lifted directly. If the garage
  Claude refactors the stylesheet, they should preserve the exact
  existing dark colors rather than rewriting them.
- **ARCADE light CSS** was lifted from
  `arcade.borcas.ai/static/css/app.css` (search "Bowman Brand
  Standards" for the header block).
- **Dark-mode toggle button**: also missing from the current ARCADE
  deployment; spork.borcas.ai has a working one in both the auth
  screen and the header bar — keep that implementation as the model.
- **PDF brand alignment**: open question. The user manual is already
  Bowman-branded; the PDF report is not. Flag this for later.
