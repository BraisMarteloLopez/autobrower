"""Screen capture and OCR scanning around the mouse cursor."""

import re
import unicodedata

import numpy as np
import pyautogui

from autobrower.config import CAPTURE_HEIGHT, CAPTURE_WIDTH

# Lazy-initialised OCR engine
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def capture_around_cursor(width: int = CAPTURE_WIDTH, height: int = CAPTURE_HEIGHT, pos: tuple[int, int] | None = None) -> "Image":
    """Take a screenshot of a rectangle centred on the current mouse position."""
    mx, my = pos if pos is not None else pyautogui.position()
    screen_w, screen_h = pyautogui.size()

    # Clamp capture size to screen dimensions
    width = min(width, screen_w)
    height = min(height, screen_h)

    left = max(0, min(mx - width // 2, screen_w - width))
    top = max(0, min(my - height // 2, screen_h - height))

    print(f"[DEBUG] mouse=({mx},{my}) screen=({screen_w}x{screen_h}) capture=({left},{top},{width},{height})")
    img = pyautogui.screenshot(region=(left, top, width, height))
    from pathlib import Path
    debug_dir = Path("debug_captures")
    debug_dir.mkdir(exist_ok=True)
    import time
    path = debug_dir / f"capture_{int(time.time())}.png"
    img.save(str(path))
    print(f"[DEBUG] Screenshot saved to {path}")
    return img


def _normalize(text: str) -> str:
    """Collapse whitespace, strip accents, and lowercase for fuzzy matching."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def scan_for_text(target: str, width: int = CAPTURE_WIDTH, height: int = CAPTURE_HEIGHT, pos: tuple[int, int] | None = None) -> tuple[bool, str]:
    """Capture screen around cursor and check if *target* appears in the OCR text.

    Uses normalized comparison (no accents, collapsed whitespace) so minor
    OCR misreads of whitespace or diacritics don't cause false negatives.

    Returns (found, full_ocr_text).
    """
    img = capture_around_cursor(width, height, pos=pos)
    result, _ = _get_engine()(np.array(img))
    texts = [line[1] for line in result] if result else []
    ocr_text = " ".join(texts)
    found = _normalize(target) in _normalize(ocr_text)
    return found, ocr_text
