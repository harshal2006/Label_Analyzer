"""
PDF Report Service — generates a downloadable nutrition analysis report.

Uses reportlab.platypus to build a multi-page PDF with:
  - Page 1: title, product info, and a nutrient summary table.
  - Page 2+: detailed nutrient breakdown with source/usage from Groq.
  - Footer on every page: page number and disclaimer.

Returns a BytesIO buffer so the PDF can be streamed without disk writes.
"""

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

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

    return styles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report_pdf(
    product_info: dict,
    nutrients: dict,
    insights: dict,
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

    Returns
    -------
    BytesIO
        In-memory PDF buffer, ready to be streamed.
    """
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
    # PAGE 1 — Title + Summary Table
    # ==================================================================
    story.append(Paragraph("Nutrition Analysis Report", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Upload #{upload_id}  ·  {upload_date}",
        styles["ReportSubtitle"],
    ))
    story.append(Spacer(1, 8))

    # ── Product info box ──
    story.append(Paragraph(
        f"<b>Product File:</b> {image_path}",
        styles["ReportBody"],
    ))
    story.append(Spacer(1, 16))

    # ── Nutrient summary table ──
    story.append(Paragraph("Nutrient Summary", styles["SectionHeading"]))

    if nutrients:
        table_data = [["Nutrient", "Value"]]
        for name, value in nutrients.items():
            table_data.append([name, str(value)])

        col_widths = [doc.width * 0.55, doc.width * 0.45]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
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
        ]))
        story.append(table)
    else:
        story.append(Paragraph(
            "<i>No nutrients were extracted from this label.</i>",
            styles["ReportBody"],
        ))

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

