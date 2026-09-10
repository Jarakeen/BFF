from types import SimpleNamespace

from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
    RaidReviewRecoverySignal,
)
from services.performance_raid_review_lokkestiiz_pull_service import (
    LokkestiizPullRaidReviewEvidence,
)
from services.performance_raid_review_lokkestiiz_session_service import (
    LokkestiizRaidReviewPullRequest,
    PerformanceRaidReviewLokkestiizSessionService,
)
from services.performance_raid_review_observation_service import RaidReviewSource
from services.performance_raid_review_tank_recovery_service import RaidReviewTankRecoveryResult
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


class _Client:
    def get_fight(self, report_code, fight_id):
        return {"name": "Lokkestiiz", "startTime": 0.0, "endTime": 100000.0}


class _PerformanceService:
    client = _Client()


class _EventProvider:
    def events_for_fight(self, **kwargs):
        return ({"timestamp": 60500.0, "type": "cast"},)


class _PullService:
    def build(self, **kwargs):
        return LokkestiizPullRaidReviewEvidence(
            boundaries=(
                EncounterObservedClockBoundary(
                    encounter_id="lokkestiiz",
                    fact_key="aerial_onslaught_flight",
                    boundary="end",
                    occurrence=1,
                    time_seconds=60.0,
                    source="reviewed test landing",
                ),
            ),
            mechanic_windows=(),
            recovery_observations=(),
            unresolved=(),
        )


class _ContinuityService:
    def measure(self, **kwargs):
        return SimpleNamespace(observations=(), unresolved=("No DPS actors were supplied for ground-continuity analysis.",))


class _TankRecoveryService:
    def __init__(self):
        self.calls = []

    def measure(self, **kwargs):
        self.calls.append(kwargs)
        actor = next(actor for actor in kwargs["actors"] if actor.role == "Tank")
        signal = tuple(kwargs["signals"])[0]
        observation = RaidReviewLandingRecoveryObservation(
            report_code=kwargs["report_code"],
            fight_id=kwargs["fight_id"],
            occurrence=1,
            actor_id=actor.actor_id,
            actor_label=actor.actor_label,
            role="Tank",
            member_key=actor.member_key,
            landing_seconds=60.0,
            recovery_seconds=60.8,
            delay_seconds=0.8,
            signal_semantic_key=signal.semantic_key,
            signal_label=signal.label,
            evidence_ability_name="Pierce Armor",
        )
        from services.performance_raid_review_landing_recovery_completion_analysis_service import RaidReviewRecoveryOpportunity
        opportunity = RaidReviewRecoveryOpportunity(
            report_code=kwargs["report_code"],
            fight_id=kwargs["fight_id"],
            occurrence=1,
            actor_id=actor.actor_id,
            actor_label=actor.actor_label,
            role="Tank",
            member_key=actor.member_key,
            signal_semantic_key=signal.semantic_key,
            signal_label=signal.label,
        )
        return RaidReviewTankRecoveryResult((observation,), (opportunity,), ())


class _Coordinator:
    def __init__(self):
        self.calls = []

    def review(self, sources, **kwargs):
        self.calls.append((tuple(sources), kwargs))
        return SimpleNamespace(
            unresolved=(),
            report=SimpleNamespace(encounter_name="Lokkestiiz"),
            collection=SimpleNamespace(observations=()),
            priorities=(),
        )


def _tank_source() -> RaidReviewSource:
    return RaidReviewSource("A", 1, 5, "Tank One", "Tank", member_key="tank-one")


def _tank_signal(reviewed: bool = True) -> RaidReviewRecoverySignal:
    return RaidReviewRecoverySignal(
        semantic_key="boss_control_after_landing",
        label="Boss Control",
        role="Tank",
        event_types=("cast",),
        ability_names=("Pierce Armor",),
        reviewed=reviewed,
    )


def test_session_passes_reviewed_tank_recovery_into_generic_coordinator() -> None:
    tank_recovery = _TankRecoveryService()
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=_EventProvider(),
        pull_service=_PullService(),
        coordinator_service=coordinator,
        dd_ground_continuity_service=_ContinuityService(),
        tank_recovery_service=tank_recovery,
    )

    result = service.review(
        [LokkestiizRaidReviewPullRequest("A", 1, 99, (_tank_source(),))],
        tank_recovery_signals=(_tank_signal(),),
    )

    assert len(tank_recovery.calls) == 1
    assert len(result.tank_recovery_observations) == 1
    assert result.tank_recovery_observations[0].delay_seconds == 0.8
    assert len(result.landing_recovery_opportunities) == 1
    _sources, kwargs = coordinator.calls[0]
    assert kwargs["landing_recovery_observations"] == result.tank_recovery_observations
    assert kwargs["landing_recovery_opportunities"] == result.landing_recovery_opportunities


def test_session_does_not_promote_unreviewed_tank_signal() -> None:
    tank_recovery = _TankRecoveryService()
    coordinator = _Coordinator()
    service = PerformanceRaidReviewLokkestiizSessionService(
        _PerformanceService(),
        event_provider=_EventProvider(),
        pull_service=_PullService(),
        coordinator_service=coordinator,
        dd_ground_continuity_service=_ContinuityService(),
        tank_recovery_service=tank_recovery,
    )

    result = service.review(
        [LokkestiizRaidReviewPullRequest("A", 1, 99, (_tank_source(),))],
        tank_recovery_signals=(_tank_signal(reviewed=False),),
    )

    assert tank_recovery.calls == []
    assert result.tank_recovery_observations == ()
    assert result.landing_recovery_opportunities == ()
