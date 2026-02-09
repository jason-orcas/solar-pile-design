"""SPile+-style PDF report generation for solar pile foundation design.

Produces a multi-section PDF report mirroring SPile+ output format:
project details, basis for design, design summary, section properties,
soil profile, analysis summary, vertical load check, load combinations,
depth profile plots and tables, pile analysis summary, and warnings.

Dependencies: fpdf2, kaleido (for Plotly chart export)
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
from fpdf import FPDF

from .sections import SteelSection, SECTIONS, get_section
from .soil import SoilProfile, SoilLayer, SoilType
from .axial import AxialResult
from .lateral import LateralResult, PYCurve
from .group import GroupResult
from .bnwf import BNWFResult
from .loads import LoadCase, LoadInput, generate_lrfd_combinations, generate_asd_combinations


# ============================================================================
# Report Data Container
# ============================================================================

@dataclass
class ReportData:
    """All data needed to generate the PDF report."""

    # Project info
    project_name: str = "Untitled Project"
    project_number: str = ""
    project_location: str = ""
    project_notes: str = ""
    engineer_of_record: str = ""
    report_date: str = ""

    # Design limits
    top_deflection_limit: float = 4.0      # in
    grade_deflection_limit: float = 1.0    # in
    bottom_deflection_limit: float = 0.1   # in

    # Pile configuration
    section: SteelSection | None = None
    pile_embedment: float = 0.0            # ft
    above_grade: float = 0.0               # ft
    pile_type: str = "driven"
    head_condition: str = "free"
    bending_axis: str = "strong"
    yield_strength: float = 50.0           # ksi
    loading_type: str = "Static"

    # Soil
    soil_profile: SoilProfile | None = None
    soil_layers_raw: list = field(default_factory=list)
    water_table_depth: float | None = None

    # Loads
    load_input: LoadInput | None = None
    design_method: str = "LRFD"

    # Analysis results (None if not run)
    axial_result: AxialResult | None = None
    lateral_result: LateralResult | None = None
    group_result: GroupResult | None = None
    bnwf_result: BNWFResult | None = None

    # Group config
    group_n_rows: int = 1
    group_n_cols: int = 1
    group_spacing: float = 36.0            # in


# ============================================================================
# Custom PDF Class
# ============================================================================

class PileReportPDF(FPDF):
    """Custom PDF class replicating SPile+ report styling."""

    # Color constants (RGB)
    HEADER_BG = (74, 85, 104)
    HEADER_FG = (255, 255, 255)
    TABLE_HEADER_BG = (100, 110, 130)
    TABLE_ALT_ROW = (245, 245, 248)
    CARD_BORDER = (210, 210, 215)
    TEXT_PRIMARY = (40, 40, 45)
    TEXT_SECONDARY = (100, 100, 110)

    APP_TITLE = "Solar Pile Design"

    # Unicode → ASCII replacements for Helvetica compatibility
    _UNICODE_MAP = {
        "\u2193": "(dn)",   # ↓
        "\u2191": "(up)",   # ↑
        "\u2192": "->",     # →
        "\u2190": "<-",     # ←
        "\u2264": "<=",     # ≤
        "\u2265": ">=",     # ≥
        "\u00b0": "deg",    # °
        "\u2018": "'",      # '
        "\u2019": "'",      # '
        "\u201c": '"',      # "
        "\u201d": '"',      # "
        "\u2014": "--",     # —
        "\u2013": "-",      # –
    }

    @staticmethod
    def _safe_text(text: str) -> str:
        """Replace Unicode characters unsupported by Helvetica with ASCII equivalents."""
        for uc, repl in PileReportPDF._UNICODE_MAP.items():
            text = text.replace(uc, repl)
        return text

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="letter")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_font("Helvetica", "", 10)

    def header(self):
        """Page header with app title top-right."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.HEADER_BG)
        self.set_xy(self.w - 65, 8)
        self.cell(55, 6, self.APP_TITLE, align="R")
        self.ln(12)

    def footer(self):
        """Page footer with page number."""
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*self.TEXT_SECONDARY)
        self.cell(0, 8, f"Page {self.page_no()} of {{nb}}", align="R")

    def section_header(self, title: str):
        """Dark rounded-corner section header bar spanning full width."""
        self._check_page_space(15)
        self.set_fill_color(*self.HEADER_BG)
        self.set_text_color(*self.HEADER_FG)
        self.set_font("Helvetica", "B", 11)
        self.set_draw_color(*self.HEADER_BG)
        x, y = self.get_x(), self.get_y()
        w = self.w - 2 * self.l_margin
        self.rect(x, y, w, 8, style="FD")
        self.set_xy(x, y + 1)
        self.cell(w, 6, self._safe_text(title), align="C")
        self.set_text_color(*self.TEXT_PRIMARY)
        self.ln(12)

    def sub_header(self, title: str):
        """Lighter sub-section header bar."""
        self._check_page_space(12)
        self.set_fill_color(190, 195, 205)
        self.set_text_color(*self.TEXT_PRIMARY)
        self.set_font("Helvetica", "B", 9)
        x = self.l_margin + 10
        w = self.w - 2 * self.l_margin - 20
        y = self.get_y()
        self.set_draw_color(190, 195, 205)
        self.rect(x, y, w, 7, style="FD")
        self.set_xy(x, y + 0.5)
        self.cell(w, 6, self._safe_text(title), align="C")
        self.set_text_color(*self.TEXT_PRIMARY)
        self.ln(10)

    def card_start(self):
        """Begin a card section."""
        self._card_y = self.get_y()
        self._card_x = self.l_margin

    def card_end(self):
        """Close the card section with a border."""
        y_end = self.get_y()
        w = self.w - 2 * self.l_margin
        h = max(y_end - self._card_y + 2, 4)
        self.set_draw_color(*self.CARD_BORDER)
        self.rect(self._card_x, self._card_y, w, h, style="D")
        self.ln(4)

    def kv_row(self, label: str, value: str, unit: str = "", note: str = ""):
        """Key-value row matching SPile+ parameter listing."""
        self._check_page_space(7)
        self.set_font("Helvetica", "", 9)
        x_start = self.l_margin + 15
        self.set_x(x_start)
        self.cell(65, 5.5, label)
        self.cell(5, 5.5, "=")
        self.set_font("Helvetica", "B", 9)
        self.cell(25, 5.5, str(value))
        self.set_font("Helvetica", "", 9)
        self.cell(15, 5.5, unit)
        if note:
            self.set_text_color(*self.TEXT_SECONDARY)
            self.cell(50, 5.5, note)
            self.set_text_color(*self.TEXT_PRIMARY)
        self.ln(5.5)

    def styled_table(self, headers: list, rows: list,
                     col_widths: list | None = None, align: str = "C"):
        """Professional table with gray header and alternating rows."""
        if not headers:
            return
        if col_widths is None:
            usable = self.w - 2 * self.l_margin - 10
            col_widths = [usable / len(headers)] * len(headers)

        x_start = self.l_margin + 5

        # Header row
        self._check_page_space(14)
        self.set_font("Helvetica", "B", 7.5)
        self.set_fill_color(*self.TABLE_HEADER_BG)
        self.set_text_color(*self.HEADER_FG)
        self.set_draw_color(*self.CARD_BORDER)
        self.set_x(x_start)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, self._safe_text(str(h)), border=1, align="C", fill=True)
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*self.TEXT_PRIMARY)
        for row_idx, row in enumerate(rows):
            self._check_page_space(7)
            if row_idx % 2 == 1:
                self.set_fill_color(*self.TABLE_ALT_ROW)
            else:
                self.set_fill_color(255, 255, 255)
            self.set_x(x_start)
            for i, cell_val in enumerate(row):
                cw = col_widths[i] if i < len(col_widths) else col_widths[-1]
                self.cell(cw, 6, self._safe_text(str(cell_val)), border=1, align=align, fill=True)
            self.ln()

    def _check_page_space(self, needed_mm: float):
        """Add a new page if insufficient space remains."""
        if self.get_y() + needed_mm > self.h - self.b_margin:
            self.add_page()


