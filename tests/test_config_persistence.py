"""
Tests for app/config.py's save/load round-trip and corrupted-file recovery.
Uses monkeypatch on app.config.ROOT_DIR to redirect all file I/O to a temp
directory — never touches the real config.json (which holds real API keys).
"""
import importlib
import json

import pytest


@pytest.fixture
def isolated_config(qapp, tmp_path, monkeypatch):
    """A fresh AppConfig instance whose load/save methods are redirected to
    tmp_path instead of the real project's config.json.

    NOTE: `import app.config as X` does NOT reliably give you the module
    here — app/__init__.py does `from app.config import config`, which
    rebinds the `config` attribute on the `app` PACKAGE object to the
    AppConfig INSTANCE, shadowing the submodule Python's import machinery
    would otherwise expose at that same attribute name. importlib.import_module
    goes through sys.modules directly and isn't affected by that.
    """
    config_module = importlib.import_module("app.config")

    monkeypatch.setattr(config_module, "ROOT_DIR", tmp_path)
    cfg = config_module.AppConfig()
    return cfg, tmp_path


def test_save_load_round_trip(isolated_config):
    cfg, tmp_path = isolated_config
    cfg.USER_NAME = "Test User"
    cfg.GROQ_API_KEY = "fake-key-123"
    cfg.ALWAYS_LISTEN = True
    cfg.SCREEN_ANALYSIS_CLOUD_CONSENT = True
    cfg.MIC_ENERGY_THRESHOLD = 123

    assert cfg.save_to_json() is True
    assert (tmp_path / "config.json").exists()

    reloaded = type(cfg)()
    reloaded.load_from_json()  # ROOT_DIR is patched at module level for the duration of this test

    assert reloaded.USER_NAME == "Test User"
    assert reloaded.GROQ_API_KEY == "fake-key-123"
    assert reloaded.ALWAYS_LISTEN is True
    assert reloaded.SCREEN_ANALYSIS_CLOUD_CONSENT is True
    assert reloaded.MIC_ENERGY_THRESHOLD == 123


def test_save_is_atomic_no_partial_file_on_success(isolated_config):
    cfg, tmp_path = isolated_config
    cfg.save_to_json()
    tmp_marker = tmp_path / "config.json.tmp"
    assert not tmp_marker.exists()  # temp file cleaned up (renamed away)
    assert (tmp_path / "config.json").exists()


def test_corrupted_config_recovery_does_not_crash(isolated_config):
    cfg, tmp_path = isolated_config
    (tmp_path / "config.json").write_text("{ this is not valid json !!!", encoding="utf-8")

    # Must not raise.
    cfg.load_from_json()
    assert cfg.last_persistence_error is not None
    assert "config.json" in cfg.last_persistence_error or "read" in cfg.last_persistence_error.lower()
    # Defaults preserved — not wiped out or half-mutated.
    assert cfg.USER_NAME  # still has SOME default value, not None/crashed


def test_save_failure_is_surfaced_not_silently_swallowed(isolated_config, monkeypatch):
    cfg, tmp_path = isolated_config

    def _boom(*a, **kw):
        raise OSError("disk full (simulated)")

    monkeypatch.setattr("builtins.open", _boom)
    result = cfg.save_to_json()
    assert result is False
    assert cfg.last_persistence_error is not None
    assert "disk full" in cfg.last_persistence_error


def test_unknown_fields_in_saved_json_are_ignored_not_fatal(isolated_config):
    cfg, tmp_path = isolated_config
    (tmp_path / "config.json").write_text(
        json.dumps({"USER_NAME": "Still Works", "SOME_FIELD_THAT_NO_LONGER_EXISTS": 42}),
        encoding="utf-8",
    )
    cfg.load_from_json()
    assert cfg.USER_NAME == "Still Works"


def test_falsy_but_meaningful_values_still_load(isolated_config):
    """A saved empty string / zero / False must still apply — only
    genuinely absent (None) fields should be skipped."""
    cfg, tmp_path = isolated_config
    (tmp_path / "config.json").write_text(
        json.dumps({"GROQ_API_KEY": "", "MIC_DEVICE_INDEX": 0, "ALWAYS_LISTEN": False}),
        encoding="utf-8",
    )
    cfg.GROQ_API_KEY = "should be overwritten with empty string"
    cfg.load_from_json()
    assert cfg.GROQ_API_KEY == ""
    assert cfg.MIC_DEVICE_INDEX == 0
    assert cfg.ALWAYS_LISTEN is False
