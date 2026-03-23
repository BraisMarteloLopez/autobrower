import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SAMPLE_INTERVAL: float = float(os.getenv("SAMPLE_INTERVAL", "0.16"))
PROFILES_DIR: Path = Path(os.getenv("PROFILES_DIR", "./profiles"))
PLAYBACK_SPEED: float = float(os.getenv("PLAYBACK_SPEED", "1.0"))
if PLAYBACK_SPEED <= 0:
    raise ValueError(f"PLAYBACK_SPEED must be positive, got {PLAYBACK_SPEED}")

# Default phrases that indicate "no appointments available".
# Comma-separated in .env; OCR scan looks for these on screen.
_DEFAULT_SCAN_TARGETS = "en este momento no hay citas disponibles,no hay citas disponibles"
SCAN_TARGETS: list[str] = [
    s.strip() for s in os.getenv("SCAN_TARGETS", _DEFAULT_SCAN_TARGETS).split(",") if s.strip()
]

CAPTURE_WIDTH: int = int(os.getenv("CAPTURE_WIDTH", "1200"))
CAPTURE_HEIGHT: int = int(os.getenv("CAPTURE_HEIGHT", "600"))


_VALID_PROFILE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def validate_profile_name(name: str) -> None:
    """Raise ValueError if the profile name contains unsafe characters."""
    if not _VALID_PROFILE_NAME.match(name):
        raise ValueError(
            f"Invalid profile name '{name}'. "
            "Use only letters, digits, hyphens, and underscores."
        )


def get_profile_path(name: str) -> Path:
    """Return the full path for a profile, creating the directory if needed."""
    validate_profile_name(name)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR / f"{name}.json"


def _read_profile_metadata(path: Path) -> dict | None:
    """Read metadata fields from a profile, excluding the events array."""
    try:
        with open(path) as fh:
            data = json.load(fh)
        data.pop("events", None)
        return data
    except (json.JSONDecodeError, OSError):
        return None


def list_profiles() -> list[dict]:
    """Scan PROFILES_DIR and return metadata for each profile."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles = []
    for f in sorted(PROFILES_DIR.glob("*.json")):
        data = _read_profile_metadata(f)
        if data is None:
            continue
        profiles.append({
            "name": data.get("name", f.stem),
            "created": data.get("created", "unknown"),
            "duration": data.get("duration", 0),
            "event_count": data.get("event_count", 0),
        })
    return profiles
