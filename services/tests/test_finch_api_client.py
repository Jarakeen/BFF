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
