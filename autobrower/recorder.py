import json
import threading
import time
from datetime import datetime, timezone

import pyautogui
from pynput import keyboard, mouse

from autobrower.config import SAMPLE_INTERVAL, SCAN_TARGETS, get_profile_path


def _abs_pos() -> tuple[int, int]:
    """Return absolute cursor position via pyautogui (reliable on multi-monitor)."""
    return pyautogui.position()


class Recorder:
    """Records mouse events at OS level using pynput."""

    def __init__(self, interval: float = SAMPLE_INTERVAL):
        self.interval = interval
        self.events: list[dict] = []
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._last_move_time: float = -interval
        self._mouse_listener: mouse.Listener | None = None
        self._kb_listener: keyboard.Listener | None = None
        self._scanning = False

    def _elapsed(self) -> float:
        return time.monotonic() - self._start_time

    def _append(self, event: dict) -> None:
        with self._lock:
            self.events.append(event)

    def _on_move(self, _x: int, _y: int) -> None:
        t = self._elapsed()
        if t - self._last_move_time < self.interval:
            return
        self._last_move_time = t
        x, y = _abs_pos()
        self._append({"t": round(t, 4), "type": "move", "x": x, "y": y})

    def _on_click(self, _x: int, _y: int, button: mouse.Button, pressed: bool) -> None:
        t = self._elapsed()
        x, y = _abs_pos()
        self._append({
            "t": round(t, 4),
            "type": "click",
            "x": x,
            "y": y,
            "button": button.name,
            "pressed": pressed,
        })

    def _on_scroll(self, _x: int, _y: int, dx: int, dy: int) -> None:
        t = self._elapsed()
        x, y = _abs_pos()
        self._append({
            "t": round(t, 4),
            "type": "scroll",
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy,
        })

    def _run_scan(self) -> None:
        from autobrower.scanner import scan_for_text

        try:
            for target in SCAN_TARGETS:
                found, ocr_text = scan_for_text(target)
                if found:
                    print(f"\n[SCAN] FOUND: \"{target}\"")
                    return

            print(f"\n[SCAN] Target text NOT found — appointments may be available!")
        except Exception as exc:
            print(f"\n[SCAN] Error: {exc}")
        finally:
            self._scanning = False

    def _on_key_press(self, key) -> None:
        try:
            char = key.char
        except AttributeError:
            return
        if char != "h":
            return
        if self._scanning:
            return
        self._scanning = True
        threading.Thread(target=self._run_scan, daemon=True).start()

    def start(self) -> None:
        """Start recording. Blocks until stop() is called or KeyboardInterrupt."""
        import pyautogui
        screen_w, screen_h = pyautogui.size()
        print(f"Screen size detected: {screen_w}x{screen_h} (absolute coordinates)")
        self.events.clear()
        self._start_time = time.monotonic()
        self._last_move_time = -self.interval
        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._mouse_listener.start()

        self._kb_listener = keyboard.Listener(on_press=self._on_key_press)
        self._kb_listener.start()

        try:
            while self._mouse_listener.is_alive():
                self._mouse_listener.join(timeout=0.5)
        except KeyboardInterrupt:
            pass
        finally:
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
