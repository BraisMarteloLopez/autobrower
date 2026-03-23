"""Screen capture and OCR scanning around the mouse cursor."""

import pyautogui
import pytesseract


def capture_around_cursor(width: int = 600, height: int = 300) -> "Image":
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


def scan_for_text(target: str, width: int = 600, height: int = 300) -> tuple[bool, str]:
    """Capture screen around cursor and check if *target* appears in the OCR text.

    Returns (found, full_ocr_text).
    """
    img = capture_around_cursor(width, height)
    ocr_text = pytesseract.image_to_string(img, lang="spa")
    found = target.lower() in ocr_text.lower()
    return found, ocr_text
