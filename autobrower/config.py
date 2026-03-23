import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SAMPLE_INTERVAL: float = float(os.getenv("SAMPLE_INTERVAL", "0.16"))
PROFILES_DIR: Path = Path(os.getenv("PROFILES_DIR", "./profiles"))


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
    """Read only the metadata fields from a profile without loading all events."""
    try:
        with open(path) as fh:
            # Metadata is in the first 6 lines of the indented JSON.
            # Read until we hit "events" key, then close with "}"
            header_lines = []
            for line in fh:
                if '"events"' in line:
                    break
                header_lines.append(line)
            # Close the JSON object so we can parse the header
            header = "".join(header_lines).rstrip().rstrip(",") + "\n}"
            return json.loads(header)
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
