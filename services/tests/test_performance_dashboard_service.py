from __future__ import annotations

from services.performance_dashboard_service import (
    PerformanceDashboardService,
    _peak_window_label,
    _top_abilities,
    _top_uptimes,
)


class _FakeClient:

    def __init__(self, fight=None, player_details=None, auras_by_call=None,
                 actor_table=None, graph_points=None):

        self._fight = fight or {
            "startTime": 0.0, "endTime": 100000.0, "name": "Test Fight",
            "kill": True, "bossPercentage": None,
        }
        self._player_details = player_details or {}
        self._auras_by_call = list(auras_by_call or [])
        self._actor_table = actor_table or ([], 0.0)
        self._graph_points = graph_points or []

        self.aura_calls = []
        self.actor_table_calls = []
        self.graph_calls = []

    def get_fight(self, report_code, fight_id):
        return self._fight

    def get_report_player_summary(self, report_code, fight_id, start_time, end_time):
        return self._player_details

    def get_aura_table(self, report_code, fight_id, start_time, end_time, **kwargs):
        self.aura_calls.append(kwargs)
        if self._auras_by_call:
            return self._auras_by_call.pop(0)
        return []

    def get_actor_table(self, report_code, fight_id, start_time, end_time, **kwargs):
        self.actor_table_calls.append(kwargs)
        return self._actor_table

    def get_output_graph(self, report_code, fight_id, start_time, end_time, **kwargs):
        self.graph_calls.append(kwargs)
        return self._graph_points


# --------------------------------------------------
# list_actors
# --------------------------------------------------


def test_list_actors_labels_anonymous_players():

    client = _FakeClient(
        player_details={
            "healers": [{"id": 7, "name": None, "type": "Templar", "anonymous": True}],
            "dps": [{"id": 3, "name": "Bobo", "type": "Nightblade", "anonymous": False}],
            "tanks": [],
        }
    )

    service = PerformanceDashboardService(client)

    summary, choices = service.list_actors("ABC123", 1)

    assert summary["name"] == "Test Fight"

    by_id = {c.ActorId: c for c in choices}

    assert by_id[7].Label == "Anonymous 7 -- Templar"
    assert by_id[7].Role == "Healer"
    assert by_id[7].Anonymous is True

    assert by_id[3].Label == "Bobo -- Nightblade"
    assert by_id[3].Role == "DPS"
    assert by_id[3].Anonymous is False


def test_list_actors_handles_flat_list_shape():

    client = _FakeClient(
        player_details=[
            {"id": 9, "name": "Solo Healer", "type": "Warden", "role": "healer"},
        ]
    )

    service = PerformanceDashboardService(client)

    _, choices = service.list_actors("ABC123", 1)

    assert choices[0].Role == "Healer"
    assert choices[0].ActorId == 9


def test_list_actors_skips_entries_without_id():

    client = _FakeClient(
        player_details={"dps": [{"name": "No Id"}], "healers": [], "tanks": []}
    )

    service = PerformanceDashboardService(client)

    _, choices = service.list_actors("ABC123", 1)

    assert choices == []


# --------------------------------------------------
# build_snapshot
# --------------------------------------------------


def test_build_snapshot_scopes_every_query_to_the_chosen_actor():

    client = _FakeClient(
        auras_by_call=[
            [{"name": "Major Courage", "totalUptime": 90000.0}],  # buffs
            [{"name": "Minor Vulnerability", "totalUptime": 50000.0}],  # debuffs
        ],
        actor_table=(
            [{"name": "Force Pulse", "total": 800000.0}],
            800000.0,
        ),
        graph_points=[(0.0, 1000.0), (10.0, 4000.0)],
    )

    service = PerformanceDashboardService(client)

    snapshot = service.build_snapshot(
        "ABC123", 1, actor_id=7, actor_label="Anonymous 7 -- Templar", role="DPS",
    )

    assert client.aura_calls[0]["source_id"] == 7
    assert client.aura_calls[0]["data_type"] == "Buffs"
    assert client.aura_calls[0]["hostility_type"] == "Friendlies"

    assert client.aura_calls[1]["source_id"] == 7
    assert client.aura_calls[1]["data_type"] == "Debuffs"
    assert client.aura_calls[1]["hostility_type"] == "Enemies"

    assert client.actor_table_calls[0]["source_id"] == 7
    assert client.actor_table_calls[0]["data_type"] == "DamageDone"
    assert client.actor_table_calls[0]["view_by"] == "Ability"

    assert client.graph_calls[0]["source_id"] == 7
    assert client.graph_calls[0]["data_type"] == "DamageDone"

    assert snapshot.OutputTotal == 800000.0
    assert snapshot.OutputPerSecond == 8000.0  # 800000 / 100s
    assert snapshot.OutputRateLabel == "DPS"
    assert snapshot.BuffUptimes[0].Name == "Major Courage"
    assert snapshot.DebuffUptimes[0].Name == "Minor Vulnerability"
    assert snapshot.TopAbilities[0].Name == "Force Pulse"


def test_build_snapshot_uses_healing_output_for_healer_role():

    client = _FakeClient(
        actor_table=([{"name": "Combat Prayer", "total": 500000.0}], 500000.0),
    )

    service = PerformanceDashboardService(client)

    snapshot = service.build_snapshot(
        "ABC123", 1, actor_id=7, actor_label="Me", role="Healer",
    )

    assert client.actor_table_calls[0]["data_type"] == "Healing"
    assert client.actor_table_calls[0]["hostility_type"] == "Friendlies"
    assert snapshot.OutputLabel == "Healing"
    assert snapshot.OutputRateLabel == "HPS"


# --------------------------------------------------
# _top_uptimes / _top_abilities (pure helpers)
# --------------------------------------------------


def test_top_uptimes_sorts_and_caps_and_clamps_percent():

    auras = [
        {"name": "Short", "totalUptime": 1000.0},
        {"name": "Full Uptime", "totalUptime": 200000.0},  # would be 200% of a 100s fight
        {"name": "", "totalUptime": 5000.0},  # unnamed, dropped
    ]

    rows = _top_uptimes(auras, duration_seconds=100.0, limit=5)

    assert [r.Name for r in rows] == ["Full Uptime", "Short"]
    assert rows[0].UptimePercent == 100.0  # clamped, not 200


def test_top_abilities_computes_percent_of_total():

    entries = [{"name": "A", "total": 30.0}, {"name": "B", "total": 70.0}]

    rows = _top_abilities(entries, total=100.0, limit=5)

    assert rows[0].Name == "B"
    assert rows[0].Percent == 70.0
    assert rows[1].Percent == 30.0


# --------------------------------------------------
# _peak_window_label
# --------------------------------------------------


def test_peak_window_label_finds_the_highest_summed_window():

    points = [
        (0.0, 100.0), (2.0, 100.0), (4.0, 100.0),  # low stretch
        (20.0, 5000.0), (22.0, 5000.0), (24.0, 5000.0),  # hot stretch
        (40.0, 100.0),
    ]

    label = _peak_window_label(points, window_seconds=10.0, rate_label="DPS")

    assert label == "Best 10s stretch: 0:20-0:24 at 3,750 DPS"


def test_peak_window_label_handles_too_little_data():

    assert "Not enough data" in _peak_window_label([], 10.0, "DPS")
    assert "Not enough data" in _peak_window_label([(0.0, 5.0)], 10.0, "DPS")
