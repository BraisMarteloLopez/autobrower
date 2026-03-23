# autobrower

Record and replay mouse actions at OS level. Captures moves, clicks, and scroll events with precise timing and replays them using system-level input simulation.

## Requirements

- Python 3.11+
- Linux or macOS (horizontal scroll not supported on Windows)

## Installation

```bash
pip install -r requirements.txt
```

## Quick start

```bash
# Record a mouse session
python -m autobrower record my-session

# Replay it
python -m autobrower play my-session

# Replay at double speed, no loop
python -m autobrower play my-session --speed 2.0 --no-loop
```

## Commands

### `record <profile>`

Records mouse events (moves, clicks, scroll) and saves them as a JSON profile.

```bash
python -m autobrower record my-session
python -m autobrower record my-session -i 0.08      # faster sampling (default: 0.16s)
python -m autobrower record my-session --force       # overwrite without asking
```

- Press `h` to trigger an OCR scan at any time. Captures a region around the cursor and checks whether any of the `SCAN_TARGETS` phrases are on screen. The result is printed to the terminal but does not affect the recording.
- Press `Ctrl+C` to stop recording.

### `play <profile>`

Replays a recorded profile. Loops by default.

```bash
python -m autobrower play my-session
python -m autobrower play my-session --speed 0.5         # half speed
python -m autobrower play my-session --no-loop            # play once
python -m autobrower play my-session --loop-delay 2.0     # 2s pause between cycles
```

Stop with `j`, `Ctrl+C`, or move the mouse to the top-left corner of the screen (pyautogui failsafe).

#### Automatic OCR scan during playback

When looping, `--scan` enables an automatic OCR scan after each cycle. The scan checks for the `SCAN_TARGETS` phrases on screen:

- **Any phrase found** → "no hay citas", the loop continues.
- **No phrase found** → appointments may be available, playback stops and an audible alert plays.

```bash
# Use SCAN_TARGETS from .env
python -m autobrower play my-session --scan

# Override with custom phrases
python -m autobrower play my-session --scan --scan-target "sin disponibilidad" --scan-target "agotado"
```

### `scan`

OCR debug mode. Does not record anything — just listens for `h` to capture the screen around the cursor and print the full OCR text. Useful for testing what the OCR engine reads and verifying your `SCAN_TARGETS`.

```bash
python -m autobrower scan

# With custom targets
python -m autobrower scan --scan-target "texto a buscar"
```

Press `Ctrl+C` to exit.

### `list`

Lists all saved profiles with metadata.

```bash
python -m autobrower list
```

### `delete <profile>`

Deletes a profile (asks for confirmation).

```bash
python -m autobrower delete my-session
```

## Configuration

Copy `.env.example` to `.env` and adjust values:

```env
SAMPLE_INTERVAL=0.16    # Seconds between move samples during recording
PROFILES_DIR=./profiles # Directory to store profile JSON files
PLAYBACK_SPEED=1.0      # Default playback speed multiplier (overridable via --speed)
SCAN_TARGETS=en este momento no hay citas disponibles,no hay citas disponibles
CAPTURE_WIDTH=1200      # Width in pixels of the OCR capture region
CAPTURE_HEIGHT=600      # Height in pixels of the OCR capture region
```

`SCAN_TARGETS` is a comma-separated list of phrases used by the OCR scanner, both during recording (manual scan with `h`) and during playback (`--scan`). If any of these phrases appear on screen, it means there are no appointments available.

`CAPTURE_WIDTH` / `CAPTURE_HEIGHT` control the size of the screenshot taken around the cursor for OCR. Increase them to capture more of the screen, or decrease for faster scans.

All variables are optional and have sensible defaults.

## Profile format

Profiles are JSON files stored in `PROFILES_DIR`:

```json
{
  "name": "my-session",
  "created": "2026-03-23T12:00:00+00:00",
  "duration": 15.3,
  "event_count": 245,
  "events": [
    {"t": 0.0, "type": "move", "x": 500, "y": 300},
    {"t": 0.16, "type": "click", "x": 500, "y": 300, "button": "left", "pressed": true},
    {"t": 0.32, "type": "scroll", "x": 500, "y": 300, "dx": 0, "dy": -3}
  ]
}
```

Each event has a `t` field (seconds since recording start) that preserves the original timing during playback.

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Project structure

```
autobrower/
  __main__.py   # Entry point
  cli.py        # Argument parsing and commands
  config.py     # Environment-based configuration
  recorder.py   # Mouse event capture (pynput)
  player.py     # Mouse event replay (pyautogui)
  scanner.py    # Screen capture and OCR scanning (easyocr)
tests/
  test_config.py
  test_player.py
  test_recorder.py
```
