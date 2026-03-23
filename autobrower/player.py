import json
import platform
import subprocess
import time

import pyautogui

from autobrower.config import SCAN_TARGETS as DEFAULT_NO_CITAS_PHRASES
from autobrower.config import get_profile_path

IS_WINDOWS = platform.system() == "Windows"


def _hscroll(clicks: int) -> None:
    """Horizontal scroll that works on all platforms including Windows."""
    if IS_WINDOWS:
        import ctypes
        import ctypes.wintypes
        MOUSEEVENTF_HWHEEL = 0x01000
        WHEEL_DELTA = 120
        # Build a MOUSEINPUT struct via SendInput
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
        inp.mi.dwFlags = MOUSEEVENTF_HWHEEL
        inp.mi.time = 0
        inp.mi.dwExtraInfo = None
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
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
            pyautogui.moveTo(x, y, _pause=False)

        elif etype == "click":
            button = event.get("button", "left")
            if event.get("pressed", True):
                pyautogui.mouseDown(x=x, y=y, button=button, _pause=False)
            else:
                pyautogui.mouseUp(x=x, y=y, button=button, _pause=False)

        elif etype == "scroll":
            dy = event.get("dy", 0)
            dx = event.get("dx", 0)
            # Move cursor first, then scroll at current position.
            # Passing x,y directly to pyautogui.scroll() can misfire on
            # Windows because the internal moveTo + wheel happen too fast
            # for the target window to register the hover.
            pyautogui.moveTo(x, y, _pause=False)
            if dy:
                pyautogui.scroll(dy, _pause=False)
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
