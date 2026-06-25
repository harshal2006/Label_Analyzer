"""
Centralized styling for the PDF Nutrition Report.

Provides a unified colour palette, paragraph styles, and table styles
to ensure consistent visual design across the entire document.
"""

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import TableStyle

# ---------------------------------------------------------------------------
# Colour Palette
# ---------------------------------------------------------------------------
PRIMARY = colors.HexColor("#4f46e5")
PRIMARY_LIGHT = colors.HexColor("#818cf8")
DARK_BG = colors.HexColor("#1a1a2e")
ROW_ALT = colors.HexColor("#f0f0f5")
TEXT_DARK = colors.HexColor("#1e1e2e")
TEXT_SECONDARY = colors.HexColor("#6b7280")
BORDER_MUTED = colors.HexColor("#d1d5db")

# Status flags
RED = colors.HexColor("#dc2626")
AMBER = colors.HexColor("#d97706")
GREEN = colors.HexColor("#16a34a")

# Highlights
ALLERGEN_BG = colors.HexColor("#fef2f2")
ALLERGEN_BORDER = RED
GOAL_BG = colors.HexColor("#f8fafc")
GOAL_BORDER = PRIMARY_LIGHT
NO_ALLERGEN_BG = colors.HexColor("#f0fdf4")
NO_ALLERGEN_BORDER = GREEN

# How to Use section
HOW_TO_USE_BG = colors.HexColor("#eff6ff")
HOW_TO_USE_BORDER = colors.HexColor("#3b82f6")

# Ingredient Details section
INGREDIENT_BG = colors.HexColor("#f5f3ff")
INGREDIENT_BORDER = colors.HexColor("#7c3aed")

# Pie chart
PIE_PROTEIN = colors.HexColor("#6366f1")  # indigo
PIE_CARBS = colors.HexColor("#06b6d4")    # cyan
PIE_FAT = colors.HexColor("#f59e0b")      # amber


# ---------------------------------------------------------------------------
# Paragraph Styles
# ---------------------------------------------------------------------------
def get_report_styles() -> dict[str, ParagraphStyle]:
    """Build custom paragraph styles for the report."""
    base_styles = getSampleStyleSheet()
    styles = {}

    styles["ReportTitle"] = ParagraphStyle(
        "ReportTitle",
        parent=base_styles["Title"],
        fontSize=22,
        leading=28,
        textColor=PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=6,
    )

    styles["ReportSubtitle"] = ParagraphStyle(
        "ReportSubtitle",
        parent=base_styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=TEXT_SECONDARY,
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    styles["SectionHeading"] = ParagraphStyle(
        "SectionHeading",
        parent=base_styles["Heading2"],
        fontSize=16,
        leading=20,
        textColor=PRIMARY,
        spaceBefore=16,
        spaceAfter=10,
    )

    styles["NutrientHeading"] = ParagraphStyle(
        "NutrientHeading",
        parent=base_styles["Heading3"],
        fontSize=12,
        leading=16,
        textColor=TEXT_DARK,
        spaceBefore=14,
        spaceAfter=4,
    )

    styles["ReportBody"] = ParagraphStyle(
        "ReportBody",
        parent=base_styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=TEXT_DARK,
        spaceAfter=4,
    )

    styles["ReportLabel"] = ParagraphStyle(
        "ReportLabel",
        parent=base_styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=TEXT_SECONDARY,
        spaceAfter=2,
    )

    styles["Disclaimer"] = ParagraphStyle(
        "Disclaimer",
        parent=base_styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=TEXT_SECONDARY,
        alignment=TA_LEFT,
        fontName="Helvetica-Oblique",
    )

    styles["AllergenText"] = ParagraphStyle(
        "AllergenText",
        parent=base_styles["Normal"],
        fontSize=11,
        leading=15,
        textColor=RED,
        alignment=TA_LEFT,
    )

    styles["NoAllergenText"] = ParagraphStyle(
        "NoAllergenText",
        parent=base_styles["Normal"],
        fontSize=11,
        leading=15,
        textColor=GREEN,
        alignment=TA_LEFT,
    )

    styles["GoalText"] = ParagraphStyle(
        "GoalText",
        parent=base_styles["Normal"],
        fontSize=11,
        leading=16,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
    )

    styles["ProductTypeBadge"] = ParagraphStyle(
        "ProductTypeBadge",
        parent=base_styles["Normal"],
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#1e40af"),
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
        spaceAfter=8,
    )

    styles["HowToUseText"] = ParagraphStyle(
        "HowToUseText",
        parent=base_styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
        spaceAfter=4,
    )

    styles["IngredientSource"] = ParagraphStyle(
        "IngredientSource",
        parent=base_styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=TEXT_SECONDARY,
        alignment=TA_LEFT,
        spaceAfter=2,
    )

    return styles


# ---------------------------------------------------------------------------
# Table Styles
# ---------------------------------------------------------------------------
def get_data_table_style(num_rows: int) -> TableStyle:
    """Standard table style with alternating row banding and subtle grid lines."""
    cmds = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        # Body rows
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
        ("TOPPADDING", (0, 1), (-1, -1), 7),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_MUTED),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]

    # Alternating row banding
    for i in range(2, num_rows, 2):
        cmds.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))

    return TableStyle(cmds)


def get_allergen_table_style(num_rows: int) -> TableStyle:
    """Table style specifically for allergens, tinted red."""
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
        ("TOPPADDING", (0, 1), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, ALLERGEN_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]

    for i in range(2, num_rows, 2):
        cmds.append(("BACKGROUND", (0, i), (-1, i), ALLERGEN_BG))

    return TableStyle(cmds)


def get_highlight_box_style(bg_color: colors.Color, border_color: colors.Color) -> TableStyle:
    """Style for a single-cell table used as a highlight box (Goal, Warnings)."""
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 1.5, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
    ])
