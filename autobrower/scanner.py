"""Screen capture and OCR scanning around the mouse cursor."""

import ctypes
import ctypes.wintypes
import os
import platform
import re
import time
import unicodedata
from pathlib import Path

import numpy as np
from PIL import ImageGrab

from autobrower.config import CAPTURE_HEIGHT, CAPTURE_WIDTH

# Lazy-initialised OCR engine
_engine = None

IS_WINDOWS = platform.system() == "Windows"
DEBUG_CAPTURES = os.environ.get("AUTOBROWER_DEBUG_CAPTURES", "1").lower() in ("1", "true", "yes")


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
    return _engine


def _get_cursor_pos() -> tuple[int, int]:
    """Get cursor position using the Windows API directly."""
    if IS_WINDOWS:
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
    import pyautogui
    return pyautogui.position()


def _get_virtual_screen() -> tuple[int, int, int, int]:
    """Return (left, top, width, height) of the virtual screen."""
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
    """Take a screenshot of a rectangle centred on the current mouse position.

    This implementation is DPI-robust: instead of trusting that all APIs use
    the same coordinate space, it takes a full screenshot, measures the actual
    scale factor between reported screen size and image pixels, and converts
    the cursor position accordingly.
    """
    mx, my = pos if pos is not None else _get_cursor_pos()
    vx, vy, vw, vh = _get_virtual_screen()

    # Take a full screenshot — the image size reveals the true physical resolution
    full = ImageGrab.grab(all_screens=True)
    fw, fh = full.size

    # Compute actual scale factor: image pixels vs reported screen size.
    # If DPI awareness is set correctly, scale ≈ 1.0.
    # If not (e.g. 150% scaling), scale ≈ 1.5.
    # This makes us robust regardless of DPI awareness state.
    scale_x = fw / vw if vw > 0 else 1.0
    scale_y = fh / vh if vh > 0 else 1.0

    # Convert cursor position from API coordinates to image pixel coordinates
    img_x = int((mx - vx) * scale_x)
    img_y = int((my - vy) * scale_y)

    # Scale capture region to image pixels
    crop_w = int(width * scale_x)
    crop_h = int(height * scale_y)

    # Clamp to image bounds
    crop_w = min(crop_w, fw)
    crop_h = min(crop_h, fh)

    # Centre the crop on the cursor, clamped to image edges
    left = max(0, min(img_x - crop_w // 2, fw - crop_w))
    top = max(0, min(img_y - crop_h // 2, fh - crop_h))

    img = full.crop((left, top, left + crop_w, top + crop_h))

    if DEBUG_CAPTURES:
        debug_dir = Path("debug_captures")
        debug_dir.mkdir(exist_ok=True)
        ts = f"{time.time():.3f}".replace(".", "_")
        path = debug_dir / f"capture_{ts}.png"
        img.save(str(path))
        print(
            f"[DEBUG] mouse=({mx},{my}) vscreen=({vx},{vy},{vw},{vh}) "
            f"full=({fw}x{fh}) scale=({scale_x:.3f},{scale_y:.3f}) "
            f"img_pos=({img_x},{img_y}) crop=({left},{top},{crop_w},{crop_h}) → {path}"
        )

    return img


def _normalize(text: str) -> str:
    """Strip accents and lowercase for fuzzy matching."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def _spaceless(text: str) -> str:
    """Normalize then remove ALL whitespace — handles OCR joining words."""
    return re.sub(r"\s+", "", _normalize(text))


def scan_for_text(target: str, width: int = CAPTURE_WIDTH, height: int = CAPTURE_HEIGHT, pos: tuple[int, int] | None = None) -> tuple[bool, str]:
    """Capture screen around cursor and check if *target* appears in the OCR text.

    Comparison ignores spaces entirely because OCR often joins or splits words
    (e.g. "estemomentonohay" instead of "en este momento no hay").

    Returns (found, full_ocr_text).
    """
    img = capture_around_cursor(width, height, pos=pos)
    result, _ = _get_engine()(np.array(img))
    texts = [line[1] for line in result] if result else []
    ocr_text = " ".join(texts)
    found = _spaceless(target) in _spaceless(ocr_text)
    return found, ocr_text
