from __future__ import annotations

import json

import pytest

from services.esologs_client import EsoLogsApiError, EsoLogsClient


class _FakeResponse:

    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _client() -> EsoLogsClient:

    client = EsoLogsClient(client_id="id", client_secret="secret")

    # Skip the OAuth round-trip for these tests -- token handling is
    # already covered elsewhere and isn't what these tests exercise.
    client._token = "fake-token"
    client._token_expires_at = 10**12

    return client


# --------------------------------------------------
# get_trial_zones
# --------------------------------------------------


def test_trial_zones_filters_to_known_trials(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "worldData": {
                "zones": [
                    {
                        "id": 15,
                        "name": "Rockgrove",
                        "encounters": [{"id": 63, "name": "Oaxiltso"}],
                    },
                    {
                        "id": 999,
                        "name": "Some Random Dungeon",
                        "encounters": [{"id": 1000, "name": "Trash Boss"}],
                    },
                    {
                        "id": 20,
                        "name": "sanctum ophidia",  # case-insensitive match
                        "encounters": [{"id": 88, "name": "Direfrost"}],
                    },
                ]
            }
        }
    }

    monkeypatch.setattr(
        "requests.post",
        lambda *a, **kw: _FakeResponse(payload),
    )

    zones = client.get_trial_zones()

    names = [z["name"] for z in zones]

    assert "Rockgrove" in names
    assert "sanctum ophidia" in names
    assert "Some Random Dungeon" not in names

    rockgrove = next(z for z in zones if z["name"] == "Rockgrove")

    assert rockgrove["id"] == 15
    assert rockgrove["encounters"] == [{"id": 63, "name": "Oaxiltso"}]


def test_trial_zones_drops_trials_with_no_encounters(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "worldData": {
                "zones": [
                    {"id": 15, "name": "Rockgrove", "encounters": []},
                ]
            }
        }
    }

    monkeypatch.setattr(
        "requests.post",
        lambda *a, **kw: _FakeResponse(payload),
    )

    assert client.get_trial_zones() == []


# --------------------------------------------------
# get_top_report_for_encounter
# --------------------------------------------------


def test_top_report_reads_code_and_fight_id(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "worldData": {
                "encounter": {
                    "characterRankings": {
                        "rankings": [
                            {
                                "name": "Xx_Healbot_xX",
                                "report": {"code": "AbCd1234", "fightID": 7},
                            }
                        ]
                    }
                }
            }
        }
    }

    monkeypatch.setattr(
        "requests.post",
        lambda *a, **kw: _FakeResponse(payload),
    )

    code, fight_id = client.get_top_report_for_encounter(15, 63)

    assert code == "AbCd1234"
    assert fight_id == 7


def test_top_report_does_not_send_zone_id_argument(monkeypatch):
    """
    Regression test: a live call confirmed ESO Logs rejects a zoneID
    argument on Encounter.characterRankings ("Unknown argument
    zoneID on field characterRankings of type Encounter"). zone_id
    stays in the Python method signature for call-site symmetry, but
    must never be sent as a GraphQL variable/argument again.
    """

    client = _client()

    payload = {
        "data": {
            "worldData": {
                "encounter": {
                    "characterRankings": {
                        "rankings": [
                            {"report": {"code": "AbCd1234", "fightID": 7}}
                        ]
                    }
                }
            }
        }
    }

    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["query"] = json.get("query", "")
        captured["variables"] = json.get("variables", {})
        return _FakeResponse(payload)

    monkeypatch.setattr("requests.post", fake_post)

    client.get_top_report_for_encounter(15, 63)

    assert "zoneID" not in captured["variables"]
    assert "zoneID" not in captured["query"]


def test_top_report_raises_clearly_on_unexpected_shape(monkeypatch):

    client = _client()

    payload = {"data": {"worldData": {"encounter": {"characterRankings": {}}}}}

    monkeypatch.setattr(
        "requests.post",
        lambda *a, **kw: _FakeResponse(payload),
    )

    with pytest.raises(EsoLogsApiError):
        client.get_top_report_for_encounter(15, 63)


# --------------------------------------------------
# get_report_player_summary
# --------------------------------------------------


def test_report_player_summary_returns_player_details(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "table": {
                        "data": {
                            "playerDetails": {
                                "tanks": [{"name": "TankyMcTank"}],
                                "healers": [],
                                "dps": [],
                            }
                        }
                    }
                }
            }
        }
    }

    monkeypatch.setattr(
        "requests.post",
        lambda *a, **kw: _FakeResponse(payload),
    )

    details = client.get_report_player_summary("AbCd1234", 7, 0.0, 100000.0)

    assert details["tanks"][0]["name"] == "TankyMcTank"


def test_report_player_summary_raises_when_missing(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {"table": {"data": {}}}
            }
        }
    }

    monkeypatch.setattr(
        "requests.post",
        lambda *a, **kw: _FakeResponse(payload),
    )

    with pytest.raises(EsoLogsApiError):
        client.get_report_player_summary("AbCd1234", 7, 0.0, 100000.0)
