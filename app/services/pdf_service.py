"""
PDF Report Service — generates a downloadable nutrition analysis report.

Uses reportlab.platypus to build a multi-page PDF with:
  - Page 1: title, product summary, "How to Use" section, allergen info,
    nutrient summary table with %DV/flags, and a macronutrient pie chart.
  - Page 2+: detailed ingredient breakdown with source & role from Groq.
  - Footer on every page: page number and disclaimer.

Returns a BytesIO buffer so the PDF can be streamed without disk writes.
"""

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Line
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.utils.pdf_styles import (
    ALLERGEN_BG,
    ALLERGEN_BORDER,
    GOAL_BG,
    GOAL_BORDER,
    HOW_TO_USE_BG,
    HOW_TO_USE_BORDER,
    INGREDIENT_BG,
    INGREDIENT_BORDER,
    NO_ALLERGEN_BG,
    NO_ALLERGEN_BORDER,
    ROW_ALT,
    BORDER_MUTED,
    PIE_CARBS,
    PIE_FAT,
    PIE_PROTEIN,
    PRIMARY_LIGHT,
    RED,
    AMBER,
    GREEN,
    get_allergen_table_style,
    get_data_table_style,
    get_highlight_box_style,
    get_report_styles,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page footer callback
# ---------------------------------------------------------------------------
def _footer(canvas, doc):
    """Draw page number, disclaimer, and top border line on every page footer."""
    canvas.saveState()
    page_num = canvas.getPageNumber()
    width, height = A4

    styles = get_report_styles()
    
    # Top border line for footer
    canvas.setStrokeColor(PRIMARY_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 18 * mm, width - 20 * mm, 18 * mm)

    # Page number — right side
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawRightString(width - 20 * mm, 12 * mm, f"Page {page_num}")

    # Disclaimer — left side
    disclaimer_text = (
        "This report is for informational purposes only and does not "
        "constitute medical advice."
    )
    p = Paragraph(disclaimer_text, styles["Disclaimer"])
    # We draw the paragraph at a specific absolute position
    w, h = p.wrap(width - 60 * mm, 10 * mm)
    p.drawOn(canvas, 20 * mm, 12 * mm)

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Drawing Helpers
# ---------------------------------------------------------------------------
def _build_divider(width: float) -> Drawing:
    """Create a thin horizontal divider line."""
    d = Drawing(width, 10)
    line = Line(0, 5, width, 5)
    line.strokeColor = colors.HexColor("#e5e7eb")
    line.strokeWidth = 0.5
    d.add(line)
    return d


def _build_macro_pie(macro_split: dict, doc_width: float) -> Drawing:
    """Create a macro pie chart Drawing with legend."""
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
            f"{protein:.1f}%",
            f"{carbs:.1f}%",
            f"{fat:.1f}%",
        ]
        pie.slices[0].fillColor = PIE_PROTEIN
        pie.slices[1].fillColor = PIE_CARBS
        pie.slices[2].fillColor = PIE_FAT

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
            (PIE_PROTEIN, f"Protein  ({protein:.1f}%)"),
            (PIE_CARBS,   f"Carbs    ({carbs:.1f}%)"),
            (PIE_FAT,     f"Fat      ({fat:.1f}%)"),
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
    primary_goal: str,
    ingredient_details: list[dict] | None = None,
    how_to_use: dict | None = None,
    dv_flags: dict | None = None,
    allergens: list[dict] | None = None,
    macro_split: dict | None = None,
    health_score: float | None = None,
    health_reasoning: str | None = None,
) -> BytesIO:
    """Generate a styled PDF nutrition report and return it as a BytesIO buffer.

    Parameters
    ----------
    product_info : dict
        Basic upload metadata (upload_id, image_path, uploaded_at).
    nutrients : dict
        ``{name: "value unit"}`` dict for the nutrition table.
    primary_goal : str
        2-3 sentence product purpose summary from Groq.
    ingredient_details : list[dict] | None
        List of ``{"name", "source", "role"}`` dicts for each ingredient.
    how_to_use : dict | None
        ``{"product_type", "usage_instructions", "cautions"}`` from Groq.
    dv_flags : dict | None
        ``{name: {"percent_dv": float, "flag": str}}``.
    allergens : list[dict] | None
        List of detected allergens with matched ingredients.
    macro_split : dict | None
        ``{"protein_pct", "carbs_pct", "fat_pct"}``.
    """
    ingredient_details = ingredient_details or []
    how_to_use = how_to_use or {}
    dv_flags = dv_flags or {}
    allergens = allergens or []
    macro_split = macro_split or {}

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=25 * mm,
        bottomMargin=30 * mm,  # extra space for footer
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="Nutrition Analysis Report",
        author="Nutrition Label Analyzer",
    )

    styles = get_report_styles()
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
    # PAGE 1 — Header block
    # ==================================================================
    story.append(Paragraph("Nutrition Analysis Report", styles["ReportTitle"]))
    story.append(Paragraph(
        f"{product_name}<br/>"
        f"Upload #{upload_id}  ·  {upload_date}",
        styles["ReportSubtitle"],
    ))
    story.append(_build_divider(doc.width))
    story.append(Spacer(1, 16))

    # ==================================================================
    # PAGE 1 — Health Score Section
    # ==================================================================
    if health_score is not None:
        story.append(Paragraph("Health Score", styles["SectionHeading"]))
        
        if health_score >= 8.0:
            qualitative = "Excellent"
            color_hex = GREEN.hexval()
        elif health_score >= 6.0:
            qualitative = "Good"
            color_hex = GREEN.hexval()
        elif health_score >= 4.0:
            qualitative = "Fair"
            color_hex = AMBER.hexval()
        else:
            qualitative = "Poor"
            color_hex = RED.hexval()
            
        score_text = f"<font color='{color_hex}'><b>{health_score:.1f} / 10.0</b> \u2014 {qualitative}</font>"
        
        score_table = Table(
            [[
                Paragraph(score_text, styles["ProductTypeBadge"]),
                Paragraph(health_reasoning or "No reasoning provided.", styles["ReportBody"])
            ]],
            colWidths=[doc.width * 0.35, doc.width * 0.65],
        )
        score_table.setStyle(get_highlight_box_style(ROW_ALT, BORDER_MUTED))
        story.append(score_table)
        story.append(Spacer(1, 20))

    # ==================================================================
    # PAGE 1 — Primary Goal Section
    # ==================================================================
    if primary_goal:
        story.append(Paragraph("Product Summary", styles["SectionHeading"]))
        goal_table = Table(
            [[Paragraph(primary_goal, styles["GoalText"])]],
            colWidths=[doc.width],
        )
        goal_table.setStyle(get_highlight_box_style(GOAL_BG, GOAL_BORDER))
        story.append(goal_table)
        story.append(Spacer(1, 20))

    # ==================================================================
    # PAGE 1 — How to Use This Product
    # ==================================================================
    if how_to_use:
        story.append(Paragraph("How to Use This Product", styles["SectionHeading"]))

        product_type = how_to_use.get("product_type", "Nutritional Supplement")
        usage_instructions = how_to_use.get("usage_instructions", "")
        cautions = how_to_use.get("cautions", "")

        # Build content for the highlight box
        content_parts = []
        content_parts.append(
            Paragraph(f"Product Type: {product_type}", styles["ProductTypeBadge"])
        )
        if usage_instructions:
            content_parts.append(
                Paragraph(
                    f"<b>Recommended Usage:</b> {usage_instructions}",
                    styles["HowToUseText"],
                )
            )
        if cautions:
            content_parts.append(
                Paragraph(
                    f"<b>Cautions &amp; Tips:</b> {cautions}",
                    styles["HowToUseText"],
                )
            )

        # Wrap all paragraphs in a single-cell table for the highlight box
        inner_table = Table(
            [[p] for p in content_parts],
            colWidths=[doc.width - 28],  # account for box padding
        )
        inner_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

        outer_table = Table(
            [[inner_table]],
            colWidths=[doc.width],
        )
        outer_table.setStyle(get_highlight_box_style(HOW_TO_USE_BG, HOW_TO_USE_BORDER))
        story.append(outer_table)
        story.append(Spacer(1, 20))

    # ==================================================================
    # PAGE 1 — Allergen Section
    # ==================================================================
    story.append(Paragraph("Allergen Information", styles["SectionHeading"]))
    if allergens:
        table_data = [["Allergen", "Matched Ingredient(s)", "Prominence"]]
        for allergen_dict in allergens:
            alg_name = allergen_dict.get("allergen", "")
            matched_list = allergen_dict.get("matched_ingredients", [])
            matched_str = ", ".join(matched_list)
            prominence = allergen_dict.get("prominence", "Minor / Trace")
            table_data.append([alg_name, matched_str, prominence])
            
        col_widths = [doc.width * 0.30, doc.width * 0.45, doc.width * 0.25]
        alg_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        alg_table.setStyle(get_allergen_table_style(len(table_data)))
        story.append(alg_table)
    else:
        # Green confirmation box
        safe_table = Table(
            [[Paragraph("✓ No major allergens detected.", styles["NoAllergenText"])]],
            colWidths=[doc.width],
        )
        safe_table.setStyle(get_highlight_box_style(NO_ALLERGEN_BG, NO_ALLERGEN_BORDER))
        story.append(safe_table)

    story.append(Spacer(1, 20))

    # ==================================================================
    # PAGE 1 — Nutrient Summary Table
    # ==================================================================
    story.append(Paragraph("Nutrition Summary", styles["SectionHeading"]))

    if nutrients:
        has_dv = bool(dv_flags)
        if has_dv:
            table_data = [["Nutrient", "Value", "%DV", "Flag"]]
            col_widths = [
                doc.width * 0.40,
                doc.width * 0.25,
                doc.width * 0.15,
                doc.width * 0.20,
            ]
        else:
            table_data = [["Nutrient", "Value"]]
            col_widths = [doc.width * 0.55, doc.width * 0.45]

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

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Base table style
        tstyle = get_data_table_style(len(table_data))
        
        # Add color overrides for flags
        if has_dv:
            flag_col = 3
            for row_idx in range(1, len(table_data)):
                flag_val = table_data[row_idx][flag_col] if len(table_data[row_idx]) > flag_col else ""
                if flag_val == "High":
                    tstyle.add("TEXTCOLOR", (flag_col, row_idx), (flag_col, row_idx), RED)
                    tstyle.add("FONTNAME", (flag_col, row_idx), (flag_col, row_idx), "Helvetica-Bold")
                elif flag_val == "Low":
                    tstyle.add("TEXTCOLOR", (flag_col, row_idx), (flag_col, row_idx), AMBER)
                elif flag_val == "Moderate":
                    tstyle.add("TEXTCOLOR", (flag_col, row_idx), (flag_col, row_idx), GREEN)
                    
        table.setStyle(tstyle)
        story.append(table)
    else:
        story.append(Paragraph(
            "<i>No nutrients were extracted from this label.</i>",
            styles["ReportBody"],
        ))

    story.append(Spacer(1, 20))

    # ==================================================================
    # PAGE 1 — Macronutrient pie chart
    # ==================================================================
    if macro_split and any(v > 0 for v in macro_split.values()):
        story.append(Paragraph("Macronutrient Breakdown", styles["SectionHeading"]))
        pie_drawing = _build_macro_pie(macro_split, doc.width)
        story.append(pie_drawing)
        story.append(Spacer(1, 20))

    # ==================================================================
    # PAGE 2+ — Ingredient Details
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("Ingredient Details", styles["SectionHeading"]))
    story.append(Spacer(1, 10))

    if ingredient_details:
        # Group ingredients by category
        grouped_ingredients = {}
        for ing in ingredient_details:
            cat = ing.get("category", "Other")
            if cat not in grouped_ingredients:
                grouped_ingredients[cat] = []
            grouped_ingredients[cat].append(ing)

        # Render each category
        # Defined display order
        display_order = ["Protein Sources", "Flavoring & Sweeteners", "Additives & Emulsifiers", "Other"]
        
        for category in display_order:
            if category in grouped_ingredients:
                story.append(Spacer(1, 10))
                story.append(Paragraph(category, styles["SubsectionHeading"]))
                story.append(Spacer(1, 5))
                story.append(_build_divider(doc.width))
                story.append(Spacer(1, 10))
                
                for ing in grouped_ingredients[category]:
                    name = ing.get("name", "Unknown")
                    source = ing.get("source", "Information not available.")
                    role = ing.get("role", "Information not available.")

                    story.append(Paragraph(
                        f"<b>{name}</b>",
                        styles["NutrientHeading"],
                    ))

                    # "What it is" — source / origin
                    story.append(Paragraph("<b>What it is:</b>", styles["ReportLabel"]))
                    story.append(Paragraph(source, styles["ReportBody"]))

                    # "Why it's here" — functional role in this product
                    story.append(Paragraph("<b>Why it's here:</b>", styles["ReportLabel"]))
                    story.append(Paragraph(role, styles["ReportBody"]))

                    story.append(Spacer(1, 10))
    else:
        story.append(Paragraph(
            "<i>No detailed ingredient information available for this report.</i>",
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
