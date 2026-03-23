import ctypes
import platform

# Enable DPI awareness BEFORE any other imports so that all Windows APIs
# (GetCursorPos, GetSystemMetrics, PIL ImageGrab) use physical pixel
# coordinates consistently. Without this, cursor position is in logical
# (scaled) coords but screenshots use physical pixels, causing an offset
# that grows with distance from (0,0).
if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from autobrower.cli import main

main()
