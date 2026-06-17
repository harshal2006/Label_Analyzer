"""
PDF Report Service — generates a downloadable nutrition analysis report.

Uses reportlab.platypus to build a multi-page PDF with:
  - Page 1: title, allergen warning, nutrient summary table with %DV/flags,
    and a macronutrient pie chart.
  - Page 2+: detailed nutrient breakdown with source/usage from Groq.
  - Footer on every page: page number and disclaimer.

Returns a BytesIO buffer so the PDF can be streamed without disk writes.
"""

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
_PRIMARY = colors.HexColor("#4f46e5")
_PRIMARY_LIGHT = colors.HexColor("#818cf8")
_ACCENT = colors.HexColor("#06d6a0")
_DARK_BG = colors.HexColor("#1a1a2e")
_HEADER_BG = colors.HexColor("#4f46e5")
_HEADER_TEXT = colors.white
_ROW_ALT = colors.HexColor("#f0f0f5")
_TEXT_DARK = colors.HexColor("#1e1e2e")
_TEXT_SECONDARY = colors.HexColor("#6b7280")

_RED = colors.HexColor("#dc2626")
_AMBER = colors.HexColor("#d97706")
_GREEN = colors.HexColor("#16a34a")
_ALLERGEN_BG = colors.HexColor("#fef2f2")
_ALLERGEN_BORDER = colors.HexColor("#dc2626")

# Pie chart colours
_PIE_PROTEIN = colors.HexColor("#6366f1")  # indigo
_PIE_CARBS = colors.HexColor("#06b6d4")    # cyan
_PIE_FAT = colors.HexColor("#f59e0b")      # amber

_DISCLAIMER = (
    "This report is for informational purposes only and does not "
    "constitute medical advice."
)


