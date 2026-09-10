from types import SimpleNamespace

from services.performance_raid_review_coordinator_service import PerformanceRaidReviewCoordinatorService
from services.performance_raid_review_landing_recovery_completion_analysis_service import RaidReviewRecoveryOpportunity
from services.performance_raid_review_landing_recovery_service import RaidReviewLandingRecoveryObservation
from services.performance_raid_review_observation_service import RaidReviewCollectionResult
from services.performance_raid_review_service import RaidReviewObservation


class _PerformanceService:
    client = SimpleNamespace()


class _ObservationService:
    def collect(self, sources):
        return RaidReviewCollectionResult(
            observations=(
                _row(1, True),
                _row(2, True),
                _row(3, False),
                _row(4, False),
            ),
            unresolved=(),
        )


def _row(fight_id: int, kill: bool) -> RaidReviewObservation:
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
    )


def _chance(fight_id: int) -> RaidReviewRecoveryOpportunity:
    return RaidReviewRecoveryOpportunity(
        "A",
        fight_id,
        1,
        7,
        "DD One",
        "DPS",
        "dd-one",
        "boss_damage_reacquisition_after_landing",
        "Boss Damage Reacquisition",
    )


def _done(fight_id: int) -> RaidReviewLandingRecoveryObservation:
    return RaidReviewLandingRecoveryObservation(
        report_code="A",
        fight_id=fight_id,
        occurrence=1,
        actor_id=7,
        actor_label="DD One",
        role="DPS",
        member_key="dd-one",
        landing_seconds=70.0,
        recovery_seconds=71.0,
        delay_seconds=1.0,
        signal_semantic_key="boss_damage_reacquisition_after_landing",
        signal_label="Boss Damage Reacquisition",
    )


def test_coordinator_promotes_missed_dd_reacquisition_into_unified_report() -> None:
    service = PerformanceRaidReviewCoordinatorService(
        _PerformanceService(),
        observation_service=_ObservationService(),
        event_provider=SimpleNamespace(resolve=lambda source, fight: None),
    )

    result = service.review(
        (),
        encounter_name="Lokkestiiz",
        landing_recovery_observations=(_done(1), _done(2)),
        landing_recovery_opportunities=(_chance(1), _chance(2), _chance(3), _chance(4)),
    )

    finding = next(
        row for row in result.report.findings
        if row.category == "landing_recovery_completion"
    )
    assert finding.subject == "DD One"
    assert finding.priority == "medium"
    assert "missed more often on wipe pulls" in finding.title
    assert "2/2 kill opportunities" in finding.evidence
    assert "0/2 wipe opportunities" in finding.evidence
