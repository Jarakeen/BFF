from types import SimpleNamespace

from services.performance_raid_review_landing_recovery_service import RaidReviewLandingRecoveryObservation
from services.performance_raid_review_lokkestiiz_pull_service import LokkestiizPullRaidReviewEvidence
from services.performance_raid_review_lokkestiiz_session_service import (
    LokkestiizRaidReviewPullRequest,
    PerformanceRaidReviewLokkestiizSessionService,
)
from services.performance_raid_review_observation_service import RaidReviewSource
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


class _Client:
    def get_fight(self, report_code, fight_id):
        return {"name": "Lokkestiiz", "startTime": 1000.0, "endTime": 11000.0}


class _PerformanceService:
    def __init__(self):
        self.client = _Client()


class _EventProvider:
    def events_for_fight(self, **kwargs):
        return ()


class _PullService:
    def build(self, **kwargs):
        actor = tuple(kwargs["actors"])[0]
        return LokkestiizPullRaidReviewEvidence(
            boundaries=(
                EncounterObservedClockBoundary(
                    encounter_id="lokkestiiz",
                    fact_key="aerial_onslaught_flight",
                    boundary="end",
                    occurrence=1,
                    time_seconds=70.0,
                    source="reviewed runtime evidence",
                ),
            ),
            mechanic_windows=(),
            recovery_observations=(
                RaidReviewLandingRecoveryObservation(
                    report_code=kwargs["report_code"],
                    fight_id=kwargs["fight_id"],
                    occurrence=1,
                    actor_id=actor.actor_id,
                    actor_label=actor.actor_label,
                    role=actor.role,
                    member_key=actor.member_key,
                    landing_seconds=70.0,
                    recovery_seconds=71.0,
                    delay_seconds=1.0,
                    signal_semantic_key="boss_damage_reacquisition_after_landing",
                    signal_label="Boss Damage Reacquisition",
                ),
            ),
        )


class _Coordinator:
    def __init__(self):
        self.calls = []

    def review(self, sources, **kwargs):
        self.calls.append((tuple(sources), kwargs))
        return SimpleNamespace(
            unresolved=(),
            report=SimpleNamespace(encounter_name="Lokkestiiz"),
            collection=SimpleNamespace(observations=()),
        )


def test_session_preserves_one_dd_reacquisition_opportunity_per_observed_landing() -> None:
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=_EventProvider(),
        pull_service=_PullService(),
        coordinator_service=coordinator,
    )
    source = RaidReviewSource("A", 1, 7, "DD One", "DPS", member_key="dd-one")

    result = service.review([LokkestiizRaidReviewPullRequest("A", 1, 99, (source,))])

    assert len(result.landing_recovery_opportunities) == 1
    opportunity = result.landing_recovery_opportunities[0]
    assert opportunity.occurrence == 1
    assert opportunity.actor_id == 7
    assert opportunity.member_key == "dd-one"
    assert opportunity.signal_semantic_key == "boss_damage_reacquisition_after_landing"
    _sources, kwargs = coordinator.calls[0]
    assert kwargs["landing_recovery_opportunities"] == result.landing_recovery_opportunities


def test_session_does_not_create_dd_opportunity_for_healer() -> None:
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=_EventProvider(),
        pull_service=_PullService(),
        coordinator_service=coordinator,
    )
    source = RaidReviewSource("A", 1, 11, "Healer One", "Healer", member_key="healer-one")

    result = service.review([LokkestiizRaidReviewPullRequest("A", 1, 99, (source,))])

    assert result.landing_recovery_opportunities == ()
