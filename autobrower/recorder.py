import json
import time
from datetime import datetime, timezone

from pynput import keyboard, mouse

from autobrower.config import SAMPLE_INTERVAL, get_profile_path


class Recorder:
    """Records mouse events at OS level using pynput."""

    def __init__(self, interval: float = SAMPLE_INTERVAL,
                 scan_key: str | None = None,
                 scan_target: str | None = None,
                 scan_callback=None):
        self.interval = interval
        self.events: list[dict] = []
        self._start_time: float = 0.0
        self._last_move_time: float = -interval
        self._mouse_listener: mouse.Listener | None = None
        self._kb_listener: keyboard.Listener | None = None

        # OCR scan settings
        self._scan_key = scan_key  # e.g. "h"
        self._scan_target = scan_target
        self._scan_callback = scan_callback  # fn(found, ocr_text)

    def _elapsed(self) -> float:
        return time.monotonic() - self._start_time

    def _on_move(self, x: int, y: int) -> None:
        t = self._elapsed()
        if t - self._last_move_time < self.interval:
            return
        self._last_move_time = t
        self.events.append({"t": round(t, 4), "type": "move", "x": x, "y": y})

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        t = self._elapsed()
        self.events.append({
            "t": round(t, 4),
            "type": "click",
            "x": x,
            "y": y,
            "button": button.name,
            "pressed": pressed,
        })

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        t = self._elapsed()
        self.events.append({
            "t": round(t, 4),
            "type": "scroll",
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy,
        })

    def _on_key_press(self, key) -> None:
        if self._scan_key is None or self._scan_target is None:
            return
        try:
            char = key.char
        except AttributeError:
            return
        if char != self._scan_key:
            return

        from autobrower.scanner import scan_for_text

        found, ocr_text = scan_for_text(self._scan_target)
        if self._scan_callback:
            self._scan_callback(found, ocr_text)

    def start(self) -> None:
        """Start recording. Blocks until stop() is called or KeyboardInterrupt."""
        self.events.clear()
        self._start_time = time.monotonic()
        self._last_move_time = -self.interval
        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._mouse_listener.start()

        # Start keyboard listener for scan hotkey
        if self._scan_key:
            self._kb_listener = keyboard.Listener(on_press=self._on_key_press)
            self._kb_listener.start()

        try:
            self._mouse_listener.join()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the listeners."""
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
        if self._kb_listener is not None:
            self._kb_listener.stop()

    def save(self, profile_name: str) -> str:
        """Save recorded events to a profile JSON file. Returns the file path."""
        duration = self.events[-1]["t"] if self.events else 0.0
        document = {
            "name": profile_name,
            "created": datetime.now(timezone.utc).isoformat(),
            "duration": round(duration, 2),
            "event_count": len(self.events),
            "events": self.events,
        }
        path = get_profile_path(profile_name)
        with open(path, "w") as f:
            json.dump(document, f, indent=2)
        return str(path)
