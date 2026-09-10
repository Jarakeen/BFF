from types import SimpleNamespace

from services.performance_raid_review_coordinator_service import PerformanceRaidReviewCoordinatorService
from services.performance_raid_review_observation_service import RaidReviewCollectionResult
from services.performance_raid_review_service import RaidReviewObservation
from services.performance_raid_review_tank_effect_continuity_service import RaidReviewTankEffectContinuityObservation


class _ObservationService:
    def __init__(self, observations):
        self.observations = tuple(observations)

    def collect(self, sources):
        return RaidReviewCollectionResult(observations=self.observations, unresolved=())


class _PerformanceService:
    client = SimpleNamespace()


def _obs(fight_id: int, *, kill: bool) -> RaidReviewObservation:
    return RaidReviewObservation(
        report_code="A",
        fight_id=fight_id,
        fight_name="Lokkestiiz",
        kill=kill,
        actor_id=5,
        actor_label="Main Tank",
        role="Tank",
        fight_duration_seconds=100.0,
        member_key="main-tank",
    )


def _coverage(fight_id: int, percent: float) -> RaidReviewTankEffectContinuityObservation:
    return RaidReviewTankEffectContinuityObservation(
        report_code="A",
        fight_id=fight_id,
        actor_id=5,
        actor_label="Main Tank",
        member_key="main-tank",
        requirement_semantic_key="major_breach_assignment",
        requirement_label="Major Breach",
        eligible_seconds=100.0,
        covered_seconds=percent,
        coverage_percent=percent,
        active_effect_names=("Major Breach",),
    )


def test_coordinator_promotes_weaker_tank_effect_coverage_into_report_and_priorities() -> None:
    observations = (
        _obs(1, kill=True),
        _obs(2, kill=True),
        _obs(3, kill=False),
        _obs(4, kill=False),
    )
    continuity = (
        _coverage(1, 96.0),
        _coverage(2, 94.0),
        _coverage(3, 70.0),
        _coverage(4, 72.0),
    )
    service = PerformanceRaidReviewCoordinatorService(
        _PerformanceService(),
        observation_service=_ObservationService(observations),
        event_provider=SimpleNamespace(),
    )

    result = service.review(
        (),
        encounter_name="Lokkestiiz",
        tank_effect_continuity_observations=continuity,
    )

    finding = next(item for item in result.report.findings if item.category == "tank_effect_continuity")
    assert finding.subject == "Main Tank"
    assert finding.priority == "medium"
    assert "kills 95.0% vs wipes 71.0%" in finding.evidence
    assert any(item.category == "tank_effect_continuity" for item in result.priorities)
