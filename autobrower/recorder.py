import json
import time
from datetime import datetime, timezone

from pynput import mouse

from autobrower.config import SAMPLE_INTERVAL, get_profile_path


class Recorder:
    """Records mouse events at OS level using pynput."""

    def __init__(self, interval: float = SAMPLE_INTERVAL):
        self.interval = interval
        self.events: list[dict] = []
        self._start_time: float = 0.0
        self._last_move_time: float = 0.0
        self._listener: mouse.Listener | None = None

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

    def start(self) -> None:
        """Start recording. Blocks until stop() is called or KeyboardInterrupt."""
        self.events.clear()
        self._start_time = time.monotonic()
        self._last_move_time = 0.0
        self._listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._listener.start()
        try:
            self._listener.join()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the listener."""
        if self._listener is not None:
            self._listener.stop()

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
