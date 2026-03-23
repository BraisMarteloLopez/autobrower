"""Screen capture and OCR scanning around the mouse cursor."""

import ctypes
import ctypes.wintypes
import platform
import re
import unicodedata

import numpy as np
from PIL import ImageGrab

from autobrower.config import CAPTURE_HEIGHT, CAPTURE_WIDTH

# Lazy-initialised OCR engine
_engine = None

IS_WINDOWS = platform.system() == "Windows"


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def _get_cursor_pos() -> tuple[int, int]:
    """Get cursor position using the Windows API directly (same coord space as screenshots)."""
    if IS_WINDOWS:
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
    import pyautogui
    return pyautogui.position()


def _get_virtual_screen() -> tuple[int, int, int, int]:
    """Return (left, top, width, height) of the virtual screen (all monitors)."""
    if IS_WINDOWS:
        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79
        vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        vw = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        vh = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        return vx, vy, vw, vh
    import pyautogui
    sw, sh = pyautogui.size()
    return 0, 0, sw, sh


def capture_around_cursor(width: int = CAPTURE_WIDTH, height: int = CAPTURE_HEIGHT, pos: tuple[int, int] | None = None) -> "Image":
    """Take a screenshot of a rectangle centred on the current mouse position."""
    mx, my = pos if pos is not None else _get_cursor_pos()
    vx, vy, vw, vh = _get_virtual_screen()

    # Clamp capture size to virtual screen
    width = min(width, vw)
    height = min(height, vh)

    # Calculate crop region in virtual screen coordinates
    left = max(vx, min(mx - width // 2, vx + vw - width))
    top = max(vy, min(my - height // 2, vy + vh - height))

    # Grab exactly the region we need (bbox uses virtual screen coords on Windows)
    img = ImageGrab.grab(bbox=(left, top, left + width, top + height), all_screens=True)

    # Debug: save capture for verification (remove once confirmed working)
    from pathlib import Path
    import time
    debug_dir = Path("debug_captures")
    debug_dir.mkdir(exist_ok=True)
    path = debug_dir / f"capture_{int(time.time())}.png"
    img.save(str(path))
    actual_w, actual_h = img.size
    print(f"[DEBUG] mouse=({mx},{my}) vscreen=({vx},{vy},{vw},{vh}) bbox=({left},{top},{left+width},{top+height}) img=({actual_w}x{actual_h}) → {path}")

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
