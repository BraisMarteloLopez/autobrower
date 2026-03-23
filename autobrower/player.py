import json
import platform
import subprocess
import time

import pyautogui

from autobrower.config import SCAN_TARGETS as DEFAULT_NO_CITAS_PHRASES
from autobrower.config import get_profile_path

_HAS_HSCROLL = platform.system() != "Windows"


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

    def _check_scan(self) -> bool:
        """Run OCR scan after a loop cycle.

        Returns True if the loop should CONTINUE (target text found → no
        appointments), False if the loop should STOP (text gone → maybe
        appointments available).
        """
        if not self._scan_targets:
            return True  # no scan configured, always continue

        from autobrower.scanner import scan_for_text

        for target in self._scan_targets:
            found, ocr_text = scan_for_text(target)
            if found:
                print(f"\n[SCAN] \"{target}\" detected — no appointments, continuing loop...")
                return True

        # None of the target phrases found → appointments might be available!
        print(f"\n[SCAN] Target text NOT found — appointments may be available!")
        return False

    def _dispatch(self, event: dict) -> None:
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
            if dy:
                pyautogui.scroll(dy, x=x, y=y, _pause=False)
            if dx and _HAS_HSCROLL:
                pyautogui.hscroll(dx, x=x, y=y, _pause=False)

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
                for i, event in enumerate(self.events):
                    if not self.running:
                        break
                    self._dispatch(event)

                    # Sleep for the delta until the next event
                    if i < len(self.events) - 1:
                        delta = (self.events[i + 1]["t"] - event["t"]) / self.speed
                        if delta > 0:
                            time.sleep(delta)

                if not self.loop:
                    break

                # After each loop cycle, run OCR scan
                if self.running and self._scan_targets:
                    should_continue = self._check_scan()
                    if not should_continue:
                        _play_alert()
                        print(f"[ALERT] Stopped after {cycle} cycles — check for available appointments!")
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
