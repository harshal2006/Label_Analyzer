"""
Groq Report Insights Service — batched ingredient & usage lookup.

Sends a single batched request to the Groq LLM to get:
  - primary_goal: overall product purpose summary
  - ingredient_details: source/origin and functional role for each ingredient
  - how_to_use: inferred product type, usage instructions, and cautions

Falls back to generic placeholders if the API call fails.
"""

import json
import logging
import os

from groq import Groq

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq client (reuses the same GROQ_API_KEY from .env as analysis_service)
# ---------------------------------------------------------------------------
_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not _GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not set — report insights will use fallback text.")
    _client = None
else:
    _client = Groq(api_key=_GROQ_API_KEY)
    logger.info("Groq client initialized for report insights.")

# ---------------------------------------------------------------------------
# Fallback text when the API is unavailable or fails
# ---------------------------------------------------------------------------
_FALLBACK_PRIMARY_GOAL = (
    "This product provides a mix of nutritional components suitable for general consumption."
)
_FALLBACK_HOW_TO_USE: dict = {
    "product_type": "Nutritional Supplement",
    "usage_instructions": "Follow the dosage instructions on the product label.",
    "cautions": "Consult a healthcare professional before use if you have any medical conditions.",
}


def _build_fallback(
    ingredient_names: list[str],
) -> tuple[str, list[dict], dict]:
    """Return generic placeholder goal, ingredient details, and how_to_use."""
    ingredient_details = [
        {
            "name": name,
            "source": "Commonly found in various foods and dietary sources.",
            "role": "Nutritional component typically found in packaged food products.",
        }
        for name in ingredient_names
    ]
    return _FALLBACK_PRIMARY_GOAL, ingredient_details, dict(_FALLBACK_HOW_TO_USE)


def get_report_insights(
    nutrients: dict,
    ingredient_names: list[str],
) -> tuple[str, list[dict], dict]:
    """Get overall product goal, ingredient details, and usage info via Groq.

    Parameters
    ----------
    nutrients:
        A dict mapping nutrient names to their display values, e.g.
        ``{"Protein": "24 g", "Sodium": "200 mg"}``.
    ingredient_names:
        A list of ingredient name strings extracted from the label, e.g.
        ``["Whey Protein Concentrate", "Cocoa Powder", "Sucralose"]``.

    Returns
    -------
    tuple[str, list[dict], dict]
        A tuple containing:
        - primary_goal (str): A 2-3 sentence summary of the product's overall intent.
        - ingredient_details (list[dict]): A list of
          ``{"name": "...", "source": "...", "role": "..."}`` for each ingredient.
        - how_to_use (dict): ``{"product_type": "...",
          "usage_instructions": "...", "cautions": "..."}``.
        On failure, returns generic placeholder text for all three.
    """
    if not nutrients and not ingredient_names:
        return "", [], {}

    if _client is None:
        logger.warning("Groq client unavailable — returning fallback insights.")
        return _build_fallback(ingredient_names)

    nutrient_list = ", ".join(f'"{k}" ({v})' for k, v in nutrients.items())
    ingredient_list = ", ".join(f'"{name}"' for name in ingredient_names) if ingredient_names else "None detected"

    system_prompt = (
        "You are a nutrition science assistant. "
        "Return ONLY valid JSON with no markdown fences, no preamble, no explanation. "
        "Do not wrap the output in ```json or ``` blocks."
    )

    user_prompt = (
        f"A product label has the following nutrient profile and ingredients.\n\n"
        f"Nutrients: {nutrient_list}\n"
        f"Ingredients: {ingredient_list}\n\n"
        f"Based on this data, provide three things:\n\n"
        f'1. "primary_goal": A 2-3 sentence plain-English statement summarizing the overall '
        f'purpose/intent of this product (e.g., "This product is designed primarily as a '
        f'high-protein recovery supplement, with moderate carbohydrates and a notably low '
        f'sugar content suited for post-workout nutrition.").\n\n'
        f'2. "ingredient_details": For each ingredient listed above, provide:\n'
        f'   - "name": the ingredient name exactly as given\n'
        f'   - "source": a brief description of what it is and where it comes from '
        f'(natural/dietary origin, how it is produced)\n'
        f'   - "role": its specific functional role in THIS product '
        f'(e.g., primary protein source, sweetener, texture agent, preservative, flavoring)\n\n'
        f'3. "how_to_use": Based ONLY on the nutrient profile and ingredients, infer:\n'
        f'   - "product_type": what this product likely is (e.g., "Whey Protein Powder", '
        f'"Multivitamin Tablet", "Energy Drink", "Mass Gainer")\n'
        f'   - "usage_instructions": recommended usage (timing, dosage, who it is for). '
        f'Be practical and specific.\n'
        f'   - "cautions": any usage cautions or tips based on the ingredients/nutrients. '
        f'Do NOT make medical claims. Stick to factual, label-based observations.\n\n'
        f'Return a JSON object with this exact shape:\n'
        f'{{"primary_goal": "...", '
        f'"ingredient_details": [{{"name": "...", "source": "...", "role": "..."}}], '
        f'"how_to_use": {{"product_type": "...", "usage_instructions": "...", "cautions": "..."}}}}\n\n'
        f"Return ONLY the JSON object, nothing else."
    )

    try:
        logger.info(
            "Requesting report insights from Groq (%d nutrients, %d ingredients)…",
            len(nutrients),
            len(ingredient_names),
        )
        chat_completion = _client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=4096,
        )

        raw_response = chat_completion.choices[0].message.content
        logger.info("Groq report insights response received (%d chars).", len(raw_response))

        # Defensively strip markdown fences
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        parsed_json = json.loads(cleaned)

        # --- Extract primary_goal ---
        primary_goal = parsed_json.get("primary_goal", _FALLBACK_PRIMARY_GOAL)

        # --- Extract ingredient_details ---
        raw_details = parsed_json.get("ingredient_details", [])
        ingredient_details: list[dict] = []
        returned_names = set()

        for item in raw_details:
            name = item.get("name", "Unknown")
            returned_names.add(name)
            ingredient_details.append({
                "name": name,
                "source": item.get("source", "Information not available."),
                "role": item.get("role", "Information not available."),
            })

        # Ensure every requested ingredient has an entry
        for name in ingredient_names:
            if name not in returned_names:
                ingredient_details.append({
                    "name": name,
                    "source": "Information not available.",
                    "role": "Information not available.",
                })

        # --- Extract how_to_use ---
        how_to_use = parsed_json.get("how_to_use", dict(_FALLBACK_HOW_TO_USE))
        # Ensure required keys exist
        how_to_use.setdefault("product_type", "Nutritional Supplement")
        how_to_use.setdefault(
            "usage_instructions",
            "Follow the dosage instructions on the product label.",
        )
        how_to_use.setdefault(
            "cautions",
            "Consult a healthcare professional before use if you have any medical conditions.",
        )

        logger.info(
            "Report insights parsed: %d ingredient details, product_type=%s.",
            len(ingredient_details),
            how_to_use.get("product_type", "?"),
        )
        return primary_goal, ingredient_details, how_to_use

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Groq report insights as JSON: %s", exc)
        return _build_fallback(ingredient_names)
    except Exception as exc:
        logger.exception("Groq report insights API call failed: %s", exc)
        return _build_fallback(ingredient_names)
