from types import SimpleNamespace

from services.performance_raid_review_healer_effect_coverage_service import (
    RaidReviewHealerEffectRequirement,
)
from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
)
from services.performance_raid_review_lokkestiiz_pull_service import (
    LokkestiizPullRaidReviewEvidence,
)
from services.performance_raid_review_lokkestiiz_session_service import (
    LokkestiizRaidReviewPullRequest,
    PerformanceRaidReviewLokkestiizSessionService,
)
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow
from services.performance_raid_review_observation_service import RaidReviewSource


class _Client:
    def __init__(self):
        self.fights = {
            ("A", 1): {"name": "Lokkestiiz", "startTime": 1000.0, "endTime": 11000.0},
            ("A", 2): {"name": "Lokkestiiz", "startTime": 12000.0, "endTime": 22000.0},
            ("A", 3): {"name": "Yolnahkriin", "startTime": 23000.0, "endTime": 33000.0},
        }

    def get_fight(self, report_code, fight_id):
        return self.fights[(report_code, fight_id)]


class _PerformanceService:
    def __init__(self):
        self.client = _Client()


class _EventProvider:
    def __init__(self):
        self.calls = []

    def events_for_fight(self, *, report_code, fight_id, start_time, end_time):
        self.calls.append((report_code, fight_id, start_time, end_time))
        return ({"timestamp": start_time + 100.0, "type": "cast"},)


class _AuraEventProvider(_EventProvider):
    def events_for_fight(self, *, report_code, fight_id, start_time, end_time):
        self.calls.append((report_code, fight_id, start_time, end_time))
        return (
            {"timestamp": start_time + 500.0, "type": "applybuff", "sourceID": 11, "targetID": 21, "abilityName": "Major Courage"},
            {"timestamp": start_time + 2500.0, "type": "removebuff", "sourceID": 11, "targetID": 21, "abilityName": "Major Courage"},
        )


class _PullService:
    def __init__(self):
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        fight_id = int(kwargs["fight_id"])
        source = f"pull-{fight_id}"
        window = RaidReviewEncounterWindow(
            report_code=kwargs["report_code"],
            fight_id=fight_id,
            semantic_key=f"flight_{fight_id}",
            label=f"Flight {fight_id}",
            start_seconds=1.0,
            end_seconds=2.0,
            evidence_source=source,
        )
        actor = tuple(kwargs["actors"])[0]
        recovery = RaidReviewLandingRecoveryObservation(
            report_code=kwargs["report_code"],
            fight_id=fight_id,
            occurrence=1,
            actor_id=actor.actor_id,
            actor_label=actor.actor_label,
            role=actor.role,
            member_key=actor.member_key,
            landing_seconds=2.0,
            recovery_seconds=3.0,
            delay_seconds=1.0,
            signal_semantic_key="boss_damage_reacquisition_after_landing",
            signal_label="Boss Damage Reacquisition",
        )
        return LokkestiizPullRaidReviewEvidence(
            boundaries=(),
            mechanic_windows=(window,),
            recovery_observations=(recovery,),
            unresolved=(("sample pull gap",) if fight_id == 2 else ()),
        )


class _Coordinator:
    def __init__(self, unresolved=()):
        self.calls = []
        self._unresolved = tuple(unresolved)

    def review(self, sources, **kwargs):
        self.calls.append((tuple(sources), kwargs))
        return SimpleNamespace(
            unresolved=self._unresolved,
            report=SimpleNamespace(encounter_name=kwargs.get("encounter_name")),
            collection=SimpleNamespace(observations=()),
        )


def _source(fight_id: int, actor_id: int = 7) -> RaidReviewSource:
    return RaidReviewSource(
        "A",
        fight_id,
        actor_id,
        "DD One",
        "DPS",
        member_key="dd-one",
    )


def _healer_source(fight_id: int) -> RaidReviewSource:
    return RaidReviewSource(
        "A",
        fight_id,
        11,
        "Healer One",
        "Healer",
        member_key="healer-one",
    )


def test_session_aggregates_pull_evidence_into_one_generic_review() -> None:
    events = _EventProvider()
    pulls = _PullService()
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=events,
        pull_service=pulls,
        coordinator_service=coordinator,
    )

    result = service.review(
        [
            LokkestiizRaidReviewPullRequest("A", 1, 99, (_source(1),)),
            LokkestiizRaidReviewPullRequest("A", 2, 99, (_source(2),)),
        ]
    )

    assert len(result.pull_evidence) == 2
    assert len(events.calls) == 2
    assert len(pulls.calls) == 2
    sources, kwargs = coordinator.calls[0]
    assert len(sources) == 2
    assert kwargs["encounter_name"] == "Lokkestiiz"
    assert len(kwargs["mechanic_windows"]) == 2
    assert len(kwargs["landing_recovery_observations"]) == 2
    assert "A #2: sample pull gap" in result.unresolved


def test_session_skips_non_lokkestiiz_fight_before_runtime_event_fetch() -> None:
    events = _EventProvider()
    pulls = _PullService()
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=events,
        pull_service=pulls,
        coordinator_service=coordinator,
    )

    result = service.review(
        [LokkestiizRaidReviewPullRequest("A", 3, 99, (_source(3),))]
    )

    assert events.calls == []
    assert pulls.calls == []
    assert result.pull_evidence == ()
    assert any("not Lokkestiiz" in message for message in result.unresolved)


def test_session_preserves_generic_coordinator_unresolved_evidence() -> None:
    coordinator = _Coordinator(unresolved=("generic observation gap",))
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=_EventProvider(),
        pull_service=_PullService(),
        coordinator_service=coordinator,
    )

    result = service.review(
        [LokkestiizRaidReviewPullRequest("A", 1, 99, (_source(1),))]
    )

    assert "generic observation gap" in result.unresolved


def test_empty_session_fails_closed_without_inventing_pull_evidence() -> None:
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=_EventProvider(),
        pull_service=_PullService(),
        coordinator_service=coordinator,
    )

    result = service.review([])

    assert result.pull_evidence == ()
    assert result.unresolved == ("No Lokkestiiz pulls were supplied for Raid Review.",)
    sources, kwargs = coordinator.calls[0]
    assert sources == ()
    assert kwargs["encounter_name"] == "Lokkestiiz"


def test_session_projects_reviewed_healer_effect_coverage_from_same_fight_events() -> None:
    events = _AuraEventProvider()
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=events,
        pull_service=_PullService(),
        coordinator_service=coordinator,
    )

    result = service.review(
        [LokkestiizRaidReviewPullRequest("A", 1, 99, (_healer_source(1),))],
        healer_effect_requirements=(
            RaidReviewHealerEffectRequirement(
                semantic_key="major_courage_precoverage",
                label="Major Courage Pre-Coverage",
                effect_names=("Major Courage",),
                mechanic_keys=("flight_1",),
                source_actor_id=11,
            ),
        ),
    )

    assert len(events.calls) == 1
    assert len(result.healer_effect_coverage) == 1
    observation = result.healer_effect_coverage[0]
    assert observation.covered
    assert observation.mechanic_semantic_key == "flight_1"
    assert observation.requirement_semantic_key == "major_courage_precoverage"
    assert observation.active_effect_names == ("Major Courage",)