# ============================================================================
# Section Renderers
# ============================================================================

def _render_cover_page(pdf: PileReportPDF, data: ReportData):
    """Project Details and Table of Contents."""
    pdf.add_page()

    pdf.section_header("Project Details")
    pdf.card_start()
    pdf.kv_row("Project Name", data.project_name)
    pdf.kv_row("Project Number", data.project_number or "-")
    pdf.kv_row("Engineer of Record", data.engineer_of_record or "-")
    pdf.kv_row("Location", data.project_location or "-")
    date_str = data.report_date or datetime.now().strftime("%B %d, %Y")
    pdf.kv_row("Report Date", date_str)
    pdf.card_end()
    pdf.ln(8)

    # Table of Contents
    pdf.section_header("Table of Contents")
    toc_items = [
        ("1", "Basis for Design"),
        ("2", "Design Summary"),
        ("3", "Section Properties"),
        ("4", "Soil Profile and Properties"),
        ("5", "Lateral Analysis Summary"),
        ("6", "Vertical Load Check"),
        ("7", "Pile Head Loads"),
        ("8", "Load Combinations"),
        ("9", "Pile Plot and Results"),
        ("10", "Pile Analysis Summary"),
        ("11", "Warnings and Alerts"),
    ]
    pdf.styled_table(
        headers=["S.No", "Description", "Status"],
        rows=[
            [num, desc, "Included" if _section_available(num, data) else "Skipped"]
            for num, desc in toc_items
        ],
        col_widths=[20, 110, 40],
    )


