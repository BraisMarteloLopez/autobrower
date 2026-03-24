import json
import threading
import time
from datetime import datetime, timezone

from pynput import keyboard, mouse

from autobrower.config import SAMPLE_INTERVAL, SCAN_TARGETS, get_profile_path
from autobrower.scanner import _get_cursor_pos


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
        x, y = _get_cursor_pos()
        self._append({"t": round(t, 4), "type": "move", "x": x, "y": y})

    def _on_click(self, _x: int, _y: int, button: mouse.Button, pressed: bool) -> None:
        t = self._elapsed()
        x, y = _get_cursor_pos()
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
        x, y = _get_cursor_pos()
        self._append({
            "t": round(t, 4),
            "type": "scroll",
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy,
        })

    def _run_scan_preview(self, pos) -> None:
        """Live preview scan during recording (just for user feedback)."""
        from autobrower.scanner import scan_for_text

        try:
            for target in SCAN_TARGETS:
                found, ocr_text = scan_for_text(target, pos=pos)
                if found:
                    print(f"\n[SCAN PREVIEW] FOUND: \"{target}\"")
                    print(f"  OCR: {ocr_text[:120]}")
                    return

            print(f"\n[SCAN PREVIEW] Target text NOT found in OCR output.")
            print(f"  (This scan point has been saved to the profile)")
        except Exception as exc:
            print(f"\n[SCAN PREVIEW] Error: {exc}")
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

        t = self._elapsed()
        x, y = _get_cursor_pos()

        # Save the scan point as an event in the profile
        self._append({"t": round(t, 4), "type": "scan", "x": x, "y": y})
        print(f"\n[REC] Scan point recorded at ({x}, {y}) t={t:.1f}s")

        # Run a live preview so the user can verify OCR works at this spot
        threading.Thread(target=self._run_scan_preview, args=((x, y),), daemon=True).start()

    def start(self) -> None:
        """Start recording. Blocks until stop() is called or KeyboardInterrupt."""
        from autobrower.scanner import _get_virtual_screen
        vx, vy, vw, vh = _get_virtual_screen()
        print(f"Screen size detected: {vw}x{vh} (virtual screen at {vx},{vy})")
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
