import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest


def test_default_values():
    """Config loads sensible defaults without .env."""
    # Re-import with clean env to test defaults
    with mock.patch.dict(os.environ, {}, clear=True):
        import importlib
        import autobrower.config as cfg
        importlib.reload(cfg)

        assert cfg.SAMPLE_INTERVAL == 0.16
        assert cfg.PROFILES_DIR == Path("./profiles")


def test_env_override():
    """Config respects environment variable overrides."""
    with mock.patch.dict(os.environ, {
        "SAMPLE_INTERVAL": "0.5",
        "PROFILES_DIR": "/tmp/my_profiles",
    }):
        import importlib
        import autobrower.config as cfg
        importlib.reload(cfg)

        assert cfg.SAMPLE_INTERVAL == 0.5
        assert cfg.PROFILES_DIR == Path("/tmp/my_profiles")


def test_get_profile_path_creates_dir():
    """get_profile_path creates the profiles directory if missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        profiles_dir = Path(tmpdir) / "sub" / "profiles"
        with mock.patch.dict(os.environ, {"PROFILES_DIR": str(profiles_dir)}):
            import importlib
            import autobrower.config as cfg
            importlib.reload(cfg)

            path = cfg.get_profile_path("test")
            assert path == profiles_dir / "test.json"
            assert profiles_dir.is_dir()


def test_list_profiles_empty():
    """list_profiles returns empty list when no profiles exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with mock.patch.dict(os.environ, {"PROFILES_DIR": tmpdir}):
            import importlib
            import autobrower.config as cfg
            importlib.reload(cfg)

            assert cfg.list_profiles() == []


def test_list_profiles_with_data():
    """list_profiles reads metadata from profile JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        profile = {
            "name": "demo",
            "created": "2026-01-01T00:00:00",
            "duration": 10.5,
            "event_count": 42,
            "events": [],
        }
        with open(Path(tmpdir) / "demo.json", "w") as f:
            json.dump(profile, f)

        with mock.patch.dict(os.environ, {"PROFILES_DIR": tmpdir}):
            import importlib
            import autobrower.config as cfg
            importlib.reload(cfg)

            result = cfg.list_profiles()
            assert len(result) == 1
            assert result[0]["name"] == "demo"
            assert result[0]["duration"] == 10.5
            assert result[0]["event_count"] == 42
