from types import SimpleNamespace

from services.performance_raid_review_coordinator_service import (
    PerformanceRaidReviewCoordinatorService,
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


def test_coordinator_exposes_player_summary_from_final_findings() -> None:
    observations = (
        _obs(1, kill=True, output=100_000),
        _obs(2, kill=True, output=102_000),
        _obs(3, kill=False, output=70_000),
        _obs(4, kill=False, output=72_000),
    )
    service = PerformanceRaidReviewCoordinatorService(
        _PerformanceService(),
        observation_service=_ObservationService(observations),
        event_provider=SimpleNamespace(),
    )

    result = service.review((), encounter_name="Lokkestiiz")

    assert len(result.player_summaries) == 1
    summary = result.player_summaries[0]
    assert summary.member_key == "dd-one"
    assert summary.actor_label == "DD One"
    assert summary.role == "DPS"
    assert summary.pull_count == 4
    assert summary.kill_count == 2
    assert summary.wipe_count == 2
    assert any(item.category == "damage" for item in summary.improvements)
    assert result.player_summary_unresolved == ()
    assert result.unresolved == ()
