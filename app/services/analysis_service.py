"""
Analysis Service — Groq-powered ingredient analysis.

Sends OCR-extracted text to a Groq LLM for ingredient-level health analysis,
allergen detection, and overall health scoring.
"""

import json
import logging
import os

from groq import Groq

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq client (initialized once)
# ---------------------------------------------------------------------------
_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not _GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not set — ingredient analysis will be unavailable.")
    _client = None
else:
    _client = Groq(api_key=_GROQ_API_KEY)
    logger.info("Groq client initialized.")

# ---------------------------------------------------------------------------
# Analysis prompt
# ---------------------------------------------------------------------------
ANALYSIS_PROMPT = """You are a food and cosmetic ingredient analysis assistant. Analyze the following OCR-extracted text from a product label to find and evaluate its ingredients.

The OCR text usually contains a mix of a nutrition facts table, usage instructions, warnings, and an ingredients list. 
CRITICAL RULES FOR READING THE TEXT:
1. Multi-column interleaved text: Because OCR reads line-by-line across the whole image, lines from different columns are often interleaved. For example, a line of the ingredients list might be immediately followed by a random warning from an adjacent column, and then the ingredients list continues on the next line. You must piece together the "INGREDIENTS:" section by intelligently ignoring the interleaved noise lines.
2. Search aggressively: You MUST carefully search the entire text for the word "INGREDIENTS:" or similar markers. Do NOT assume the ingredient list is missing just because the text looks messy or you see a large nutrition table first. 

The OCR text may contain Hindi/English mixed content, OCR errors, or unclear segments. Do your best to interpret it. If the text is in Hindi or Devanagari script, transliterate ingredient names to English before analysis.

OCR TEXT:
{ocr_text}

Respond ONLY with valid JSON in the exact structure below. Do not include any text, explanation, or markdown formatting outside the JSON.

{{
  "ingredients": [
    {{
      "name": "string - ingredient name (in English)",
      "purpose": "string - what this ingredient does (e.g., preservative, sweetener, emulsifier, protein source)",
      "harmful_flags": {{
        "diabetes": "boolean - true if harmful or risky for diabetics",
        "kidney": "boolean - true if harmful or risky for kidney patients",
        "pregnancy": "boolean - true if harmful or risky during pregnancy"
      }},
      "is_allergen": "boolean - true if this is a common allergen",
      "allergen_type": "string or null - e.g., 'nuts', 'dairy', 'soy', 'gluten', null if not an allergen"
    }}
  ],
  "overall_health_score": "integer 1-10, where 1 is very unhealthy and 10 is very healthy",
  "health_score_reasoning": "string - brief 1-2 sentence explanation of the score",
  "summary": "string - 2-3 sentence overall summary of the product based on its ingredients",
  "warnings": ["array of strings - any critical warnings, e.g., 'Contains artificial sweeteners'"],
  "ocr_quality_issue": "boolean - true ONLY if the OCR text is completely unreadable or missing the ingredients section entirely",
  "low_confidence_items": ["array of strings - ingredient names you're unsure about due to OCR/translation ambiguity"]
}}

If, after searching carefully, the text truly does not contain any ingredients, set "ocr_quality_issue" to true, return an empty "ingredients" array, set "overall_health_score" to 0, and explain that no ingredients were found in "summary".
"""


def analyze_ingredients(ocr_text: str) -> dict | None:
    """Send OCR text to Groq for ingredient analysis.

    Parameters
    ----------
    ocr_text:
        The raw OCR text extracted from a product label.

    Returns
    -------
    dict or None
        Parsed JSON analysis from the LLM, or None if the service
        is unavailable or an error occurs.
    """
    if _client is None:
        logger.warning("Groq client not initialized — skipping analysis.")
        return None

    if not ocr_text or len(ocr_text.strip()) < 10:
        logger.warning("OCR text too short for analysis (%d chars).", len(ocr_text))
        return {
            "ingredients": [],
            "overall_health_score": 0,
            "health_score_reasoning": "OCR text too short to analyze.",
            "summary": "Insufficient text extracted from the image for analysis.",
            "warnings": [],
            "ocr_quality_issue": True,
            "low_confidence_items": [],
        }

    prompt = ANALYSIS_PROMPT.format(ocr_text=ocr_text)

    try:
        logger.info("Sending OCR text to Groq for ingredient analysis…")
        chat_completion = _client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=4096,
        )

        raw_response = chat_completion.choices[0].message.content
        logger.info("Groq response received (%d chars).", len(raw_response))

        # Strip markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        analysis = json.loads(cleaned)
        logger.info(
            "Analysis complete: health_score=%s, %d ingredients parsed.",
            analysis.get("overall_health_score", "?"),
            len(analysis.get("ingredients", [])),
        )
        return analysis

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Groq response as JSON: %s", exc)
        logger.debug("Raw response: %s", raw_response)
        return None
    except Exception as exc:
        logger.exception("Groq API call failed: %s", exc)
        return None
