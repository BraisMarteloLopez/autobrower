import sys
from unittest import mock

import pytest

# Mock pyautogui before importing player (no X server in CI)
mock_pyautogui = mock.MagicMock()
sys.modules.setdefault("pyautogui", mock_pyautogui)

from autobrower.player import Player


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset pyautogui mocks before each test."""
    mock_pyautogui.reset_mock()
    yield


@pytest.fixture
def sample_profile():
    return {
        "name": "test",
        "created": "2026-01-01T00:00:00",
        "duration": 1.0,
        "event_count": 4,
        "events": [
            {"t": 0.0, "type": "move", "x": 100, "y": 200},
            {"t": 0.2, "type": "click", "x": 100, "y": 200, "button": "left", "pressed": True},
            {"t": 0.3, "type": "click", "x": 100, "y": 200, "button": "left", "pressed": False},
            {"t": 1.0, "type": "scroll", "x": 100, "y": 200, "dx": 0, "dy": -3},
        ],
    }


def test_dispatch_move(sample_profile):
    """Move events call moveTo."""
    player = Player(sample_profile, loop=False)
    player._dispatch(sample_profile["events"][0])
    mock_pyautogui.moveTo.assert_called_once_with(100, 200, _pause=False)


def test_dispatch_click_pressed(sample_profile):
    """Click with pressed=True moves to position then calls mouseDown."""
    player = Player(sample_profile, loop=False)
    player._dispatch(sample_profile["events"][1])
    mock_pyautogui.moveTo.assert_called_once_with(100, 200, _pause=False)
    mock_pyautogui.mouseDown.assert_called_once_with(button="left", _pause=False)


def test_dispatch_click_released(sample_profile):
    """Click with pressed=False moves to position then calls mouseUp."""
    player = Player(sample_profile, loop=False)
    player._dispatch(sample_profile["events"][2])
    mock_pyautogui.moveTo.assert_called_once_with(100, 200, _pause=False)
    mock_pyautogui.mouseUp.assert_called_once_with(button="left", _pause=False)


def test_dispatch_scroll(sample_profile):
    """Scroll events move to position then scroll."""
    player = Player(sample_profile, loop=False)
    player._dispatch(sample_profile["events"][3])
    mock_pyautogui.moveTo.assert_called_once_with(100, 200, _pause=False)
    mock_pyautogui.scroll.assert_called_once_with(-3, _pause=False)


@mock.patch("autobrower.player._hscroll")
def test_dispatch_scroll_horizontal(mock_hs):
    """Scroll events with dx call _hscroll."""
    event = {"t": 0.0, "type": "scroll", "x": 100, "y": 200, "dx": 5, "dy": 0}
    profile = {"name": "test", "events": [event]}
    player = Player(profile, loop=False)
    player._dispatch(event)
    mock_hs.assert_called_once_with(5)
    mock_pyautogui.scroll.assert_not_called()


@mock.patch("time.sleep")
def test_play_no_loop(mock_sleep, sample_profile):
    """play() with no-loop runs events once and stops."""
    player = Player(sample_profile, loop=False)
    player.play()

    assert mock_pyautogui.moveTo.call_count == 4  # move + 2 clicks + scroll
    assert mock_pyautogui.mouseDown.call_count == 1
    assert mock_pyautogui.mouseUp.call_count == 1
    assert mock_pyautogui.scroll.call_count == 1
    assert mock_sleep.call_count == 3  # 3 deltas between 4 events


@mock.patch("time.sleep")
def test_speed_multiplier(mock_sleep, sample_profile):
    """Speed multiplier divides sleep deltas."""
    player = Player(sample_profile, speed=2.0, loop=False)
    player.play()

    # First delta: (0.2 - 0.0) / 2.0 = 0.1
    mock_sleep.assert_any_call(pytest.approx(0.1, abs=0.01))


@mock.patch("time.sleep")
def test_pause_restored_after_play(mock_sleep, sample_profile):
    """pyautogui.PAUSE is restored to its original value after playback."""
    mock_pyautogui.PAUSE = 0.1
    player = Player(sample_profile, loop=False)
    player.play()
    assert mock_pyautogui.PAUSE == 0.1


def test_invalid_speed():
    """Player rejects zero or negative speed."""
    profile = {"name": "test", "events": []}
    with pytest.raises(ValueError):
        Player(profile, speed=0)
    with pytest.raises(ValueError):
        Player(profile, speed=-1.5)


@mock.patch("time.sleep")
def test_loop_delay(mock_sleep):
    """Loop delay adds a pause between cycles."""
    events = [
        {"t": 0.0, "type": "move", "x": 10, "y": 20},
        {"t": 0.1, "type": "move", "x": 30, "y": 40},
    ]
    profile = {"name": "test", "events": events}
    player = Player(profile, loop=True, loop_delay=1.0)

    # Stop after first cycle completes
    call_count = [0]
    original_dispatch = player._dispatch

    def counting_dispatch(event):
        result = original_dispatch(event)
        call_count[0] += 1
        if call_count[0] >= 4:  # 2 events x 2 cycles
            player.stop()
        return result

    player._dispatch = counting_dispatch
    player.play()

    # Should have inter-event sleep (0.1s) + loop_delay (1.0s) calls
    sleep_args = [c[0][0] for c in mock_sleep.call_args_list]
    assert any(pytest.approx(1.0, abs=0.01) == s for s in sleep_args), \
        f"Expected loop_delay of 1.0s in sleep calls: {sleep_args}"


@mock.patch("time.sleep")
def test_empty_profile(mock_sleep):
    """play() with empty events returns immediately."""
    profile = {"name": "empty", "events": []}
    player = Player(profile, loop=False)
    player.play()

    mock_pyautogui.moveTo.assert_not_called()
    mock_sleep.assert_not_called()
