from __future__ import annotations

from services.finch_api_client import FinchApiClient, FinchApiError


def test_finch_api_client_requires_url_and_key() -> None:
    try:
        FinchApiClient(base_url="", api_key="secret")
    except FinchApiError as exc:
        assert "URL" in str(exc)
    else:
        raise AssertionError("missing URL should fail")

    try:
        FinchApiClient(base_url="https://finch.example", api_key="")
    except FinchApiError as exc:
        assert "key" in str(exc).casefold()
    else:
        raise AssertionError("missing API key should fail")


def test_finch_api_client_status_projection(monkeypatch) -> None:
    client = FinchApiClient(
        base_url="https://finch.example/",
        api_key="secret",
    )

    monkeypatch.setattr(
        client,
        "_request_json",
        lambda path: {
            "ok": True,
            "service": "Finch",
            "api_version": "v1",
            "discord_ready": True,
            "discord_user": "Finch#0001",
            "database_ready": True,
        },
    )

    result = client.test_connection()

    assert result.ok is True
    assert result.service == "Finch"
    assert result.api_version == "v1"
    assert result.discord_ready is True
    assert result.discord_user == "Finch#0001"
    assert result.database_ready is True


def test_finch_api_client_publishes_shared_team_to_quoted_key(monkeypatch) -> None:
    client = FinchApiClient(base_url="https://finch.example", api_key="secret")
    calls = []

    def request(path, *, method="GET", payload=None):
        calls.append((path, method, payload))
        return {
            "snapshot": {
                "kind": "team",
                "snapshot_key": "Performance Mode",
                "schema_version": 1,
                "payload": {"team_name": "Performance Mode"},
                "published_by": "Jarakeen",
                "updated_at": "2026-09-20T00:00:00+00:00",
            }
        }

    monkeypatch.setattr(client, "_request_json", request)

    result = client.publish_shared_team(
        snapshot_key="Performance Mode",
        payload={"team_name": "Performance Mode"},
    )

    assert calls == [
        (
            "/api/v1/shared/teams/Performance%20Mode",
            "PUT",
            {
                "schema_version": 1,
                "payload": {"team_name": "Performance Mode"},
            },
        )
    ]
    assert result.kind == "team"
    assert result.snapshot_key == "Performance Mode"


def test_finch_api_client_publishes_shared_raid_plan_by_stable_id(monkeypatch) -> None:
    client = FinchApiClient(base_url="https://finch.example", api_key="secret")
    calls = []

    def request(path, *, method="GET", payload=None):
        calls.append((path, method, payload))
        return {
            "snapshot": {
                "kind": "raid_plan",
                "snapshot_key": "plan/id",
                "schema_version": 1,
                "payload": {"plan_id": "plan/id"},
                "published_by": "Jarakeen",
                "updated_at": "2026-09-20T00:00:00+00:00",
            }
        }

    monkeypatch.setattr(client, "_request_json", request)

    result = client.publish_shared_raid_plan(
        snapshot_key="plan/id",
        payload={"plan_id": "plan/id"},
    )

    assert calls[0][0] == "/api/v1/shared/raid-plans/plan%2Fid"
    assert calls[0][1] == "PUT"
    assert calls[0][2]["schema_version"] == 1
    assert result.snapshot_key == "plan/id"
