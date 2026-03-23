import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SAMPLE_INTERVAL: float = float(os.getenv("SAMPLE_INTERVAL", "0.16"))
PROFILES_DIR: Path = Path(os.getenv("PROFILES_DIR", "./profiles"))


def get_profile_path(name: str) -> Path:
    """Return the full path for a profile, creating the directory if needed."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR / f"{name}.json"


def list_profiles() -> list[dict]:
    """Scan PROFILES_DIR and return metadata for each profile."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles = []
    for f in sorted(PROFILES_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
            profiles.append({
                "name": data.get("name", f.stem),
                "created": data.get("created", "unknown"),
                "duration": data.get("duration", 0),
                "event_count": data.get("event_count", 0),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return profiles
