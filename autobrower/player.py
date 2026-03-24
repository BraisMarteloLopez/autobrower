import json
import platform
import subprocess
import time

import pyautogui

from autobrower.config import SCAN_TARGETS as DEFAULT_NO_CITAS_PHRASES
from autobrower.config import get_profile_path

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"


def _xdotool(*args: str) -> bool:
    """Run an xdotool command. Returns True on success, False if unavailable."""
    try:
        subprocess.run(
            ["xdotool", *args],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        return False


def _move_to(x: int, y: int) -> None:
    """Move cursor to absolute coordinates, supporting multi-monitor setups.

    pyautogui.moveTo() clamps coordinates to the primary monitor bounds,
    so negative x/y values (monitors to the left/above) are silently lost.
    On Windows we call SetCursorPos directly; on Linux we use xdotool
    which correctly handles the full virtual screen coordinate space.
    """
    if IS_WINDOWS:
        import ctypes
        ctypes.windll.user32.SetCursorPos(x, y)
    elif IS_LINUX and _xdotool("mousemove", "--", str(x), str(y)):
        pass  # xdotool handled it
    else:
        pyautogui.moveTo(x, y, _pause=False)


def _send_wheel(clicks: int, horizontal: bool = False) -> None:
    """Send a mouse wheel event via SendInput on Windows.

    Uses WHEEL_DELTA=120 per click to match the Windows wheel protocol.
    """
    import ctypes
    import ctypes.wintypes
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_HWHEEL = 0x01000
    # WHEEL_DELTA is a C preprocessor #define in WinUser.h, not an exported
    # symbol — it cannot be read at runtime.  The value has been 120 since
    # Windows NT 4.0 and is guaranteed by the Windows API contract.
    WHEEL_DELTA = 120

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.wintypes.DWORD),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("time", ctypes.wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.wintypes.DWORD),
            ("mi", MOUSEINPUT),
        ]

    inp = INPUT()
    inp.type = 0  # INPUT_MOUSE
    inp.mi.dx = 0
    inp.mi.dy = 0
    inp.mi.mouseData = ctypes.wintypes.DWORD(int(clicks * WHEEL_DELTA))
    inp.mi.dwFlags = MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL
    inp.mi.time = 0
    inp.mi.dwExtraInfo = None
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def _vscroll(clicks: int) -> None:
    """Vertical scroll that works reliably on all platforms including multi-monitor."""
    if clicks == 0:
        return
    if IS_WINDOWS:
        _send_wheel(clicks, horizontal=False)
    elif IS_LINUX:
        button = "5" if clicks < 0 else "4"
        if _xdotool("click", "--repeat", str(abs(clicks)), button):
            return
        pyautogui.scroll(clicks, _pause=False)
    else:
        pyautogui.scroll(clicks, _pause=False)


def _click(x: int, y: int, button: str, pressed: bool) -> None:
    """Click at absolute coordinates, supporting multi-monitor setups."""
    _move_to(x, y)
    if pressed:
        pyautogui.mouseDown(button=button, _pause=False)
    else:
        pyautogui.mouseUp(button=button, _pause=False)


def _hscroll(clicks: int) -> None:
    """Horizontal scroll that works on all platforms including Windows."""
    if IS_WINDOWS:
        _send_wheel(clicks, horizontal=True)
    else:
        pyautogui.hscroll(clicks, _pause=False)


def load_profile(name: str) -> dict:
    """Load a profile JSON file by name."""
    path = get_profile_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    with open(path) as f:
        return json.load(f)


def _play_alert() -> None:
    """Emit an audible alert using the system bell or paplay."""
    system = platform.system()
    try:
        if system == "Linux":
            # Try paplay first (PulseAudio), fall back to beep
            try:
                subprocess.Popen(
                    ["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                print("\a")  # terminal bell
        elif system == "Darwin":
            subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("\a")
    except Exception:
        print("\a")


class Player:
    """Replays recorded mouse events at OS level using pyautogui."""

    def __init__(self, profile: dict, speed: float = 1.0, loop: bool = True,
                 loop_delay: float = 0.5,
                 scan_targets: list[str] | None = None):
        if speed <= 0:
            raise ValueError(f"speed must be positive, got {speed}")
        self.events = profile["events"]
        self.speed = speed
        self.loop = loop
        self.loop_delay = loop_delay
        self.running = False
        self._scan_targets = scan_targets

    def _run_scan_at(self, x: int, y: int) -> bool:
        """Run OCR scan at the given position (from a recorded scan event).

        Returns True if the loop should CONTINUE (target text found → no
        appointments), False if the loop should STOP (text gone → maybe
        appointments available).
        """
        if not self._scan_targets:
            return True  # no scan configured, always continue

        from autobrower.scanner import scan_for_text

        try:
            for target in self._scan_targets:
                found, ocr_text = scan_for_text(target, pos=(x, y))
                if found:
                    print(f"\n[SCAN] \"{target}\" detected at ({x},{y}) — no appointments, continuing loop...")
                    return True
        except Exception as exc:
            print(f"\n[SCAN] Error during scan: {exc}")
            return True  # on error, keep looping rather than false-alerting

        # None of the target phrases found → appointments might be available!
        print(f"\n[SCAN] Target text NOT found at ({x},{y}) — appointments may be available!")
        return False

    def _dispatch(self, event: dict) -> bool:
        """Execute a single event. Returns False if playback should stop (scan miss)."""
        x, y = event["x"], event["y"]
        etype = event["type"]

        if etype == "move":
            _move_to(x, y)

        elif etype == "click":
            button = event.get("button", "left")
            _click(x, y, button, event.get("pressed", True))

        elif etype == "scroll":
            dy = event.get("dy", 0)
            dx = event.get("dx", 0)
            _move_to(x, y)
            if dy:
                _vscroll(dy)
            if dx:
                _hscroll(dx)

        elif etype == "scan":
            # Synchronous: wait for OCR result before continuing
            should_continue = self._run_scan_at(x, y)
            if not should_continue:
                return False

        return True

    def _on_key_press(self, key) -> None:
        try:
            char = key.char
        except AttributeError:
            return
        if char == "j":
            print("\n[STOP] 'j' pressed — stopping playback...")
            self.running = False

    def play(self) -> None:
        """Start playback. Loops until Ctrl+C, 'j' key, failsafe, or scan detects availability."""
        if not self.events:
            return

        self.running = True
        original_pause = pyautogui.PAUSE
        pyautogui.PAUSE = 0
        cycle = 0
        from pynput import keyboard
        kb_listener = keyboard.Listener(on_press=self._on_key_press)
        kb_listener.start()
        try:
            while self.running:
                cycle += 1
                scan_failed = False
                for i, event in enumerate(self.events):
                    if not self.running:
                        break

                    if not self._dispatch(event):
                        # Scan event didn't find target text → stop
                        _play_alert()
                        print(f"[ALERT] Stopped after {cycle} cycles — check for available appointments!")
                        scan_failed = True
                        self.running = False
                        break

                    # Sleep for the delta until the next event
                    if i < len(self.events) - 1:
                        delta = (self.events[i + 1]["t"] - event["t"]) / self.speed
                        if delta > 0:
                            time.sleep(delta)

                if scan_failed or not self.loop:
                    break

                if self.running and self.loop_delay > 0:
                    time.sleep(self.loop_delay)
        except (KeyboardInterrupt, pyautogui.FailSafeException):
            pass
        finally:
            kb_listener.stop()
            pyautogui.PAUSE = original_pause
            self.running = False

    def stop(self) -> None:
        self.running = False
