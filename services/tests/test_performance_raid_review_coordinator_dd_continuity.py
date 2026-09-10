from types import SimpleNamespace

from services.performance_raid_review_coordinator_service import PerformanceRaidReviewCoordinatorService
from services.performance_raid_review_dd_ground_continuity_service import RaidReviewDDGroundContinuityObservation
from services.performance_raid_review_observation_service import RaidReviewCollectionResult
from services.performance_raid_review_service import RaidReviewObservation


class _Performance:
    def __init__(self):
        self.client = SimpleNamespace()


class _ObservationService:
    def collect(self, sources):
        return RaidReviewCollectionResult(
            observations=(
                _review(1, True),
                _review(2, True),
                _review(3, False),
                _review(4, False),
            ),
            unresolved=(),
        )


def _review(fight_id: int, kill: bool) -> RaidReviewObservation:
    return RaidReviewObservation(
        report_code="A",
        fight_id=fight_id,
        fight_name="Lokkestiiz",
        kill=kill,
        actor_id=7,
        actor_label="DD One",
        role="DPS",
        fight_duration_seconds=120.0,
        member_key="dd-one",
        output_total=10_000_000.0,
        output_per_second=100_000.0,
        boss_active_seconds=100.0,
    )


def _continuity(fight_id: int, longest: float, long_gaps: int) -> RaidReviewDDGroundContinuityObservation:
    return RaidReviewDDGroundContinuityObservation(
        report_code="A",
        fight_id=fight_id,
        actor_id=7,
        actor_label="DD One",
        member_key="dd-one",
        damage_event_count=5,
        measured_gap_count=4,
        inactivity_gap_count=long_gaps,
        total_inactivity_seconds=longest * long_gaps,
        longest_inactivity_seconds=longest,
        inactivity_windows=(),
        inactivity_threshold_seconds=3.0,
    )


def test_coordinator_promotes_weaker_wipe_side_dd_boss_continuity() -> None:
    service = PerformanceRaidReviewCoordinatorService(
        _Performance(),
        observation_service=_ObservationService(),
    )

    result = service.review(
        (),
        encounter_name="Lokkestiiz",
        dd_ground_continuity_observations=(
            _continuity(1, 3.5, 1),
            _continuity(2, 4.0, 1),
            _continuity(3, 7.0, 2),
            _continuity(4, 8.0, 2),
        ),
    )

    finding = next(item for item in result.report.findings if item.category == "boss_contact")
    assert finding.subject == "DD One"
    assert finding.priority == "medium"
    assert finding.title == "Boss-contact continuity is weaker on wipe pulls"
    assert "kills 3.75s vs wipes 7.50s" in finding.evidence
