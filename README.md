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

Press `Ctrl+C` to stop recording.

#### OCR scan during recording

You can trigger an on-demand OCR scan while recording by pressing a hotkey. This captures a 1200x600 region around the cursor, runs Tesseract OCR (Spanish), and checks whether the target text is present on screen.

```bash
python -m autobrower record my-session --scan-key h --scan-target "no hay citas disponibles"
```

While recording, press `h` to scan. The result is printed to the terminal but does not affect the recording itself. Requires `tesseract` installed on the system.

### `play <profile>`

Replays a recorded profile. Loops by default.

```bash
python -m autobrower play my-session
python -m autobrower play my-session --speed 0.5         # half speed
python -m autobrower play my-session --no-loop            # play once
python -m autobrower play my-session --loop-delay 2.0     # 2s pause between cycles
```

Stop with `Ctrl+C` or move the mouse to the top-left corner of the screen (pyautogui failsafe).

#### OCR scan during playback

When looping, `--scan` enables an automatic OCR scan after each cycle. If the target text is found on screen, the loop continues. If it disappears (meaning appointments may be available), playback stops and an audible alert plays.

```bash
# Use default target phrases ("no hay citas disponibles" variants)
python -m autobrower play my-session --scan

# Use custom target phrases
python -m autobrower play my-session --scan --scan-target "sin disponibilidad" --scan-target "agotado"
```

Requires `tesseract` installed on the system (`apt install tesseract-ocr tesseract-ocr-spa` on Debian/Ubuntu).

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
SCAN_TARGETS=en este momento no hay citas disponibles,no hay citas disponibles  # Comma-separated phrases for OCR scan
```

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
  scanner.py    # Screen capture and OCR scanning (tesseract)
tests/
  test_config.py
  test_player.py
  test_recorder.py
```
