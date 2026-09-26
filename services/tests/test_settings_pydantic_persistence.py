from __future__ import annotations

import json
from pathlib import Path

import pytest

import services.settings_service as settings_module
from services.accessibility_preferences import AccessibilityPreferences
from services.settings_service import SettingsService


def test_settings_reject_invalid_payload_before_touching_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"sentinel": "keep"}\n', encoding="utf-8")
    before = path.read_bytes()
    service = SettingsService(path)

    with pytest.raises(ValueError):
        service.save({"ObsWebSocketPort": 70000})

    assert path.read_bytes() == before


def test_settings_atomic_round_trip_with_keyring_fallback(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    service = SettingsService(path)
    monkeypatch.setattr(service, "_save_secret", lambda value: False)
    monkeypatch.setattr(service, "_save_finch_api_key", lambda value: False)

    service.save({
        "EsoLogsClientId": "client",
        "EsoLogsClientSecret": "secret",
        "FinchApiKey": "finch",
        "ObsWebSocketPort": 4455,
    })

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["EsoLogsClientSecret"] == "secret"
    assert raw["FinchApiKey"] == "finch"
    assert raw["ObsWebSocketPort"] == 4455


def test_accessibility_malformed_existing_file_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "accessibility.json"
    path.write_text("{not-json", encoding="utf-8")
    before = path.read_bytes()
    preferences = AccessibilityPreferences(path)

    with pytest.raises(RuntimeError):
        preferences.set_visual_theme("anything")

    assert path.read_bytes() == before


def test_accessibility_atomic_write_preserves_additive_fields(tmp_path: Path) -> None:
    path = tmp_path / "accessibility.json"
    path.write_text(json.dumps({"FuturePreference": "keep"}), encoding="utf-8")
    preferences = AccessibilityPreferences(path)

    preferences.set_visual_theme("anything")

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["FuturePreference"] == "keep"
    assert raw["ColorVisionMode"] == "colorblind_friendly"
    assert raw["VisualTheme"] == "rylo_city_night"
