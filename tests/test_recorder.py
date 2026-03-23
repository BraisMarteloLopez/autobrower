import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Mock pynput before importing recorder (no X server in CI)
sys.modules.setdefault("pynput", mock.MagicMock())
sys.modules.setdefault("pynput.mouse", mock.MagicMock())

from autobrower.recorder import Recorder


@pytest.fixture
def recorder():
    return Recorder(interval=0.16)


def test_move_throttle(recorder):
    """Move events within the interval are discarded."""
    recorder._start_time = 0.0
    recorder._last_move_time = -1.0  # allow first event through

    with mock.patch("time.monotonic", side_effect=[0.0, 0.05, 0.10, 0.20]):
        recorder._on_move(100, 200)  # t=0.0 → recorded (last_move=-1)
        recorder._on_move(110, 210)  # t=0.05 → throttled (0.05 < 0.16)
        recorder._on_move(120, 220)  # t=0.10 → throttled (0.10 < 0.16)
        recorder._on_move(130, 230)  # t=0.20 → recorded (0.20 >= 0.16)

    assert len(recorder.events) == 2
    assert recorder.events[0]["x"] == 100
    assert recorder.events[1]["x"] == 130


def test_click_no_throttle(recorder):
    """Click events are never throttled."""
    recorder._start_time = 0.0
    btn = mock.MagicMock()
    btn.name = "left"

    with mock.patch("time.monotonic", side_effect=[0.0, 0.01, 0.02]):
        recorder._on_click(100, 200, btn, True)
        recorder._on_click(100, 200, btn, False)
        recorder._on_click(150, 250, btn, True)

    assert len(recorder.events) == 3
    assert all(e["type"] == "click" for e in recorder.events)


def test_scroll_no_throttle(recorder):
    """Scroll events are never throttled."""
    recorder._start_time = 0.0

    with mock.patch("time.monotonic", side_effect=[0.0, 0.01]):
        recorder._on_scroll(100, 200, 0, -3)
        recorder._on_scroll(100, 200, 0, 3)

    assert len(recorder.events) == 2
    assert recorder.events[0]["dy"] == -3
    assert recorder.events[1]["dy"] == 3


def test_save_creates_valid_json(recorder):
    """save() writes a valid JSON file with metadata."""
    recorder._start_time = 0.0
    recorder.events = [
        {"t": 0.0, "type": "move", "x": 100, "y": 200},
        {"t": 0.5, "type": "click", "x": 100, "y": 200, "button": "left", "pressed": True},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch("autobrower.config.PROFILES_DIR", Path(tmpdir)):
            path = recorder.save("test_profile")

        with open(path) as f:
            data = json.load(f)

        assert data["name"] == "test_profile"
        assert data["event_count"] == 2
        assert data["duration"] == 0.5
        assert len(data["events"]) == 2


def test_event_format(recorder):
    """Events have the expected fields."""
    recorder._start_time = 0.0
    btn = mock.MagicMock()
    btn.name = "right"

    with mock.patch("time.monotonic", return_value=1.0):
        recorder._on_move(50, 60)

    with mock.patch("time.monotonic", return_value=1.1):
        recorder._on_click(50, 60, btn, True)

    with mock.patch("time.monotonic", return_value=1.2):
        recorder._on_scroll(50, 60, 1, -2)

    move = recorder.events[0]
    assert move["type"] == "move"
    assert "x" in move and "y" in move

    click = recorder.events[1]
    assert click["type"] == "click"
    assert click["button"] == "right"
    assert click["pressed"] is True

    scroll = recorder.events[2]
    assert scroll["type"] == "scroll"
    assert scroll["dx"] == 1
    assert scroll["dy"] == -2
