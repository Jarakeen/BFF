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


def _respond(monkeypatch, payload: dict):

    monkeypatch.setattr(
        "requests.post",
        lambda *a, **kw: _FakeResponse(payload),
    )


# --------------------------------------------------
# get_aura_table (still routes through _fetch_table_data)
# --------------------------------------------------


def test_get_aura_table_still_returns_auras(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "table": {"data": {"auras": [{"name": "Major Courage", "totalUptime": 90000.0}]}}
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    auras = client.get_aura_table("ABC123", 1, 0.0, 100000.0, source_id=7)

    assert auras == [{"name": "Major Courage", "totalUptime": 90000.0}]


def test_get_aura_table_passes_target_id(monkeypatch):

    client = _client()

    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["variables"] = json["variables"]
        return _FakeResponse(
            {"data": {"reportData": {"report": {"table": {"data": {"auras": []}}}}}}
        )

    monkeypatch.setattr("requests.post", fake_post)

    client.get_aura_table(
        "ABC123", 1, 0.0, 1000.0, data_type="Buffs", target_id=7,
    )

    assert captured["variables"]["targetID"] == 7
    assert captured["variables"]["sourceID"] is None


# --------------------------------------------------
# get_actor_table
# --------------------------------------------------


def test_get_actor_table_returns_entries_and_reported_total(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "table": {
                        "data": {
                            "entries": [
                                {"name": "Vault polar wind", "total": 1200000.0},
                                {"name": "Force Pulse", "total": 800000.0},
                            ],
                            "total": 2000000.0,
                        }
                    }
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    entries, total = client.get_actor_table(
        "ABC123", 1, 0.0, 100000.0,
        data_type="DamageDone",
        hostility_type="Enemies",
        source_id=7,
        view_by="Ability",
    )

    assert len(entries) == 2
    assert total == 2000000.0


def test_get_actor_table_falls_back_to_summed_total_when_missing(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "table": {
                        "data": {
                            "entries": [
                                {"name": "A", "total": 10.0},
                                {"name": "B", "total": 5.0},
                            ]
                        }
                    }
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    entries, total = client.get_actor_table(
        "ABC123", 1, 0.0, 1000.0, data_type="Healing",
    )

    assert total == 15.0


def test_get_actor_table_raises_on_missing_entries(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {"table": {"data": {"total": 100.0}}}
            }
        }
    }

    _respond(monkeypatch, payload)

    with pytest.raises(EsoLogsApiError):
        client.get_actor_table("ABC123", 1, 0.0, 1000.0, data_type="Healing")


def test_get_actor_table_passes_source_id_and_view_by(monkeypatch):

    client = _client()

    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["variables"] = json["variables"]
        return _FakeResponse(
            {"data": {"reportData": {"report": {"table": {"data": {"entries": [], "total": 0.0}}}}}}
        )

    monkeypatch.setattr("requests.post", fake_post)

    client.get_actor_table(
        "ABC123", 1, 0.0, 1000.0,
        data_type="Healing",
        source_id=7,
        view_by="Ability",
    )

    assert captured["variables"]["sourceID"] == 7
    assert captured["variables"]["viewBy"] == "Ability"


# --------------------------------------------------
# get_output_graph
# --------------------------------------------------


def test_get_output_graph_parses_flat_bucket_array_and_prefers_total_row(monkeypatch):
    """
    The real v2 shape, confirmed against a live report: each series
    is one ability with pointStart/pointInterval (ms) + a flat
    array of per-bucket amounts, plus one "Total" row that's the
    actor's combined amount per bucket -- that Total row is what
    the chart should use, not a naive merge of every ability.
    """

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "graph": {
                        "data": {
                            "series": [
                                {
                                    "name": "Combat Prayer",
                                    "guid": 40094,
                                    "pointStart": 0,
                                    "pointInterval": 1000.0,
                                    "total": 300.0,
                                    "data": [100.0, 200.0],
                                },
                                {
                                    "name": "Total",
                                    "type": "Total",
                                    "id": "Total",
                                    "pointStart": 0,
                                    "pointInterval": 1000.0,
                                    "data": [150.0, 250.0],
                                },
                            ]
                        }
                    }
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    points = client.get_output_graph(
        "ABC123", 1, 0.0, 2000.0, data_type="Healing", source_id=7,
    )

    # Uses the Total row (150, 250), not the per-ability row (100, 200).
    assert points == [(0.0, 150.0), (1.0, 250.0)]


def test_get_output_graph_falls_back_to_summed_abilities_without_total_row(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "graph": {
                        "data": {
                            "series": [
                                {
                                    "name": "Combat Prayer",
                                    "pointStart": 0,
                                    "pointInterval": 1000.0,
                                    "data": [100.0, 200.0],
                                },
                                {
                                    "name": "Radiating Regeneration",
                                    "pointStart": 0,
                                    "pointInterval": 1000.0,
                                    "data": [50.0, 25.0],
                                },
                            ]
                        }
                    }
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    points = client.get_output_graph(
        "ABC123", 1, 0.0, 2000.0, data_type="Healing", source_id=7,
    )

    assert points == [(0.0, 150.0), (1.0, 225.0)]


def test_get_output_graph_offsets_by_query_start_time(monkeypatch):
    """pointStart is absolute; points should be seconds *into the fight*."""

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "graph": {
                        "data": {
                            "series": [
                                {
                                    "name": "Total",
                                    "type": "Total",
                                    "pointStart": 2144917,
                                    "pointInterval": 1000.0,
                                    "data": [10.0, 20.0],
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    points = client.get_output_graph(
        "ABC123", 1, 2144917.0, 2400669.0, data_type="Healing", source_id=7,
    )

    assert points == [(0.0, 10.0), (1.0, 20.0)]


def test_get_output_graph_parses_legacy_list_style_points(monkeypatch):
    """Defensive fallback for a [t, v]-pair shape, in case some dataType uses it."""

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "graph": {
                        "data": {
                            "series": [
                                {"name": "Bobo", "data": [[0, 1000.0], [1000, 2000.0]]}
                            ]
                        }
                    }
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    points = client.get_output_graph(
        "ABC123", 1, 0.0, 2000.0, data_type="DamageDone", source_id=7,
    )

    assert points == [(0.0, 1000.0), (1.0, 2000.0)]


def test_get_output_graph_parses_legacy_dict_style_points_and_sorts(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "graph": {
                        "data": {
                            "series": [
                                {"name": "Bobo", "data": [{"x": 2000, "y": 50.0}, {"x": 0, "y": 10.0}]}
                            ]
                        }
                    }
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    points = client.get_output_graph(
        "ABC123", 1, 0.0, 2000.0, data_type="Healing", source_id=7,
    )

    assert points == [(0.0, 10.0), (2.0, 50.0)]


def test_get_output_graph_raises_on_missing_series(monkeypatch):

    client = _client()

    payload = {
        "data": {
            "reportData": {"report": {"graph": {"data": {}}}}
        }
    }

    _respond(monkeypatch, payload)

    with pytest.raises(EsoLogsApiError):
        client.get_output_graph("ABC123", 1, 0.0, 1000.0, data_type="Healing")


def test_get_output_graph_matches_live_captured_shape(monkeypatch):
    """
    Regression test built from an actual live response (Lokkestiiz
    veteran hardmode kill, Healing graph, sourceID filtered) so this
    parser can never silently regress back to returning zero points
    for this exact shape again.
    """

    client = _client()

    payload = {
        "data": {
            "reportData": {
                "report": {
                    "graph": {
                        "data": {
                            "series": [
                                {
                                    "name": "Combat Prayer",
                                    "guid": 40094,
                                    "type": 8,
                                    "pointStart": 2144917,
                                    "pointInterval": 1065.6333333333334,
                                    "total": 277085,
                                    "data": [0, 0, 195.8],
                                },
                                {
                                    "name": "Total",
                                    "type": "Total",
                                    "id": "Total",
                                    "pointStart": 2144917,
                                    "pointInterval": 1065.6333333333334,
                                    "data": [342.2, 1073.6, 1460.0],
                                },
                            ],
                            "startTime": 2144917,
                            "endTime": 2400669,
                        }
                    }
                }
            }
        }
    }

    _respond(monkeypatch, payload)

    points = client.get_output_graph(
        "v16hzgGWTV7BZ48f", 22, 2144917.0, 2400669.0,
        data_type="Healing", source_id=7,
    )

    assert points[0] == (0.0, 342.2)
    assert round(points[1][0], 4) == round(1065.6333333333334 / 1000.0, 4)
    assert points[1][1] == 1073.6
