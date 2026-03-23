import ctypes
import platform

# Enable DPI awareness BEFORE any other imports so that pyautogui/pynput
# see real pixel coordinates instead of scaled ones.
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
