from __future__ import annotations

import json

import services.finch_api_client as module
from services.finch_api_client import FinchApiClient


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_publish_shared_team_uses_put_and_parses_snapshot(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            {
                "ok": True,
                "snapshot": {
                    "kind": "team",
                    "snapshot_key": "performance mode",
                    "schema_version": 1,
                    "payload": {"team_name": "Performance Mode"},
                    "published_by": "Jarakeen",
                    "updated_at": "2026-09-20T00:00:00+00:00",
                },
            }
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    client = FinchApiClient(base_url="https://finch.example", api_key="secret")

    snapshot = client.publish_shared_team(
        snapshot_key="Performance Mode",
        payload={"team_name": "Performance Mode"},
    )

    assert captured["method"] == "PUT"
    assert captured["url"].endswith("/api/v1/shared/teams/Performance%20Mode")
    assert captured["body"]["schema_version"] == 1
    assert snapshot.snapshot_key == "performance mode"
    assert snapshot.published_by == "Jarakeen"


def test_shared_raid_plan_reads_exact_encoded_key(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return _Response(
            {
                "snapshot": {
                    "kind": "raid_plan",
                    "snapshot_key": "rg / pm",
                    "schema_version": 1,
                    "payload": {"plan_id": "RG / PM"},
                    "published_by": "BFF",
                    "updated_at": "2026-09-20T00:00:00+00:00",
                }
            }
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    client = FinchApiClient(base_url="https://finch.example", api_key="secret")

    snapshot = client.shared_raid_plan("RG / PM")

    assert captured["url"].endswith("/api/v1/shared/raid-plans/RG%20%2F%20PM")
    assert snapshot.payload["plan_id"] == "RG / PM"