def _render_basis_for_design(pdf: PileReportPDF, data: ReportData):
    """Basis for Design: units, design limits, scope of work."""
    pdf.add_page()
    pdf.section_header("Basis For Design")

    # Units
    pdf.card_start()
    pdf.sub_header("Units Considered")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(pdf.l_margin + 15)
    pdf.cell(0, 5, "-US Units (lbs, kip, lbs-in, kip-in, ksi, ft, in)")
    pdf.ln(8)
    pdf.card_end()

    # Design Limits
    pdf.card_start()
    pdf.sub_header("Design Limits")
    pdf.kv_row("Top Deflection", f"{data.top_deflection_limit}", "in")
    pdf.kv_row("Grade Deflection", f"{data.grade_deflection_limit}", "in")
    pdf.kv_row("Bottom Deflection", f"{data.bottom_deflection_limit}", "in")
    sec_type = data.section.name[:2] if data.section else "W6"
    pdf.kv_row("Section Type", sec_type)
    pdf.kv_row("Yield Strength", f"{data.yield_strength:.0f}", "ksi")
    pdf.kv_row("Loading Type", data.loading_type)
    pdf.card_end()

    # Scope of work
    pdf.card_start()
    pdf.sub_header("Scope of Work")
    pdf.set_font("Helvetica", "", 9)
    scope = (
        f"The foundation scope of work covers the design of the {data.pile_type} "
        f"pile foundations for the solar tracker structure. Piles have been designed "
        f"for the worst case lateral and uplift loads. Lateral loads are resisted "
        f"through pile bearing and capacities have been calculated to limit the "
        f"overall deflection of the tracker system."
    )
    pdf.set_x(pdf.l_margin + 10)
    pdf.multi_cell(pdf.w - 2 * pdf.l_margin - 20, 5, scope)
    pdf.ln(3)
    pdf.card_end()


def _render_design_summary(pdf: PileReportPDF, data: ReportData):
    """Design Summary table."""
    pdf.add_page()
    pdf.section_header("Design Summary")

    total_length = data.above_grade + data.pile_embedment
    sec_name = data.section.name if data.section else "-"

    pdf.card_start()
    pdf.styled_table(
        headers=["Pile Name", "Section Used", "Above Grade", "Embed (ft)", "Total Length (ft)"],
        rows=[
            ["Pile 1", sec_name, f"{data.above_grade:.1f}",
             f"{data.pile_embedment:.1f}", f"{total_length:.1f}"],
        ],
        col_widths=[35, 30, 30, 30, 35],
    )
    pdf.card_end()

    if data.axial_result:
        pdf.ln(3)
        pdf.card_start()
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_x(pdf.l_margin + 10)
        pdf.cell(0, 5, "*Embed governed by Vertical load check.")
        pdf.ln(4)
        pdf.card_end()


def _render_section_properties(pdf: PileReportPDF, data: ReportData):
    """Section Properties with W-beam diagram and full properties table."""
    if data.section is None:
        return
    pdf.add_page()
    s = data.section
    pdf.section_header(f"Section Properties: {s.name}")

    # W-beam cross-section diagram
    _draw_w_section(pdf, s)
    pdf.ln(5)

    # Two-column property table
    Mp_strong = s.Mp_strong
    Mp_weak = s.Mp_weak

    left_props = [
        ("Section Properties", s.name, ""),
        ("Width", f"{s.width:.2f}", "in"),
        ("Height", f"{s.depth:.2f}", "in"),
        ("Flange Thick", f"{s.tf:.2f}", "in"),
        ("Web Thick", f"{s.tw:.2f}", "in"),
        ("Area", f"{s.area:.2f}", "in2"),
        ("Ixx", f"{s.Ix:.2f}", "in4"),
        ("Iyy", f"{s.Iy:.2f}", "in4"),
        ("Sx", f"{s.Sx:.2f}", "in3"),
        ("Sy", f"{s.Sy:.2f}", "in3"),
    ]
    right_props = [
        ("Zx", f"{s.Zx:.2f}", "in3"),
        ("Zy", f"{s.Zy:.2f}", "in3"),
        ("Perimeter", f"{s.perimeter:.1f}", "in"),
        ("Tip Area", f"{s.tip_area:.2f}", "in2"),
        ("Elastic Modulus", "29000", "ksi"),
        ("Moment Cap Strong", f"{Mp_strong:.2f}", "kip-in"),
        ("Moment Cap Weak", f"{Mp_weak:.2f}", "kip-in"),
        ("Yield Strength", f"{s.fy:.0f}", "ksi"),
        ("", "", ""),
        ("", "", ""),
    ]

    rows = []
    max_len = max(len(left_props), len(right_props))
    for i in range(max_len):
        row = []
        if i < len(left_props):
            lbl, val, unit = left_props[i]
            row.extend([lbl, f"{val} {unit}".strip()])
        else:
            row.extend(["", ""])
        if i < len(right_props):
            lbl, val, unit = right_props[i]
            row.extend([lbl, f"{val} {unit}".strip()])
        else:
            row.extend(["", ""])
        rows.append(row)

    pdf.card_start()
    pdf.styled_table(
        headers=["Description", "Properties", "Description", "Properties"],
        rows=rows,
        col_widths=[40, 30, 40, 30],
    )
    pdf.card_end()