# ---------------------------------------------------------------------------
# Page footer callback
# ---------------------------------------------------------------------------
def _footer(canvas, doc):
    """Draw page number and disclaimer on every page."""
    canvas.saveState()
    page_num = canvas.getPageNumber()
    width, height = A4

    # Page number — right side
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_TEXT_SECONDARY)
    canvas.drawRightString(width - 20 * mm, 12 * mm, f"Page {page_num}")

    # Disclaimer — left side
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_TEXT_SECONDARY)
    canvas.drawString(20 * mm, 12 * mm, _DISCLAIMER)

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------
def _get_styles():
    """Build custom paragraph styles for the report."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=28,
        textColor=_PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=_TEXT_SECONDARY,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))

    styles.add(ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=16,
        leading=20,
        textColor=_PRIMARY,
        spaceBefore=16,
        spaceAfter=10,
    ))

    styles.add(ParagraphStyle(
        "NutrientHeading",
        parent=styles["Heading3"],
        fontSize=12,
        leading=16,
        textColor=_TEXT_DARK,
        spaceBefore=14,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=_TEXT_DARK,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        "ReportLabel",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=_TEXT_SECONDARY,
        spaceAfter=2,
    ))

    styles.add(ParagraphStyle(
        "AllergenText",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        textColor=_RED,
        alignment=TA_LEFT,
        spaceAfter=0,
    ))

    return styles


# ---------------------------------------------------------------------------
# Pie chart builder
# ---------------------------------------------------------------------------
def _build_macro_pie(macro_split: dict, doc_width: float) -> Drawing:
    """Create a macro pie chart Drawing with legend.

    Parameters
    ----------
    macro_split:
        ``{"protein_pct": float, "carbs_pct": float, "fat_pct": float}``
    doc_width:
        Available document width for sizing.
    """
    drawing_width = min(doc_width, 400)
    drawing_height = 180
    d = Drawing(drawing_width, drawing_height)

    pie = Pie()
    pie.x = 40
    pie.y = 10
    pie.width = 140
    pie.height = 140

    protein = macro_split.get("protein_pct", 0)
    carbs = macro_split.get("carbs_pct", 0)
    fat = macro_split.get("fat_pct", 0)

    # Avoid empty pie (all zeros) — show a placeholder slice
    if protein + carbs + fat <= 0:
        pie.data = [100]
        pie.labels = ["No data"]
        pie.slices[0].fillColor = colors.HexColor("#d1d5db")
    else:
        pie.data = [protein, carbs, fat]
        pie.labels = [
            f"{protein:.0f}%",
            f"{carbs:.0f}%",
            f"{fat:.0f}%",
        ]
        pie.slices[0].fillColor = _PIE_PROTEIN
        pie.slices[1].fillColor = _PIE_CARBS
        pie.slices[2].fillColor = _PIE_FAT

    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    pie.sideLabels = True
    pie.sideLabelsOffset = 0.1

    d.add(pie)

    # Legend
    legend = Legend()
    legend.x = 230
    legend.y = 110
    legend.dx = 10
    legend.dy = 10
    legend.deltay = 14
    legend.fontName = "Helvetica"
    legend.fontSize = 9

    if protein + carbs + fat > 0:
        legend.colorNamePairs = [
            (_PIE_PROTEIN, f"Protein  ({protein:.1f}%)"),
            (_PIE_CARBS,   f"Carbs    ({carbs:.1f}%)"),
            (_PIE_FAT,     f"Fat      ({fat:.1f}%)"),
        ]
    else:
        legend.colorNamePairs = [
            (colors.HexColor("#d1d5db"), "No macro data available"),
        ]

    d.add(legend)
    return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report_pdf(
    product_info: dict,
    nutrients: dict,
    insights: dict,
    dv_flags: dict | None = None,
    allergens: list[str] | None = None,
    macro_split: dict | None = None,
) -> BytesIO:
    """Generate a styled PDF nutrition report and return it as a BytesIO buffer.

    Parameters
    ----------
    product_info:
        Dict with keys ``upload_id`` (int), ``image_path`` (str),
        ``uploaded_at`` (str or datetime).
    nutrients:
        Dict mapping nutrient names to display strings, e.g.
        ``{"Protein": "24 g", "Sodium": "200 mg"}``.
    insights:
        Dict mapping nutrient names to
        ``{"source": "...", "usage": "..."}``.
    dv_flags:
        Optional dict from ``calculate_dv_flags``, e.g.
        ``{"Sodium": {"percent_dv": 8.7, "flag": "Moderate"}}``.
    allergens:
        Optional list of detected allergen names, e.g. ``["Milk", "Soy"]``.
    macro_split:
        Optional dict from ``calculate_macro_split``, e.g.
        ``{"protein_pct": 30.0, "carbs_pct": 45.0, "fat_pct": 25.0}``.

    Returns
    -------
    BytesIO
        In-memory PDF buffer, ready to be streamed.
    """
    dv_flags = dv_flags or {}
    allergens = allergens or []
    macro_split = macro_split or {}

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="Nutrition Analysis Report",
        author="Nutrition Label Analyzer",
    )

    styles = _get_styles()
    story: list = []

    # ── Derive product name from image path ──
    image_path = product_info.get("image_path", "Unknown")
    product_name = Path(image_path).stem.replace("_", " ").replace("-", " ").title()
    upload_id = product_info.get("upload_id", "—")

    uploaded_at = product_info.get("uploaded_at", "")
    if isinstance(uploaded_at, datetime):
        upload_date = uploaded_at.strftime("%B %d, %Y at %I:%M %p")
    elif uploaded_at:
        upload_date = str(uploaded_at)
    else:
        upload_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # ==================================================================
    # PAGE 1 — Title + Allergen Warning + Summary Table + Pie Chart
    # ==================================================================
    story.append(Paragraph("Nutrition Analysis Report", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Upload #{upload_id}  ·  {upload_date}",
        styles["ReportSubtitle"],
    ))

    # ── Allergen warning box (only if allergens detected) ──
    if allergens:
        allergen_text = f"⚠  Contains: {', '.join(allergens)}"
        allergen_table = Table(
            [[Paragraph(allergen_text, styles["AllergenText"])]],
            colWidths=[doc.width],
        )
        allergen_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _ALLERGEN_BG),
            ("BOX", (0, 0), (-1, -1), 1.5, _ALLERGEN_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(allergen_table)
        story.append(Spacer(1, 12))

    # ── Product info box ──
    story.append(Paragraph(
        f"<b>Product File:</b> {image_path}",
        styles["ReportBody"],
    ))
    story.append(Spacer(1, 12))

    # ── Nutrient summary table (now with %DV and Flag columns) ──
    story.append(Paragraph("Nutrient Summary", styles["SectionHeading"]))

    if nutrients:
        has_dv = bool(dv_flags)
        if has_dv:
            table_data = [["Nutrient", "Value", "%DV", "Flag"]]
        else:
            table_data = [["Nutrient", "Value"]]

        for name, value in nutrients.items():
            row = [name, str(value)]
            if has_dv:
                dv_info = dv_flags.get(name)
                if dv_info:
                    row.append(f"{dv_info['percent_dv']:.1f}%")
                    row.append(dv_info["flag"])
                else:
                    row.append("—")
                    row.append("—")
            table_data.append(row)

        if has_dv:
            col_widths = [
                doc.width * 0.40,
                doc.width * 0.25,
                doc.width * 0.15,
                doc.width * 0.20,
            ]
        else:
            col_widths = [doc.width * 0.55, doc.width * 0.45]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Base style commands
        style_cmds = [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_TEXT),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            # Body rows
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
            ("TOPPADDING", (0, 1), (-1, -1), 7),
            # Alternating row backgrounds
            *[
                ("BACKGROUND", (0, i), (-1, i), _ROW_ALT)
                for i in range(2, len(table_data), 2)
            ],
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]

        # Colour-code flag cells (column index 3 when %DV columns are present)
        if has_dv:
            flag_col = 3
            for row_idx in range(1, len(table_data)):
                flag_val = table_data[row_idx][flag_col] if len(table_data[row_idx]) > flag_col else ""
                if flag_val == "High":
                    style_cmds.append(("TEXTCOLOR", (flag_col, row_idx), (flag_col, row_idx), _RED))
                    style_cmds.append(("FONTNAME", (flag_col, row_idx), (flag_col, row_idx), "Helvetica-Bold"))
                elif flag_val == "Low":
                    style_cmds.append(("TEXTCOLOR", (flag_col, row_idx), (flag_col, row_idx), _AMBER))
                elif flag_val == "Moderate":
                    style_cmds.append(("TEXTCOLOR", (flag_col, row_idx), (flag_col, row_idx), _GREEN))

        table.setStyle(TableStyle(style_cmds))
        story.append(table)
    else:
        story.append(Paragraph(
            "<i>No nutrients were extracted from this label.</i>",
            styles["ReportBody"],
        ))

    # ── Macronutrient pie chart ──
    if macro_split and any(v > 0 for v in macro_split.values()):
        story.append(Spacer(1, 16))
        story.append(Paragraph("Macronutrient Split", styles["SectionHeading"]))
        pie_drawing = _build_macro_pie(macro_split, doc.width)
        story.append(pie_drawing)

    # ==================================================================
    # PAGE 2+ — Detailed Nutrient Breakdown
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("Detailed Nutrient Breakdown", styles["SectionHeading"]))
    story.append(Spacer(1, 6))

    if nutrients and insights:
        for name, value in nutrients.items():
            nutrient_insight = insights.get(name, {})
            source = nutrient_insight.get("source", "Information not available.")
            usage = nutrient_insight.get("usage", "Information not available.")

            # Nutrient subheading
            story.append(Paragraph(
                f"<b>{name}</b>  —  {value}",
                styles["NutrientHeading"],
            ))

            # Source paragraph
            story.append(Paragraph("<b>Source:</b>", styles["ReportLabel"]))
            story.append(Paragraph(source, styles["ReportBody"]))

            # Usage paragraph
            story.append(Paragraph("<b>Usage in this Product:</b>", styles["ReportLabel"]))
            story.append(Paragraph(usage, styles["ReportBody"]))

            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph(
            "<i>No detailed nutrient information available for this report.</i>",
            styles["ReportBody"],
        ))

    # ── Build the PDF ──
    try:
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    except Exception as exc:
        logger.exception("Failed to build PDF report: %s", exc)
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    buf.seek(0)
    logger.info("PDF report generated successfully (%d bytes).", buf.getbuffer().nbytes)
    return buf
