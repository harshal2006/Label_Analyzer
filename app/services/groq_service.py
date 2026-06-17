"""
Groq Nutrient Insights Service — batched source & usage lookup.

Sends a single batched request to the Groq LLM to get natural/dietary
source and functional usage information for each nutrient in a product.
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
    logger.warning("GROQ_API_KEY not set — nutrient insights will use fallback text.")
    _client = None
else:
    _client = Groq(api_key=_GROQ_API_KEY)
    logger.info("Groq client initialized for nutrient insights.")

# ---------------------------------------------------------------------------
# Fallback text when the API is unavailable or fails
# ---------------------------------------------------------------------------
_FALLBACK_SOURCE = "Commonly found in various foods and dietary sources."
_FALLBACK_USAGE = "Nutritional component typically found in packaged food products."


def _build_fallback(nutrients: dict) -> dict:
    """Return a dict with generic placeholder insights for every nutrient."""
    return {
        name: {"source": _FALLBACK_SOURCE, "usage": _FALLBACK_USAGE}
        for name in nutrients
    }


def get_nutrient_insights(nutrients: dict) -> dict:
    """Get source and usage information for each nutrient via Groq.

    Parameters
    ----------
    nutrients:
        A dict mapping nutrient names to their display values, e.g.
        ``{"Protein": "24 g", "Sodium": "200 mg"}``.

    Returns
    -------
    dict
        A dict with the same keys, each mapping to
        ``{"source": "...", "usage": "..."}``.
        On failure, returns generic placeholder text per nutrient.
    """
    if not nutrients:
        return {}

    if _client is None:
        logger.warning("Groq client unavailable — returning fallback insights.")
        return _build_fallback(nutrients)

    nutrient_list = ", ".join(f'"{k}" ({v})' for k, v in nutrients.items())

    system_prompt = (
        "You are a nutrition science assistant. "
        "Return ONLY valid JSON with no markdown fences, no preamble, no explanation. "
        "Do not wrap the output in ```json or ``` blocks."
    )

    user_prompt = (
        f"For each of the following nutrients, provide:\n"
        f'- "source": a brief description of natural/dietary sources of that nutrient\n'
        f'- "usage": its functional role or purpose in a packaged food product '
        f"(e.g. preservative, sweetener, texture agent, nutritional additive)\n\n"
        f"Nutrients: {nutrient_list}\n\n"
        f"Return a JSON object where each key is the nutrient name and the value is "
        f'{{"source": "...", "usage": "..."}}. '
        f"Return ONLY the JSON object, nothing else."
    )

    try:
        logger.info("Requesting nutrient insights from Groq (%d nutrients)…", len(nutrients))
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
        logger.info("Groq nutrient insights response received (%d chars).", len(raw_response))

        # Defensively strip markdown fences
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        insights = json.loads(cleaned)

        # Ensure every requested nutrient has an entry
        for name in nutrients:
            if name not in insights:
                insights[name] = {"source": _FALLBACK_SOURCE, "usage": _FALLBACK_USAGE}
            else:
                # Ensure both keys exist in each entry
                entry = insights[name]
                if "source" not in entry:
                    entry["source"] = _FALLBACK_SOURCE
                if "usage" not in entry:
                    entry["usage"] = _FALLBACK_USAGE

        logger.info("Nutrient insights parsed successfully for %d nutrients.", len(insights))
        return insights

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Groq nutrient insights as JSON: %s", exc)
        return _build_fallback(nutrients)
    except Exception as exc:
        logger.exception("Groq nutrient insights API call failed: %s", exc)
        return _build_fallback(nutrients)