def _draw_w_section(pdf: PileReportPDF, section: SteelSection):
    """Draw a simplified W-beam cross-section diagram."""
    cx = pdf.w / 2
    cy = pdf.get_y() + 40
    scale = 8.0  # mm per inch

    d = section.depth * scale
    bf = section.width * scale
    tf = max(section.tf * scale, 1.5)
    tw = max(section.tw * scale, 1.0)

    pdf.set_draw_color(0, 0, 0)
    pdf.set_fill_color(240, 235, 225)

    # Top flange
    pdf.rect(cx - bf / 2, cy - d / 2, bf, tf, style="FD")
    # Bottom flange
    pdf.rect(cx - bf / 2, cy + d / 2 - tf, bf, tf, style="FD")
    # Web
    pdf.rect(cx - tw / 2, cy - d / 2 + tf, tw, d - 2 * tf, style="FD")

    # Dimension labels
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(40, 40, 45)

    # Height dimension (left side)
    arrow_x = cx - bf / 2 - 12
    pdf.line(arrow_x, cy - d / 2, arrow_x, cy + d / 2)
    pdf.line(arrow_x - 1, cy - d / 2, arrow_x + 1, cy - d / 2)
    pdf.line(arrow_x - 1, cy + d / 2, arrow_x + 1, cy + d / 2)
    pdf.set_xy(arrow_x - 15, cy - 2)
    pdf.cell(15, 4, f"{section.depth:.2f} in", align="C")

    # Width dimension (bottom)
    arrow_y = cy + d / 2 + 4
    pdf.line(cx - bf / 2, arrow_y, cx + bf / 2, arrow_y)
    pdf.line(cx - bf / 2, arrow_y - 1, cx - bf / 2, arrow_y + 1)
    pdf.line(cx + bf / 2, arrow_y - 1, cx + bf / 2, arrow_y + 1)
    pdf.set_xy(cx - 12, arrow_y + 1)
    pdf.cell(24, 4, f"{section.width:.2f} in", align="C")

    pdf.set_y(cy + d / 2 + 12)


def _render_soil_profile(pdf: PileReportPDF, data: ReportData):
    """Soil Profile and Properties table."""
    if not data.soil_layers_raw:
        return
    pdf.add_page()
    pdf.section_header("Soil Profile and Properties")

    if data.water_table_depth is not None:
        pdf.card_start()
        pdf.kv_row("Water Table Depth", f"{data.water_table_depth:.1f}", "ft")
        pdf.card_end()
        pdf.ln(2)

    headers = ["Soil Name", "Layer Start", "Layer End", "Gamma",
               "Phi", "Cu", "N_spt"]
    rows = []
    for ld in data.soil_layers_raw:
        top = ld.get("top_depth", 0)
        bot = top + ld.get("thickness", 0)
        rows.append([
            ld.get("description") or ld.get("soil_type", "-"),
            f"{top:.1f}",
            f"{bot:.1f}",
            f"{ld['gamma']:.0f}" if ld.get("gamma") else "-",
            f"{ld['phi']:.0f}" if ld.get("phi") else "-",
            f"{ld['c_u']:.0f}" if ld.get("c_u") else "-",
            str(ld.get("N_spt", "-")),
        ])

    pdf.card_start()
    pdf.styled_table(headers, rows, col_widths=[35, 22, 22, 20, 18, 20, 18])
    pdf.card_end()

    pdf.ln(5)

    # Units reference table
    pdf.card_start()
    pdf.sub_header("Units")
    unit_rows = [
        ["Soil Layer", "ft"],
        ["Gamma (Unit Weight)", "lbs/ft3"],
        ["Phi (Friction Angle)", "degrees"],
        ["Cu (Cohesion)", "lbs/ft2"],
        ["k / kpy", "lbs/in3"],
    ]
    pdf.styled_table(["Parameter", "Unit"], unit_rows, col_widths=[60, 40])
    pdf.card_end()


def _render_lateral_summary(pdf: PileReportPDF, data: ReportData):
    """Lateral Analysis Summary table (SPile+ Summary page)."""
    result = data.bnwf_result or data.lateral_result
    if result is None:
        return
    pdf.add_page()
    pdf.section_header("Lateral Analysis Summary")

    s = data.section
    if s is None:
        return

    axis = data.bending_axis
    Mp_kip_in = s.Mp_strong if axis == "strong" else s.Mp_weak

    # Extract deflection values
    if isinstance(result, BNWFResult):
        defl = result.deflection_lateral_in
        y_top = float(defl[0]) if len(defl) > 0 else 0.0
        y_ground = float(result.y_ground_lateral)
    else:
        defl = result.deflection_in
        y_top = float(defl[0]) if len(defl) > 0 else 0.0
        y_ground = float(result.y_ground)

    M_max_kip_in = abs(float(result.M_max)) * 12.0 / 1000.0
    stress_ratio = M_max_kip_in / Mp_kip_in if Mp_kip_in > 0 else 0.0

    pdf.card_start()
    pdf.sub_header("Lateral Pile Analysis")
    pdf.styled_table(
        headers=["Pile Name", "Section", "Above Grade (ft)", "Embed (ft)",
                 "Top Defl (in)", "Grade Defl (in)",
                 "Design Moment (kip-in)", "Moment Cap (kip-in)", "Pile Stress"],
        rows=[[
            "Pile 1", s.name, f"{data.above_grade:.1f}",
            f"{data.pile_embedment:.1f}",
            f"{abs(y_top):.2f}", f"{abs(y_ground):.2f}",
            f"{M_max_kip_in:.2f}", f"{Mp_kip_in:.2f}", f"{stress_ratio:.2f}",
        ]],
        col_widths=[18, 17, 20, 16, 20, 20, 25, 25, 18],
    )
    pdf.card_end()


