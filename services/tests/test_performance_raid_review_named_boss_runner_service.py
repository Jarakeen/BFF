from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.performance_raid_review_named_boss_runner_service import (
    PerformanceRaidReviewNamedBossRunnerService,
)


class _Client:
    def __init__(self, fights):
        self.fights = list(fights)

    @staticmethod
    def normalize_report_code(value):
        return str(value or "").strip().replace("https://www.esologs.com/reports/", "")

    def get_fights(self, report_code):
        return list(self.fights)

    def get_fight(self, report_code, fight_id):
        for fight in self.fights:
            if int(fight.get("id") or 0) == int(fight_id):
                return dict(fight)
        raise ValueError("missing fight")


class _PerformanceService:
    def __init__(self, fights, actors_by_fight=None):
        self.client = _Client(fights)
        self.actors_by_fight = actors_by_fight or {}

    def list_actors(self, report_code, fight_id):
        return {}, tuple(self.actors_by_fight.get(int(fight_id), ()))


class _Coordinator:
    def __init__(self):
        self.calls = []
        self.result = SimpleNamespace(unresolved=("shared unresolved",))

    def review(self, sources, *, encounter_name=None):
        self.calls.append((tuple(sources), encounter_name))
        return self.result


def _fight(fight_id, name, *, kill=False, boss_percentage=None, duration_ms=10000):
    return {
        "id": fight_id,
        "name": name,
        "kill": kill,
        "bossPercentage": boss_percentage,
        "startTime": 1000,
        "endTime": 1000 + duration_ms,
    }


def test_named_boss_runner_requires_explicit_boss_name() -> None:
    with pytest.raises(ValueError, match="non-empty boss name"):
        PerformanceRaidReviewNamedBossRunnerService("")


def test_list_fights_filters_to_named_boss_and_preserves_pull_metadata() -> None:
    performance = _PerformanceService(
        [
            _fight(8, "Xalvakka", kill=True, boss_percentage=0, duration_ms=123456),
            _fight(3, "Oaxiltso", boss_percentage=4512),
            _fight(4, "xalvakka", boss_percentage=1789, duration_ms=55000),
        ]
    )
    runner = PerformanceRaidReviewNamedBossRunnerService(
        "Xalvakka",
        performance_service_factory=lambda: performance,
    )

    choices = runner.list_fights("ABC123")

    assert [row.fight_id for row in choices] == [4, 8]
    assert choices[0].kill is False
    assert choices[0].boss_percentage == 1789.0
    assert choices[0].duration_seconds == 55.0
    assert choices[1].kill is True


def test_review_report_builds_report_scoped_sources_and_delegates_shared_review() -> None:
    performance = _PerformanceService(
        [_fight(4, "Xalvakka"), _fight(8, "Xalvakka", kill=True)],
        actors_by_fight={
            4: (
                SimpleNamespace(ActorId=11, Label="Healer A", Role="Healer"),
                SimpleNamespace(ActorId=22, Label="DD A", Role="DPS"),
            ),
            8: (
                SimpleNamespace(ActorId=11, Label="Healer A", Role="Healer"),
            ),
        },
    )
    coordinator = _Coordinator()
    runner = PerformanceRaidReviewNamedBossRunnerService(
        "Xalvakka",
        performance_service_factory=lambda: performance,
        coordinator_factory=lambda _: coordinator,
    )

    result = runner.review_report("ABC123", [4, 8])

    assert result.review is coordinator.result
    assert result.unresolved == ("shared unresolved",)
    assert len(coordinator.calls) == 1
    sources, encounter_name = coordinator.calls[0]
    assert encounter_name == "Xalvakka"
    assert [(row.fight_id, row.actor_id) for row in sources] == [(4, 11), (4, 22), (8, 11)]
    assert [row.member_key for row in sources] == ["abc123:11", "abc123:22", "abc123:11"]


def test_review_report_skips_wrong_encounter_and_keeps_unresolved_evidence() -> None:
    performance = _PerformanceService(
        [_fight(4, "Oaxiltso"), _fight(8, "Xalvakka")],
        actors_by_fight={
            8: (SimpleNamespace(ActorId=11, Label="Healer A", Role="Healer"),),
        },
    )
    coordinator = _Coordinator()
    coordinator.result = SimpleNamespace(unresolved=())
    runner = PerformanceRaidReviewNamedBossRunnerService(
        "Xalvakka",
        performance_service_factory=lambda: performance,
        coordinator_factory=lambda _: coordinator,
    )

    result = runner.review_report("ABC123", [4, 8])

    assert result.review is coordinator.result
    assert len(result.unresolved) == 1
    assert "not Xalvakka" in result.unresolved[0]
    sources, _ = coordinator.calls[0]
    assert {(row.fight_id, row.actor_id) for row in sources} == {(8, 11)}


def test_review_report_fails_closed_when_no_selected_pull_can_supply_players() -> None:
    performance = _PerformanceService([_fight(4, "Xalvakka")])
    coordinator = _Coordinator()
    runner = PerformanceRaidReviewNamedBossRunnerService(
        "Xalvakka",
        performance_service_factory=lambda: performance,
        coordinator_factory=lambda _: coordinator,
    )

    result = runner.review_report("ABC123", [4])

    assert result.review is None
    assert "No friendly player actors" in result.unresolved[0]
    assert coordinator.calls == []
