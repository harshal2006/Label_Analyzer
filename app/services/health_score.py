"""
Deterministic Health Score Calculator — rule-based, no LLM.

Computes a health score (1-10) from nutrient %DV data and ingredient
lists.  Designed to produce a realistic spread:
  - 2-3 for junk / ultra-processed products
  - 5-6 for average products
  - 8-9 for clean / nutrient-dense products

All weights and thresholds are defined as named constants at the top
of this module for easy tuning.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.utils.nutrition_reference import DAILY_VALUES

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# TUNABLE CONSTANTS — adjust these to shift scoring behaviour
# ═══════════════════════════════════════════════════════════════════════

# Starting baseline (middle of the 1-10 range)
BASELINE_SCORE: float = 5.0

# ── Negative nutrient penalties ──────────────────────────────────────
# Each entry: (nutrient_synonyms, penalty_tiers)
# penalty_tiers: list of (threshold_%DV, penalty_points)
# Applied cumulatively: if %DV >= threshold, subtract penalty.
NEGATIVE_NUTRIENT_PENALTIES: list[tuple[list[str], list[tuple[float, float]]]] = [
    # Saturated Fat — DV = 20 g
    (
        ["Saturated Fat"],
        [
            (5,  0.3),   # >5% DV:  mild concern
            (15, 0.5),   # >15% DV: moderate
            (30, 0.7),   # >30% DV: high
            (50, 0.5),   # >50% DV: very high (extra)
        ],
    ),
    # Trans Fat — DV = 2 g (any amount is bad)
    (
        ["Trans Fat"],
        [
            (1,  0.5),   # any detectable amount
            (25, 0.8),   # >25% DV (>0.5 g)
            (50, 0.7),   # >50% DV (>1 g)
        ],
    ),
    # Added Sugars — DV = 50 g
    (
        ["Added Sugars", "Added Sugar"],
        [
            (10, 0.3),   # >10% DV
            (25, 0.5),   # >25% DV
            (50, 0.7),   # >50% DV
            (75, 0.5),   # >75% DV (extra)
        ],
    ),
    # Total Sugars (fallback if Added Sugars not found) — DV = 50 g
    (
        ["Total Sugars", "Sugar", "Sugars"],
        [
            (20, 0.2),   # >20% DV
            (40, 0.4),   # >40% DV
            (60, 0.4),   # >60% DV
        ],
    ),
    # Sodium — DV = 2300 mg
    (
        ["Sodium"],
        [
            (10, 0.2),   # >10% DV
            (25, 0.4),   # >25% DV
            (50, 0.5),   # >50% DV
            (75, 0.4),   # >75% DV (extra)
        ],
    ),
    # Cholesterol — DV = 300 mg
    (
        ["Cholesterol"],
        [
            (20, 0.2),
            (40, 0.3),
            (60, 0.3),
        ],
    ),
]

# ── Positive nutrient bonuses ────────────────────────────────────────
# Same structure: (nutrient_synonyms, bonus_tiers)
POSITIVE_NUTRIENT_BONUSES: list[tuple[list[str], list[tuple[float, float]]]] = [
    # Protein — DV = 50 g  (strong quality signal)
    (
        ["Protein"],
        [
            (10, 0.4),    # >10% DV
            (25, 0.5),    # >25% DV
            (40, 0.5),    # >40% DV
            (60, 0.4),    # >60% DV
        ],
    ),
    # Dietary Fiber — DV = 28 g  (strong quality signal)
    (
        ["Dietary Fiber", "Dietary Fibre", "Fiber", "Fibre"],
        [
            (10, 0.4),
            (20, 0.4),
            (35, 0.4),
        ],
    ),
    # Vitamin D — DV = 20 mcg
    (
        ["Vitamin D"],
        [
            (10, 0.2),
            (25, 0.2),
        ],
    ),
    # Calcium — DV = 1300 mg
    (
        ["Calcium"],
        [
            (10, 0.2),
            (25, 0.2),
        ],
    ),
    # Iron — DV = 18 mg
    (
        ["Iron"],
        [
            (10, 0.2),
            (25, 0.2),
        ],
    ),
    # Potassium — DV = 4700 mg
    (
        ["Potassium"],
        [
            (10, 0.2),
            (25, 0.2),
        ],
    ),
    # Vitamin C — DV = 90 mg
    (
        ["Vitamin C"],
        [
            (10, 0.15),
            (25, 0.15),
        ],
    ),
    # Vitamin A — DV = 900 mcg
    (
        ["Vitamin A"],
        [
            (10, 0.15),
            (25, 0.15),
        ],
    ),
]

# ── Clean label bonus ────────────────────────────────────────────────
# If total negative nutrient penalty is below this threshold, award a
# bonus for having a genuinely clean nutritional profile.
CLEAN_LABEL_PENALTY_THRESHOLD: float = 0.3   # max negative penalty to qualify
CLEAN_LABEL_BONUS: float = 1.5               # bonus points awarded

# ── Ultra-processed ingredient penalties ─────────────────────────────
# Lowercase keywords that indicate ultra-processing / artificial additives.
ULTRA_PROCESSED_KEYWORDS: list[str] = [
    # Artificial sweeteners
    "sucralose", "aspartame", "acesulfame", "acesulfame-k", "saccharin",
    "neotame", "advantame",
    # Artificial colors
    "red 40", "red no. 40", "yellow 5", "yellow 6", "blue 1", "blue 2",
    "fd&c", "tartrazine", "sunset yellow", "allura red", "brilliant blue",
    "artificial color", "artificial colour",
    # Preservatives
    "sodium benzoate", "potassium sorbate", "sodium nitrite", "sodium nitrate",
    "bha", "bht", "tbhq", "sodium metabisulfite", "calcium propionate",
    # Emulsifiers / thickeners of concern
    "polysorbate", "carrageenan",
    # Flavor enhancers
    "monosodium glutamate", "msg", "disodium inosinate", "disodium guanylate",
    "artificial flavor", "artificial flavour",
    # Hydrogenated oils
    "hydrogenated", "partially hydrogenated",
]

# Penalty per ultra-processed indicator found
ULTRA_PROCESSED_PER_ITEM_PENALTY: float = 0.25

# Maximum total penalty from ultra-processed indicators (cap)
ULTRA_PROCESSED_MAX_PENALTY: float = 2.0

# ── Score bounds ─────────────────────────────────────────────────────
SCORE_MIN: float = 1.0
SCORE_MAX: float = 10.0


# ═══════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════

def _extract_numeric(value_str: str) -> Optional[float]:
    """Pull the first number from a string like '24 g'."""
    match = re.search(r"[\d]+\.?[\d]*", str(value_str))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def _compute_percent_dv(nutrient_name: str, value_str: str) -> Optional[float]:
    """Compute %DV for a nutrient given its value string."""
    dv_entry = DAILY_VALUES.get(nutrient_name)
    if dv_entry is None:
        return None
    daily_value = dv_entry["value"]
    if not daily_value or daily_value <= 0:
        return None
    extracted = _extract_numeric(value_str)
    if extracted is None:
        return None
    return round((extracted / daily_value) * 100, 1)


def _apply_tiers(
    percent_dv: float,
    tiers: list[tuple[float, float]],
) -> float:
    """Sum up points from all tiers whose threshold is met."""
    total = 0.0
    for threshold, points in tiers:
        if percent_dv >= threshold:
            total += points
    return total


def _find_percent_dv(
    synonyms: list[str],
    nutrients: dict[str, str],
) -> Optional[float]:
    """Find the %DV for the first matching synonym in the nutrients dict."""
    for name in synonyms:
        if name in nutrients:
            pct = _compute_percent_dv(name, nutrients[name])
            if pct is not None:
                return pct
    return None


def _count_ultra_processed(ingredient_names: list[str]) -> tuple[int, list[str]]:
    """Count ultra-processed indicators in the ingredient list.

    Returns (count, list_of_matched_keywords).
    """
    if not ingredient_names:
        return 0, []

    # Build a single lowercase string of all ingredient names
    combined = " ".join(name.lower() for name in ingredient_names)
    matched: list[str] = []

    for keyword in ULTRA_PROCESSED_KEYWORDS:
        if keyword in combined:
            matched.append(keyword)

    return len(matched), matched


# ═══════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════

def calculate_health_score(
    nutrients: dict[str, str],
    ingredient_names: list[str] | None = None,
) -> tuple[float, str]:
    """Calculate a deterministic health score from nutrients and ingredients.

    Parameters
    ----------
    nutrients:
        ``{name: "value unit"}`` dict, e.g. ``{"Sodium": "200 mg"}``.
    ingredient_names:
        List of ingredient name strings from the label.

    Returns
    -------
    tuple[float, str]
        ``(score, reasoning)`` where score is clamped to [1, 10] with
        1 decimal place, and reasoning is a human-readable explanation.
    """
    ingredient_names = ingredient_names or []
    score = BASELINE_SCORE
    reasoning_parts: list[str] = []

    # ── 1. Negative nutrient penalties ──
    negative_total = 0.0
    already_scored_sugar = False

    for synonyms, tiers in NEGATIVE_NUTRIENT_PENALTIES:
        # Skip Total Sugars if Added Sugars was already scored
        if synonyms[0] in ("Total Sugars", "Sugar", "Sugars") and already_scored_sugar:
            continue

        pct_dv = _find_percent_dv(synonyms, nutrients)
        if pct_dv is not None and pct_dv > 0:
            penalty = _apply_tiers(pct_dv, tiers)
            if penalty > 0:
                negative_total += penalty
                reasoning_parts.append(
                    f"{synonyms[0]} at {pct_dv:.0f}% DV (\u2212{penalty:.1f})"
                )
                if synonyms[0] in ("Added Sugars", "Added Sugar"):
                    already_scored_sugar = True

    score -= negative_total

    # ── 2. Positive nutrient bonuses ──
    positive_total = 0.0
    for synonyms, tiers in POSITIVE_NUTRIENT_BONUSES:
        pct_dv = _find_percent_dv(synonyms, nutrients)
        if pct_dv is not None and pct_dv > 0:
            bonus = _apply_tiers(pct_dv, tiers)
            if bonus > 0:
                positive_total += bonus
                reasoning_parts.append(
                    f"{synonyms[0]} at {pct_dv:.0f}% DV (+{bonus:.1f})"
                )

    score += positive_total

    # ── 2b. Clean label bonus ──
    # Reward products that have very low negative nutrient penalties
    if negative_total <= CLEAN_LABEL_PENALTY_THRESHOLD:
        score += CLEAN_LABEL_BONUS
        reasoning_parts.append(
            f"Clean nutrient profile bonus (+{CLEAN_LABEL_BONUS:.1f})"
        )

    # ── 3. Ultra-processed ingredient penalties ──
    up_count, up_matches = _count_ultra_processed(ingredient_names)
    if up_count > 0:
        up_penalty = min(
            up_count * ULTRA_PROCESSED_PER_ITEM_PENALTY,
            ULTRA_PROCESSED_MAX_PENALTY,
        )
        score -= up_penalty
        reasoning_parts.append(
            f"{up_count} ultra-processed indicator(s) found (\u2212{up_penalty:.1f}): "
            f"{', '.join(up_matches[:5])}"
        )

    # ── 4. Clamp and round ──
    score = round(max(SCORE_MIN, min(SCORE_MAX, score)), 1)

    # ── 5. Build reasoning string ──
    if not reasoning_parts:
        reasoning = (
            f"Baseline score of {BASELINE_SCORE:.0f}. "
            "Insufficient nutrient data to adjust further."
        )
    else:
        reasoning = (
            f"Starting from baseline {BASELINE_SCORE:.0f}/10. "
            + "; ".join(reasoning_parts)
            + f". Final score: {score}/10."
        )

    logger.info("Health score calculated: %.1f \u2014 %s", score, reasoning)
    return score, reasoning
