import json
import platform
import time

import pyautogui

from autobrower.config import get_profile_path

_HAS_HSCROLL = platform.system() != "Windows"


def load_profile(name: str) -> dict:
    """Load a profile JSON file by name."""
    path = get_profile_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    with open(path) as f:
        return json.load(f)


class Player:
    """Replays recorded mouse events at OS level using pyautogui."""

    def __init__(self, profile: dict, speed: float = 1.0, loop: bool = True,
                 loop_delay: float = 0.5):
        self.events = profile["events"]
        self.speed = speed
        self.loop = loop
        self.loop_delay = loop_delay
        self.running = False

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

    def play(self) -> None:
        """Start playback. Loops until Ctrl+C or failsafe triggers."""
        if not self.events:
            return

        self.running = True
        pyautogui.PAUSE = 0
        try:
            while self.running:
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
                if self.running and self.loop_delay > 0:
                    time.sleep(self.loop_delay)
        except (KeyboardInterrupt, pyautogui.FailSafeException):
            pass
        finally:
            self.running = False

    def stop(self) -> None:
        self.running = False
