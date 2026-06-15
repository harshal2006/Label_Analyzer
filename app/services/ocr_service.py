"""
OCR Service — PaddleOCR-based text extraction and nutrient parsing.

The PaddleOCR model is loaded once at module level (singleton) so startup
cost is paid only once, not on every request.
"""

import logging
import re
from pathlib import Path

import cv2
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton model – loaded once on first import
# ---------------------------------------------------------------------------
# Suppress noisy PaddleOCR / PaddlePaddle logs
logging.getLogger("ppocr").setLevel(logging.WARNING)

logger.info("Loading PaddleOCR model (this may take a moment on first run)…")
_ocr = PaddleOCR(use_textline_orientation=True, lang="en")
logger.info("PaddleOCR model loaded successfully.")

# ---------------------------------------------------------------------------
# Known nutrient names (matched case-insensitively)
# ---------------------------------------------------------------------------
KNOWN_NUTRIENTS: list[str] = [
    "Energy",
    "Protein",
    "Carbohydrate",
    "Carbohydrates",
    "Total Carbohydrate",
    "Total Carbohydrates",
    "Total Sugars",
    "Sugar",
    "Sugars",
    "Added Sugars",
    "Added Sugar",
    "Dietary Fiber",
    "Dietary Fibre",
    "Fiber",
    "Fibre",
    "Total Fat",
    "Fat",
    "Saturated Fat",
    "Trans Fat",
    "Monounsaturated Fat",
    "Polyunsaturated Fat",
    "Cholesterol",
    "Sodium",
    "Potassium",
    "Calcium",
    "Iron",
    "Vitamin A",
    "Vitamin B1",
    "Vitamin B2",
    "Vitamin B3",
    "Vitamin B5",
    "Vitamin B6",
    "Vitamin B12",
    "Vitamin C",
    "Vitamin D",
    "Vitamin E",
    "Vitamin K",
    "Thiamine",
    "Riboflavin",
    "Niacin",
    "Folate",
    "Folic Acid",
    "Biotin",
    "Pantothenic Acid",
    "Phosphorus",
    "Magnesium",
    "Zinc",
    "Selenium",
    "Copper",
    "Manganese",
    "Chromium",
    "Iodine",
    "Chloride",
    "Calories",
    "BCAA",
    "EAA",
    "Glutamic Acid",
    "Moisture",
    "Ash",
]

# Pre-compile a set of lowercase nutrient names for fast lookup
_NUTRIENT_NAMES_LOWER: set[str] = {n.lower() for n in KNOWN_NUTRIENTS}

# Regex to match a value line: number + optional unit (e.g. "24g", "116 kcal", "0.61 g", "50 mg")
_VALUE_PATTERN = re.compile(
    r"^[\s]*"
    r"(?P<value>\d+(?:[.,]\d+)?)"       # numeric value (int or decimal)
    r"\s*"
    r"(?P<unit>[a-zA-Zμµ%]+(?:/[a-zA-Z]+)?)?$"  # optional unit like g, mg, kcal, mcg, IU, %
)


def _clean_nutrient_name(raw: str) -> str | None:
    """Strip leading dashes/bullets, trailing annotation markers, and whitespace.
    Return the cleaned name if it matches a known nutrient, otherwise None."""
    cleaned = raw.strip().lstrip("-–—^•·").rstrip("^*†‡§~").strip()
    if cleaned.lower() in _NUTRIENT_NAMES_LOWER:
        return cleaned
    return None


def _parse_value_line(line: str) -> dict | None:
    """Try to parse a line as a numeric value with optional unit.
    Returns {"value": float, "unit": str} or None."""
    m = _VALUE_PATTERN.match(line.strip())
    if m:
        val_str = m.group("value").replace(",", ".")
        return {
            "value": float(val_str),
            "unit": m.group("unit") or "",
        }
    return None


def parse_nutrients(ocr_text: str) -> list[dict]:
    """Parse structured nutrient data from raw OCR text.

    Scans lines for known nutrient names; when found, looks ahead up to 5
    lines for the first value (per-serving), skipping noise lines.

    Parameters
    ----------
    ocr_text:
        The raw newline-separated OCR text.

    Returns
    -------
    list[dict]
        Each dict has keys: ``name`` (str), ``value`` (float), ``unit`` (str).
    """
    lines = ocr_text.split("\n")
    nutrients: list[dict] = []
    i = 0

    while i < len(lines):
        name = _clean_nutrient_name(lines[i])
        if name is not None:
            # Look ahead at the next few lines for the per-serving value,
            # skipping intervening noise lines (e.g. brand text, instructions)
            parsed = None
            for offset in range(1, 6):
                if i + offset < len(lines):
                    # Stop if we hit another nutrient name (don't steal its value)
                    if _clean_nutrient_name(lines[i + offset]) is not None:
                        break
                    parsed = _parse_value_line(lines[i + offset])
                    if parsed:
                        break
            if parsed:
                nutrients.append({
                    "name": name,
                    "value": parsed["value"],
                    "unit": parsed["unit"],
                })
                logger.debug("Parsed nutrient: %s = %s %s", name, parsed["value"], parsed["unit"])
        i += 1

    logger.info("Parsed %d nutrients from OCR text", len(nutrients))
    return nutrients


# ---------------------------------------------------------------------------
# Main OCR function
# ---------------------------------------------------------------------------

def extract_text(image_path: str) -> dict:
    """Run OCR on an image and return extracted text and parsed nutrients.

    Parameters
    ----------
    image_path:
        Path to the image file (absolute or relative to the project root).

    Returns
    -------
    dict
        Keys: ``ocr_text`` (str), ``nutrients`` (list[dict]).

    Raises
    ------
    FileNotFoundError
        If *image_path* does not point to an existing file.
    RuntimeError
        If PaddleOCR returns no results or encounters an error.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Read image using OpenCV
    img = cv2.imread(str(path))
    if img is None:
        raise RuntimeError(f"Could not load image: {image_path}")

    # Downscale image if it is too large to speed up CPU inference significantly
    h, w = img.shape[:2]
    max_side = 1500
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)
        img = cv2.resize(img, (new_w, new_h))
        logger.info(f"Resized image from {w}x{h} to {new_w}x{new_h} for faster OCR processing")

    result = _ocr.ocr(img)

    if not result or result[0] is None:
        raise RuntimeError("PaddleOCR returned no results for the image.")

    lines: list[str] = []
    for page in result:
        if page is None:
            continue
        # Check if the page is dict-like (PaddleOCR v3+ returns paddlex OCRResult)
        if isinstance(page, dict) or (hasattr(page, "get") and hasattr(page, "keys")):
            page_lines = page.get("rec_texts", [])
            for text in page_lines:
                if text:
                    lines.append(str(text))
        else:
            # Fallback for older PaddleOCR versions (list of [bbox, (text, confidence)] entries)
            try:
                for line in page:
                    if isinstance(line, (list, tuple)) and len(line) > 1:
                        text = line[1][0]
                        if text:
                            lines.append(str(text))
            except Exception as e:
                logger.error(f"Failed to parse line in legacy PaddleOCR format: {e}")

    if not lines:
        raise RuntimeError("No text detected in the image.")

    ocr_text = "\n".join(lines)
    logger.info("Extracted %d text regions from %s", len(lines), image_path)

    # Parse structured nutrients from the raw text
    nutrients = parse_nutrients(ocr_text)

    return {
        "ocr_text": ocr_text,
        "nutrients": nutrients,
    }
