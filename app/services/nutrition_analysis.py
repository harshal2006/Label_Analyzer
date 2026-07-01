"""
Pure nutrition analysis functions — no external API calls.

Provides %DV flag calculation, allergen detection, and macronutrient
split computation.  All three functions are deterministic and side-effect
free, making them trivial to unit-test.
"""

from __future__ import annotations

import re
from typing import Optional

from app.utils.nutrition_reference import COMMON_ALLERGENS, DAILY_VALUES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_numeric(value_str: str) -> Optional[float]:
    """Pull the first number (int or float) from a string like '24 g'.

    Returns None if no number is found.
    """
    match = re.search(r"[\d]+\.?[\d]*", str(value_str))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# 1. %DV flags
# ---------------------------------------------------------------------------

def calculate_dv_flags(nutrients: dict[str, str]) -> dict[str, dict]:
    """Compute percent daily value and assign a flag for each nutrient.

    Parameters
    ----------
    nutrients:
        ``{name: "value unit"}`` dict, e.g. ``{"Sodium": "200 mg"}``.

    Returns
    -------
    dict
        ``{name: {"percent_dv": float, "flag": "High"|"Moderate"|"Low"}}``
        for every nutrient that has a reference daily value.
    """
    results: dict[str, dict] = {}

    for name, value_str in nutrients.items():
        dv_entry = DAILY_VALUES.get(name)
        if dv_entry is None:
            continue

        daily_value = dv_entry["value"]
        if not daily_value or daily_value <= 0:
            continue

        extracted = _extract_numeric(value_str)
        if extracted is None:
            continue

        percent_dv = round((extracted / daily_value) * 100, 1)

        if percent_dv >= 20:
            flag = "High"
        elif percent_dv <= 5:
            flag = "Low"
        else:
            flag = "Moderate"

        results[name] = {"percent_dv": percent_dv, "flag": flag}

    return results


# ---------------------------------------------------------------------------
# 2. Allergen detection
# ---------------------------------------------------------------------------

def detect_allergens(ingredient_text: str, ingredient_names: list[str] = None) -> list[dict]:
    """Detect major allergens in an ingredient / OCR text and assess prominence.

    Parameters
    ----------
    ingredient_text:
        Raw text (e.g. full OCR dump or ingredient list).
    ingredient_names:
        Optional ordered list of extracted ingredient names to determine prominence.

    Returns
    -------
    list[dict]
        A list of dictionaries, each containing:
        - "allergen": Display-friendly allergen name.
        - "matched_ingredients": List of specific synonyms/keywords found.
        - "prominence": "Major" or "Minor/Trace"
        Empty list if text is empty or no allergens found.
    """
    if not ingredient_text or not ingredient_text.strip():
        return []

    text_lower = ingredient_text.lower()
    detected: list[dict] = []
    
    # Heuristics for primary sources that should always be Major
    primary_source_keywords = ["whey", "milk", "egg", "peanut", "soybean", "wheat", "cashew", "almond"]

    for entry in COMMON_ALLERGENS:
        allergen_name = entry["name"]
        matched_synonyms = []
        is_major = False

        for keyword in entry["keywords"]:
            if keyword in text_lower:
                if keyword not in matched_synonyms:
                    matched_synonyms.append(keyword)
                
                # Check for absolute primary keywords
                if keyword in primary_source_keywords:
                    is_major = True
                
                # Check position if ingredient_names is provided
                if not is_major and ingredient_names:
                    # Look in the top 3 ingredients
                    top_n = ingredient_names[:3]
                    for top_ing in top_n:
                        if keyword in top_ing.lower():
                            is_major = True
                            break
        
        if matched_synonyms:
            detected.append({
                "allergen": allergen_name,
                "matched_ingredients": matched_synonyms,
                "prominence": "Major" if is_major else "Minor / Trace",
            })

    return detected


# ---------------------------------------------------------------------------
# 3. Macronutrient calorie split
# ---------------------------------------------------------------------------

# Mapping from nutrient display names to calorie multiplier (kcal per gram).
# We check multiple synonym keys to handle whatever the parser produced.
_MACRO_MAP: list[tuple[str, list[str], float]] = [
    ("protein_pct",  ["Protein"],                                          4.0),
    ("carbs_pct",    ["Total Carbohydrate", "Total Carbohydrates",
                      "Carbohydrate", "Carbohydrates"],                    4.0),
    ("fat_pct",      ["Total Fat", "Fat"],                                 9.0),
]


def calculate_macro_split(nutrients: dict[str, str]) -> dict[str, float]:
    """Calculate macronutrient calorie percentages.

    Parameters
    ----------
    nutrients:
        ``{name: "value unit"}`` dict.

    Returns
    -------
    dict
        ``{"protein_pct": float, "carbs_pct": float, "fat_pct": float}``
        Each value is a percentage of total macro-derived calories (0–100).
        If total is zero (all macros missing), returns all zeros.
    """
    calories: dict[str, float] = {}

    for key, synonyms, multiplier in _MACRO_MAP:
        grams = 0.0
        for syn in synonyms:
            if syn in nutrients:
                val = _extract_numeric(nutrients[syn])
                if val is not None and val > 0:
                    grams = val
                    break
        calories[key] = grams * multiplier

    total = sum(calories.values())

    if total <= 0:
        return {"protein_pct": 0.0, "carbs_pct": 0.0, "fat_pct": 0.0}

    return {
        key: round((cal / total) * 100, 1)
        for key, cal in calories.items()
    }
