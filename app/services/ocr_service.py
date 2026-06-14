"""
OCR Service — PaddleOCR-based text extraction.

The PaddleOCR model is loaded once at module level (singleton) so startup
cost is paid only once, not on every request.
"""

import logging
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


def extract_text(image_path: str) -> str:
    """Run OCR on an image and return the concatenated text.

    Parameters
    ----------
    image_path:
        Path to the image file (absolute or relative to the project root).

    Returns
    -------
    str
        All detected text regions concatenated with newlines.

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

    extracted = "\n".join(lines)
    logger.info("Extracted %d text regions from %s", len(lines), image_path)
    return extracted
