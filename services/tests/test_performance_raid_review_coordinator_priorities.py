from types import SimpleNamespace

from services.performance_raid_review_coordinator_service import (
    PerformanceRaidReviewCoordinatorService,
)
from services.performance_raid_review_dd_ground_continuity_service import (
    RaidReviewDDGroundContinuityObservation,
)
from services.performance_raid_review_observation_service import RaidReviewCollectionResult
from services.performance_raid_review_service import RaidReviewObservation


class _ObservationService:
    def __init__(self, observations):
        self.observations = tuple(observations)

    def collect(self, sources):
        return RaidReviewCollectionResult(observations=self.observations, unresolved=())


class _PerformanceService:
    client = SimpleNamespace()


def _obs(fight_id: int, *, kill: bool, output: float) -> RaidReviewObservation:
    return RaidReviewObservation(
        report_code="A",
        fight_id=fight_id,
        fight_name="Lokkestiiz",
        kill=kill,
        actor_id=7,
        actor_label="DD One",
        role="DPS",
        fight_duration_seconds=100.0,
        member_key="dd-one",
        output_total=output * 100.0,
        output_per_second=output,
        boss_active_seconds=100.0,
    )


def _continuity(fight_id: int, *, longest: float, long_gaps: int) -> RaidReviewDDGroundContinuityObservation:
    return RaidReviewDDGroundContinuityObservation(
        report_code="A",
        fight_id=fight_id,
        actor_id=7,
        actor_label="DD One",
        member_key="dd-one",
        damage_event_count=20,
        measured_gap_count=10,
        inactivity_gap_count=long_gaps,
        total_inactivity_seconds=longest,
        longest_inactivity_seconds=longest,
        inactivity_windows=((10.0, 10.0 + longest),) if longest else (),
        inactivity_threshold_seconds=3.0,
    )


def test_coordinator_exposes_contextual_top_priority_without_removing_raw_findings() -> None:
    observations = (
        _obs(1, kill=True, output=100_000),
        _obs(2, kill=True, output=102_000),
        _obs(3, kill=False, output=70_000),
        _obs(4, kill=False, output=72_000),
    )
    continuity = (
        _continuity(1, longest=1.0, long_gaps=0),
        _continuity(2, longest=1.2, long_gaps=0),
        _continuity(3, longest=4.5, long_gaps=4),
        _continuity(4, longest=5.0, long_gaps=5),
    )
    service = PerformanceRaidReviewCoordinatorService(
        _PerformanceService(),
        observation_service=_ObservationService(observations),
        event_provider=SimpleNamespace(),
    )

    result = service.review(
        (),
        encounter_name="Lokkestiiz",
        dd_ground_continuity_observations=continuity,
    )

    categories = {item.category for item in result.report.findings}
    assert "damage" in categories
    assert "damage_context" in categories
    assert "boss_contact" in categories

    assert result.priorities
    assert result.priorities[0].rank == 1
    assert result.priorities[0].subject == "DD One"
    assert result.priorities[0].category == "damage_context"
    assert result.priorities[0].title == "Lower wipe-side damage has measured context"
    assert not any(item.category == "damage" for item in result.priorities)

    assert result.synthesis is not None
    assert result.synthesis.encounter_name == "Lokkestiiz"
    assert result.synthesis.pull_count == 4
    assert result.synthesis.kill_count == 2
    assert result.synthesis.wipe_count == 2
    assert result.synthesis.top_priorities == result.priorities
    dps_focus = next(item for item in result.synthesis.role_focus if item.role == "DPS")
    assert dps_focus.actionable_count >= 2
    assert "damage_context" in dps_focus.categories
    assert "boss_contact" in dps_focus.categories
