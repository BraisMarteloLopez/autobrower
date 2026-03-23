"""Screen capture and OCR scanning around the mouse cursor."""

import re
import unicodedata

import easyocr
import numpy as np
import pyautogui

# Lazy-initialised reader (first call downloads models ~100 MB)
_reader: easyocr.Reader | None = None


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["es", "en"], gpu=False)
    return _reader


def capture_around_cursor(width: int = 1200, height: int = 600) -> "Image":
    """Take a screenshot of a rectangle centred on the current mouse position."""
    mx, my = pyautogui.position()
    screen_w, screen_h = pyautogui.size()

    # Clamp capture size to screen dimensions
    width = min(width, screen_w)
    height = min(height, screen_h)

    left = max(0, min(mx - width // 2, screen_w - width))
    top = max(0, min(my - height // 2, screen_h - height))

    return pyautogui.screenshot(region=(left, top, width, height))


def _normalize(text: str) -> str:
    """Collapse whitespace, strip accents, and lowercase for fuzzy matching."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def scan_for_text(target: str, width: int = 1200, height: int = 600) -> tuple[bool, str]:
    """Capture screen around cursor and check if *target* appears in the OCR text.

    Uses normalized comparison (no accents, collapsed whitespace) so minor
    OCR misreads of whitespace or diacritics don't cause false negatives.

    Returns (found, full_ocr_text).
    """
    img = capture_around_cursor(width, height)
    results = _get_reader().readtext(np.array(img), detail=0)
    ocr_text = " ".join(results)
    found = _normalize(target) in _normalize(ocr_text)
    return found, ocr_text