def _render_vertical_load_check(pdf: PileReportPDF, data: ReportData):
    """Vertical Load Check with soil parameters and capacity summary."""
    if data.axial_result is None:
        return
    pdf.add_page()
    pdf.section_header("Vertical Load Check")
    ar = data.axial_result
    s = data.section

    # Layer contributions table
    if ar.layer_contributions:
        pdf.card_start()
        pdf.sub_header("Layer Contributions")
        headers = ["Layer", "Depth (ft)", "Method", "f_s (psf)", "dQ (lbs)"]
        rows = []
        for lc in ar.layer_contributions:
            rows.append([
                str(lc.get("layer", "-")),
                f"{lc.get('depth_ft', 0):.1f}",
                lc.get("method", "-"),
                f"{lc.get('f_s_psf', 0):.1f}",
                f"{lc.get('dQ_lbs', 0):.0f}",
            ])
        # Downsample large tables
        if len(rows) > 30:
            step = max(1, len(rows) // 25)
            rows = rows[::step]
        pdf.styled_table(headers, rows, col_widths=[25, 25, 30, 25, 25])
        pdf.card_end()

    # Capacity Summary
    pdf.ln(3)
    pdf.card_start()
    pdf.sub_header("Vertical Check Summary")
    summary_headers = ["Pile", "Section", "Q_s (lbs)", "Q_b (lbs)",
                       "Q_ult Comp (lbs)", "Q_ult Tens (lbs)",
                       "Q_allow Comp", "Q_allow Tens"]
    summary_rows = [[
        "Pile 1",
        s.name if s else "-",
        f"{ar.Q_s:.0f}",
        f"{ar.Q_b:.0f}",
        f"{ar.Q_ult_compression:.0f}",
        f"{ar.Q_ult_tension:.0f}",
        f"{ar.Q_allow_compression:.0f}",
        f"{ar.Q_allow_tension:.0f}",
    ]]
    pdf.styled_table(summary_headers, summary_rows,
                     col_widths=[16, 16, 22, 22, 24, 24, 22, 22])
    pdf.card_end()

    # LRFD factored resistance
    pdf.ln(3)
    pdf.card_start()
    pdf.sub_header("LRFD Factored Resistance")
    pdf.kv_row("phi Compression", f"{ar.phi_compression:.2f}")
    pdf.kv_row("phi Tension", f"{ar.phi_tension:.2f}")
    pdf.kv_row("Q_r Compression", f"{ar.Q_r_compression:.0f}", "lbs")
    pdf.kv_row("Q_r Tension", f"{ar.Q_r_tension:.0f}", "lbs")
    pdf.card_end()

    # Resistance formulas
    pdf.ln(3)
    pdf.card_start()
    pdf.sub_header("Resistance Formulas")
    pdf.set_font("Helvetica", "", 8)
    formulas = [
        "Uplift Resistance = (Depth x Skin friction) x Perimeter + Self weight",
        "Downward Resistance = (Depth x Skin friction) x Perimeter + End Bearing x Area",
        f"Method: {ar.method}  |  FS Comp: {ar.FS_compression}  |  FS Tens: {ar.FS_tension}",
    ]
    for f_text in formulas:
        pdf.set_x(pdf.l_margin + 10)
        pdf.cell(0, 5, f_text)
        pdf.ln(5)
    pdf.card_end()


def _render_pile_head_loads(pdf: PileReportPDF, data: ReportData):
    """Pile Head Loads table."""
    if data.load_input is None:
        return
    pdf.add_page()
    pdf.section_header("Pile Head Loads")

    li = data.load_input
    pdf.card_start()
    pdf.sub_header("Service Loads (per pile)")
    rows = [
        ["Dead Load", f"{li.dead:.0f}", "lbs"],
        ["Live Load", f"{li.live:.0f}", "lbs"],
        ["Snow Load", f"{li.snow:.0f}", "lbs"],
        ["Wind Uplift", f"{li.wind_up:.0f}", "lbs"],
        ["Wind Downward", f"{li.wind_down:.0f}", "lbs"],
        ["Wind Lateral", f"{li.wind_lateral:.0f}", "lbs"],
        ["Wind Moment at Ground", f"{li.wind_moment:.0f}", "ft-lbs"],
        ["Seismic Lateral", f"{li.seismic_lateral:.0f}", "lbs"],
        ["Seismic Vertical", f"{li.seismic_vertical:.0f}", "lbs"],
        ["Seismic Moment", f"{li.seismic_moment:.0f}", "ft-lbs"],
        ["Lateral Load Height", f"{li.lever_arm:.1f}", "ft"],
    ]
    pdf.styled_table(["Loading Type", "Value", "Unit"], rows,
                     col_widths=[60, 35, 25])
    pdf.card_end()


def _render_load_combinations(pdf: PileReportPDF, data: ReportData):
    """Load Combinations factor table."""
    if data.load_input is None:
        return
    pdf.add_page()
    pdf.section_header("Load Combinations")

    headers = ["Load Case", "V_comp (lbs)", "V_tens (lbs)",
               "H_lat (lbs)", "M_ground (ft-lbs)"]
    cw = [50, 28, 28, 28, 32]

    pdf.card_start()
    if data.design_method in ("LRFD", "Both"):
        cases = generate_lrfd_combinations(data.load_input)
        pdf.sub_header("LRFD Load Combinations (ASCE 7-22)")
        rows = [[lc.name, f"{lc.V_comp:.0f}", f"{lc.V_tens:.0f}",
                 f"{lc.H_lat:.0f}", f"{lc.M_ground:.0f}"] for lc in cases]
        pdf.styled_table(headers, rows, col_widths=cw)

    if data.design_method in ("ASD", "Both"):
        pdf.ln(5)
        cases = generate_asd_combinations(data.load_input)
        pdf.sub_header("ASD Load Combinations (ASCE 7-22)")
        rows = [[lc.name, f"{lc.V_comp:.0f}", f"{lc.V_tens:.0f}",
                 f"{lc.H_lat:.0f}", f"{lc.M_ground:.0f}"] for lc in cases]
        pdf.styled_table(headers, rows, col_widths=cw)
    pdf.card_end()


def _render_depth_profiles(pdf: PileReportPDF, data: ReportData):
    """Depth profile plots and data tables (SPile+ Plot and Results section)."""
    result = data.bnwf_result or data.lateral_result
    if result is None:
        return

    pdf.add_page()
    pdf.section_header("Pile Plot and Results")

    # Pile metadata
    pdf.card_start()
    pdf.sub_header("Pile Report")
    pdf.kv_row("Pile Name", "Pile 1")
    pdf.kv_row("Pile section", data.section.name if data.section else "-")
    pdf.kv_row("Loading type", data.loading_type)
    pdf.card_end()

    # Pile geometry
    pdf.card_start()
    pdf.sub_header("Pile Geometry")
    pdf.kv_row("Pile length above ground", f"{data.above_grade:.1f}", "ft")
    pdf.kv_row("Pile embedment", f"{data.pile_embedment:.1f}", "ft")
    total = data.above_grade + data.pile_embedment
    pdf.kv_row("Total Pile length", f"{total:.1f}", "ft")
    if data.section:
        pile_diam = data.section.depth if data.bending_axis == "strong" else data.section.width
        pdf.kv_row("Pile Diameter", f"{pile_diam:.2f}", "in")
    pdf.card_end()

    # Section properties
    if data.section:
        s = data.section
        pdf.card_start()
        pdf.sub_header("Pile Section Properties")
        pdf.kv_row("Width", f"{s.width:.2f}", "in")
        pdf.kv_row("Height", f"{s.depth:.2f}", "in")
        pdf.kv_row("Flange thick", f"{s.tf:.2f}", "in")
        pdf.kv_row("Web thick", f"{s.tw:.2f}", "in")
        pdf.kv_row("Area", f"{s.area:.2f}", "in2")
        pdf.kv_row("Ixx", f"{s.Ix:.2f}", "in4")
        pdf.kv_row("Iyy", f"{s.Iy:.2f}", "in4")
        pdf.kv_row("Moment capacity strong", f"{s.Mp_strong:.2f}", "kip-in")
        pdf.kv_row("Elastic modulus", "29000", "Ksi")
        pdf.card_end()

    # Four-panel depth profile plot
    plot_buf = _generate_depth_profile_plot(result, data)
    if plot_buf is not None:
        pdf.card_start()
        pdf.sub_header("Pile Plots")
        pdf.image(plot_buf, x=pdf.l_margin + 5,
                  w=pdf.w - 2 * pdf.l_margin - 10, h=80)
        pdf.ln(3)
        pdf.card_end()

    # Full depth data table
    _render_depth_table(pdf, result)


def _generate_depth_profile_plot(result, data: ReportData):
    """Generate 4-panel Plotly figure and export to PNG bytes via kaleido.

    Returns a BytesIO object containing PNG data, or None on failure.
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        return None

    # Extract arrays
    if isinstance(result, BNWFResult):
        depth = np.array(result.depth_ft)
        defl = np.array(result.deflection_lateral_in)
        moment = np.array(result.moment_ft_lbs) * 12.0 / 1000.0  # ft-lbs -> kip-in
        shear = np.array(result.shear_lbs) / 1000.0              # lbs -> kip
        soil_p = np.array(result.soil_reaction_p_lb_in) / 1000.0 # lb/in -> kip
    else:
        depth = np.array(result.depth_ft)
        defl = np.array(result.deflection_in)
        moment = np.array(result.moment_ft_lbs) * 12.0 / 1000.0
        shear = np.array(result.shear_lbs) / 1000.0
        soil_p = np.array(result.soil_reaction_lb_in) / 1000.0

    fig = make_subplots(
        rows=1, cols=4,
        subplot_titles=("Deflection (in)", "Bending Moment (k-in)",
                        "Shear Force(kip)", "Soil Reactions (kip)"),
        shared_yaxes=True,
        horizontal_spacing=0.06,
    )

    line_style = dict(color="royalblue", width=1.5)
    neg_depth = -depth  # Positive depth downward, plot y-axis inverted

    fig.add_trace(go.Scatter(x=defl, y=neg_depth, mode="lines",
                             line=line_style, showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=moment, y=neg_depth, mode="lines",
                             line=line_style, showlegend=False), row=1, col=2)
    fig.add_trace(go.Scatter(x=shear, y=neg_depth, mode="lines",
                             line=line_style, showlegend=False), row=1, col=3)
    fig.add_trace(go.Scatter(x=soil_p, y=neg_depth, mode="lines",
                             line=line_style, showlegend=False), row=1, col=4)

    fig.update_yaxes(title_text="Depth (ft)", row=1, col=1)
    fig.update_layout(
        height=350, width=750,
        margin=dict(l=50, r=20, t=40, b=40),
        font=dict(size=8),
        plot_bgcolor="white",
    )
    for i in range(1, 5):
        fig.update_xaxes(showgrid=True, gridcolor="lightgray", row=1, col=i)
        fig.update_yaxes(showgrid=True, gridcolor="lightgray", row=1, col=i)

    try:
        png_bytes = fig.to_image(format="png", engine="kaleido", scale=2)
        buf = io.BytesIO(png_bytes)
        buf.seek(0)
        return buf
    except Exception:
        return None


def _render_depth_table(pdf: PileReportPDF, result):
    """Full depth data table (Depth, Deflection, Moment, Shear, Soil Reaction)."""
    if isinstance(result, BNWFResult):
        depth = result.depth_ft
        defl = result.deflection_lateral_in
        moment = np.array(result.moment_ft_lbs) * 12.0 / 1000.0
        shear = np.array(result.shear_lbs) / 1000.0
        soil_p = np.array(result.soil_reaction_p_lb_in) / 1000.0
    else:
        depth = result.depth_ft
        defl = result.deflection_in
        moment = np.array(result.moment_ft_lbs) * 12.0 / 1000.0
        shear = np.array(result.shear_lbs) / 1000.0
        soil_p = np.array(result.soil_reaction_lb_in) / 1000.0

    n = len(depth)
    step = max(1, n // 80)
    indices = list(range(0, n, step))
    if indices[-1] != n - 1:
        indices.append(n - 1)

    headers = ["Depth(ft)", "Deflection(in)", "Moment(kip-in)",
               "Shear Force(kip)", "Soil Reaction(kip)"]

    rows = []
    for i in indices:
        rows.append([
            f"{depth[i]:.2f}",
            f"{defl[i]:.2f}",
            f"{moment[i]:.2f}",
            f"{shear[i]:.2f}",
            f"{soil_p[i]:.2f}",
        ])

    pdf.add_page()
    pdf.styled_table(headers, rows, col_widths=[28, 30, 30, 30, 30])


def _render_pile_analysis_summary(pdf: PileReportPDF, data: ReportData):
    """Pile Analysis Summary: deflections, moment, shear, stress, check status."""
    result = data.bnwf_result or data.lateral_result
    if result is None:
        return

    s = data.section
    if s is None:
        return

    pdf.add_page()
    pdf.section_header("Pile Analysis Summary")

    axis = data.bending_axis
    Mp_kip_in = s.Mp_strong if axis == "strong" else s.Mp_weak

    if isinstance(result, BNWFResult):
        defl = result.deflection_lateral_in
        y_top = float(defl[0]) if len(defl) > 0 else 0.0
        y_grade = float(result.y_ground_lateral)
        y_bot = float(defl[-1]) if len(defl) > 0 else 0.0
        M_max_kip_in = abs(float(result.M_max)) * 12.0 / 1000.0
        V_max_kip = float(np.max(np.abs(result.shear_lbs))) / 1000.0
    else:
        defl = result.deflection_in
        y_top = float(defl[0]) if len(defl) > 0 else 0.0
        y_grade = float(result.y_ground)
        y_bot = float(defl[-1]) if len(defl) > 0 else 0.0
        M_max_kip_in = abs(float(result.M_max)) * 12.0 / 1000.0
        V_max_kip = float(np.max(np.abs(result.shear_lbs))) / 1000.0

    stress_pct = int(100 * M_max_kip_in / Mp_kip_in) if Mp_kip_in > 0 else 0
    check = "OK" if stress_pct <= 100 else "FAIL"
    check_note = "(The analysis concluded successfully)" if check == "OK" else "(EXCEEDS CAPACITY)"

    pdf.card_start()
    pdf.sub_header(f"Pile Analysis Summary for Pile 1 - {s.name}")
    pdf.kv_row("Pile top deflection", f"{abs(y_top):.2f}", "in")
    pdf.kv_row("Pile grade deflection", f"{abs(y_grade):.2f}", "in")
    pdf.kv_row("Pile bottom deflection", f"{abs(y_bot):.2f}", "in")
    pdf.kv_row("Pile maximum bending moment", f"{M_max_kip_in:.2f}", "kip-in")
    pdf.kv_row("Pile maximum shear force", f"{V_max_kip:.2f}", "kip")
    pdf.kv_row("Pile stress", f"{stress_pct}", "%")
    pdf.kv_row("Check status", check, note=check_note)
    pdf.card_end()


def _render_group_summary(pdf: PileReportPDF, data: ReportData):
    """Pile Group Analysis summary (conditional)."""
    if data.group_result is None:
        return
    gr = data.group_result
    if gr.n_piles <= 1:
        return

    pdf.add_page()
    pdf.section_header("Pile Group Analysis")

    pdf.card_start()
    pdf.kv_row("Number of piles", f"{gr.n_piles}")
    pdf.kv_row("Configuration", f"{gr.n_rows} rows x {gr.n_cols} columns")
    pdf.kv_row("Spacing", f"{gr.spacing:.0f}", "in")
    pdf.kv_row("s/d ratio", f"{gr.s_over_d:.1f}")
    pdf.kv_row("Axial efficiency (eta)", f"{gr.eta_axial:.3f}")
    pdf.kv_row("Group capacity (governing)", f"{gr.Q_group_governing:,.0f}", "lbs")
    pdf.kv_row("Lateral group efficiency", f"{gr.eta_lateral:.3f}")
    pdf.card_end()

    # p-multiplier table
    if gr.p_multipliers:
        pdf.ln(3)
        pdf.card_start()
        pdf.sub_header("Lateral p-Multipliers by Row")
        rows = [
            [f"Row {r['row']}", r["position"], f"{r['f_m']:.3f}"]
            for r in gr.p_multipliers
        ]
        pdf.styled_table(["Row", "Position", "f_m"], rows,
                         col_widths=[25, 50, 25])
        pdf.card_end()


def _render_warnings(pdf: PileReportPDF, data: ReportData):
    """Warnings and Alerts section."""
    pdf.add_page()
    pdf.section_header("Warnings and Alerts")

    warnings = _collect_warnings(data)
    pdf.card_start()
    if warnings:
        pdf.set_font("Helvetica", "", 9)
        for w in warnings:
            pdf.set_x(pdf.l_margin + 10)
            pdf.multi_cell(pdf.w - 2 * pdf.l_margin - 20, 5, f"- {w}")
            pdf.ln(2)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_x(pdf.l_margin + 10)
        pdf.cell(0, 5, "No warnings or alerts.")
    pdf.ln(3)
    pdf.card_end()


def _collect_warnings(data: ReportData) -> list:
    """Collect all warnings from analysis results and input validation."""
    warnings = []

    if data.lateral_result and not data.lateral_result.converged:
        warnings.append("Lateral analysis did not converge.")
    if data.bnwf_result and not data.bnwf_result.converged:
        warnings.append("BNWF analysis did not converge.")

    if data.lateral_result and data.lateral_result.notes:
        for note in data.lateral_result.notes:
            if "warning" in note.lower() or "limit" in note.lower():
                warnings.append(note)

    if data.bnwf_result and data.bnwf_result.notes:
        for note in data.bnwf_result.notes:
            if "warning" in note.lower() or "limit" in note.lower():
                warnings.append(note)

    if data.axial_result and data.axial_result.notes:
        for note in data.axial_result.notes:
            if "warning" in note.lower() or "limit" in note.lower():
                warnings.append(note)

    # Stress check
    if data.section:
        axis = data.bending_axis
        Mp = data.section.Mp_strong if axis == "strong" else data.section.Mp_weak
        result = data.bnwf_result or data.lateral_result
        if result and Mp > 0:
            M_max_kip_in = abs(float(result.M_max)) * 12.0 / 1000.0
            if M_max_kip_in > Mp:
                warnings.append(
                    f"Maximum moment ({M_max_kip_in:.1f} kip-in) exceeds plastic "
                    f"moment capacity ({Mp:.1f} kip-in) - pile stress ratio > 100%."
                )

    return warnings


# ============================================================================
# TOC Helper
# ============================================================================

def _section_available(section_num: str, data: ReportData) -> bool:
    """Check if a TOC section has data available."""
    checks = {
        "1": True,
        "2": data.section is not None,
        "3": data.section is not None,
        "4": bool(data.soil_layers_raw),
        "5": data.lateral_result is not None or data.bnwf_result is not None,
        "6": data.axial_result is not None,
        "7": data.load_input is not None,
        "8": data.load_input is not None,
        "9": data.lateral_result is not None or data.bnwf_result is not None,
        "10": data.lateral_result is not None or data.bnwf_result is not None,
        "11": True,
    }
    return checks.get(section_num, False)


# ============================================================================
# Main Entry Point
# ============================================================================

def generate_report(data: ReportData) -> bytes:
    """Generate complete SPile+-style PDF report.

    Args:
        data: ReportData with all project info and analysis results.

    Returns:
        PDF file contents as bytes.
    """
    pdf = PileReportPDF()
    pdf.alias_nb_pages()

    _render_cover_page(pdf, data)
    _render_basis_for_design(pdf, data)
    _render_design_summary(pdf, data)
    _render_section_properties(pdf, data)
    _render_soil_profile(pdf, data)
    _render_lateral_summary(pdf, data)
    _render_vertical_load_check(pdf, data)
    _render_pile_head_loads(pdf, data)
    _render_load_combinations(pdf, data)
    _render_depth_profiles(pdf, data)
    _render_pile_analysis_summary(pdf, data)
    _render_group_summary(pdf, data)
    _render_warnings(pdf, data)

    return bytes(pdf.output())
