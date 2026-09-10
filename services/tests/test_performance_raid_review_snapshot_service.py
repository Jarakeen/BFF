from __future__ import annotations

from types import SimpleNamespace

from services.performance_raid_review_snapshot_service import (
    PerformanceRaidReviewSnapshotService,
)


class _Client:
    def __init__(self):
        self.fight_calls = 0
        self.aura_calls = []
        self.actor_calls = []

    def get_fight(self, report_code, fight_id):
        self.fight_calls += 1
        return {
            "name": "Xalvakka",
            "kill": False,
            "startTime": 1_000.0,
            "endTime": 11_000.0,
        }

    def get_aura_table(self, report_code, fight_id, start, end, **kwargs):
        self.aura_calls.append(dict(kwargs))
        if kwargs.get("data_type") == "Buffs":
            return [{"name": "Major Courage", "totalUptime": 8_000.0}]
        if kwargs.get("source_id") is not None:
            return [{"name": "Minor Brittle", "totalUptime": 6_000.0}]
        return [{"name": "Major Breach", "totalUptime": 9_000.0}]

    def get_actor_table(self, report_code, fight_id, start, end, **kwargs):
        self.actor_calls.append(dict(kwargs))
        return ([{"name": "Skill", "total": 500_000.0}], 1_000_000.0)


class _PerformanceService:
    def __init__(self):
        self.client = _Client()
        self.capability_service = SimpleNamespace()


def test_two_players_share_fight_and_raid_debuff_fetches() -> None:
    performance = _PerformanceService()
    service = PerformanceRaidReviewSnapshotService(performance)

    first = service.build_snapshot("ABC", 7, 11, "Healer", "Healer")
    second = service.build_snapshot("ABC", 7, 12, "DD", "DPS")

    assert performance.client.fight_calls == 1
    raid_debuff_calls = [
        call for call in performance.client.aura_calls
        if call.get("data_type") == "Debuffs" and call.get("source_id") is None
    ]
    assert len(raid_debuff_calls) == 1
    assert len(performance.client.actor_calls) == 2
    assert first.OutputSeries == []
    assert first.TopAbilities == []
    assert second.OutputSeries == []
    assert second.TopAbilities == []


def test_lean_snapshot_preserves_review_fields_without_dashboard_extras() -> None:
    performance = _PerformanceService()
    snapshot = PerformanceRaidReviewSnapshotService(performance).build_snapshot(
        "ABC", 7, 11, "Magrat", "Healer"
    )

    assert snapshot.FightName == "Xalvakka"
    assert snapshot.FightDurationSeconds == 10.0
    assert snapshot.OutputTotal == 1_000_000.0
    assert snapshot.OutputPerSecond == 100_000.0
    assert [(row.Name, row.UptimePercent) for row in snapshot.BuffUptimes] == [
        ("Major Courage", 80.0)
    ]
    assert [(row.Name, row.UptimePercent) for row in snapshot.DebuffUptimes] == [
        ("Minor Brittle", 60.0)
    ]
    assert [(row.Name, row.UptimePercent) for row in snapshot.RaidDebuffUptimes] == [
        ("Major Breach", 90.0)
    ]
    assert snapshot.PeakWindowLabel == ""
