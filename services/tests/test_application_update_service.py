from __future__ import annotations

import json
from pathlib import Path

from services import application_update_service as updater


class _Response:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_private_gateway_config_overrides_public_github(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / updater.UPDATE_ACCESS_FILE).write_text(
        json.dumps(
            {
                "base_url": "https://updates.example.test/",
                "access_key": "tester-key",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(updater, "get_app_root", lambda: tmp_path)

    calls: list[tuple[str, dict[str, str]]] = []

    def fake_get(url: str, *, headers: dict[str, str], timeout: int, **_kwargs):
        calls.append((url, headers))
        return _Response(
            {
                "tag_name": "v9.9.9",
                "name": "Private release",
                "body": "Gateway result",
                "published_at": "2026-09-21T00:00:00Z",
                "assets": [
                    {
                        "name": "FoundryDock-update.zip",
                        "download_url": "https://updates.example.test/v1/releases/assets/42",
                    }
                ],
            }
        )

    monkeypatch.setattr(updater.requests, "get", fake_get)

    service = updater.ApplicationUpdateService("0.1.3")
    info = service.check()

    assert service.release_url == "https://updates.example.test/v1/releases/latest"
    assert info is not None
    assert info.asset_url.endswith("/v1/releases/assets/42")
    assert calls[0][1]["X-FoundryDock-Update-Key"] == "tester-key"
    assert "Authorization" not in calls[0][1]


def test_public_release_fallback_does_not_require_private_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(updater, "get_app_root", lambda: tmp_path)
    monkeypatch.delenv("FOUNDRYDOCK_UPDATE_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDRYDOCK_UPDATE_ACCESS_KEY", raising=False)

    calls: list[tuple[str, dict[str, str]]] = []

    def fake_get(url: str, *, headers: dict[str, str], timeout: int, **_kwargs):
        calls.append((url, headers))
        return _Response({"tag_name": "v0.1.3", "assets": []})

    monkeypatch.setattr(updater.requests, "get", fake_get)

    service = updater.ApplicationUpdateService("0.1.3")
    service.check()

    assert service.release_url == updater.LATEST_RELEASE_API
    assert "X-FoundryDock-Update-Key" not in calls[0][1]
    assert calls[0][1]["X-GitHub-Api-Version"] == "2022-11-28"


def test_private_key_without_explicit_url_uses_production_gateway(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(updater, "get_app_root", lambda: tmp_path)
    monkeypatch.delenv("FOUNDRYDOCK_UPDATE_BASE_URL", raising=False)
    monkeypatch.setenv("FOUNDRYDOCK_UPDATE_ACCESS_KEY", "tester-key")

    service = updater.ApplicationUpdateService("0.1.3")

    assert service.release_url == f"{updater.DEFAULT_UPDATE_GATEWAY_BASE_URL}/v1/releases/latest"
    assert service._headers()["X-FoundryDock-Update-Key"] == "tester-key"
