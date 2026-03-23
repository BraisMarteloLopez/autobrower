"""Screen capture and OCR scanning around the mouse cursor."""

import re
import unicodedata

import pyautogui
import pytesseract


def capture_around_cursor(width: int = 1200, height: int = 600) -> "Image":
    """Take a screenshot of a rectangle centred on the current mouse position."""
    mx, my = pyautogui.position()
    screen_w, screen_h = pyautogui.size()

    left = max(0, mx - width // 2)
    top = max(0, my - height // 2)
    # clamp to screen edges
    if left + width > screen_w:
        left = screen_w - width
    if top + height > screen_h:
        top = screen_h - height
    left = max(0, left)
    top = max(0, top)

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
    ocr_text = pytesseract.image_to_string(img, lang="spa")
    found = _normalize(target) in _normalize(ocr_text)
    return found, ocr_text
