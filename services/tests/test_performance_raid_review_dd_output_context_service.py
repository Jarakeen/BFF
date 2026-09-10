from services.performance_raid_review_dd_ground_continuity_service import (
    RaidReviewDDGroundContinuityObservation,
)
from services.performance_raid_review_dd_output_context_service import (
    PerformanceRaidReviewDDOutputContextService,
)
from services.performance_raid_review_landing_recovery_completion_analysis_service import (
    RaidReviewRecoveryOpportunity,
)
from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
)
from services.performance_raid_review_service import RaidReviewObservation


def _obs(fight_id: int, *, kill: bool, output: float, deaths: int = 0, report: str = "A", actor_id: int = 7, member_key: str = "dd-one") -> RaidReviewObservation:
    return RaidReviewObservation(
        report_code=report,
        fight_id=fight_id,
        fight_name="Lokkestiiz",
        kill=kill,
        actor_id=actor_id,
        actor_label="DD One",
        role="DPS",
        fight_duration_seconds=100.0,
        member_key=member_key,
        output_total=output * 100.0,
        output_per_second=output,
        boss_active_seconds=100.0,
        death_count=deaths,
    )


def _continuity(fight_id: int, *, longest: float, gap_count: int, measured: int = 10, report: str = "A", actor_id: int = 7, member_key: str = "dd-one") -> RaidReviewDDGroundContinuityObservation:
    return RaidReviewDDGroundContinuityObservation(
        report_code=report,
        fight_id=fight_id,
        actor_id=actor_id,
        actor_label="DD One",
        member_key=member_key,
        damage_event_count=20,
        measured_gap_count=measured,
        inactivity_gap_count=gap_count,
        total_inactivity_seconds=longest,
        longest_inactivity_seconds=longest,
        inactivity_windows=((10.0, 10.0 + longest),) if longest else (),
        inactivity_threshold_seconds=3.0,
    )


def _opportunity(fight_id: int, occurrence: int, *, report: str = "A", actor_id: int = 7, member_key: str = "dd-one") -> RaidReviewRecoveryOpportunity:
    return RaidReviewRecoveryOpportunity(
        report_code=report,
        fight_id=fight_id,
        occurrence=occurrence,
        actor_id=actor_id,
        actor_label="DD One",
        role="DPS",
        member_key=member_key,
        signal_semantic_key="boss_damage_reacquisition_after_landing",
        signal_label="Boss Damage Reacquisition",
    )


def _recovery(fight_id: int, occurrence: int, *, report: str = "A", actor_id: int = 7, member_key: str = "dd-one") -> RaidReviewLandingRecoveryObservation:
    return RaidReviewLandingRecoveryObservation(
        report_code=report,
        fight_id=fight_id,
        occurrence=occurrence,
        actor_id=actor_id,
        actor_label="DD One",
        role="DPS",
        member_key=member_key,
        landing_seconds=50.0,
        recovery_seconds=51.0,
        delay_seconds=1.0,
        signal_semantic_key="boss_damage_reacquisition_after_landing",
        signal_label="Boss Damage Reacquisition",
    )


def _base_rows():
    return [
        _obs(1, kill=True, output=100_000),
        _obs(2, kill=True, output=102_000),
        _obs(3, kill=False, output=70_000),
        _obs(4, kill=False, output=72_000),
    ]


def test_lower_output_with_death_affected_wipes_gets_context_finding() -> None:
    rows = [
        _obs(1, kill=True, output=100_000),
        _obs(2, kill=True, output=102_000),
        _obs(3, kill=False, output=70_000, deaths=1),
        _obs(4, kill=False, output=72_000, deaths=1),
    ]

    findings = PerformanceRaidReviewDDOutputContextService().findings(rows)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.category == "damage_context"
    assert "Deaths were recorded in 2/2" in finding.evidence
    assert "death-affected pulls" in finding.recommendation


def test_lower_output_with_weaker_boss_contact_gets_context_finding() -> None:
    continuity = [
        _continuity(1, longest=1.0, gap_count=0),
        _continuity(2, longest=1.2, gap_count=0),
        _continuity(3, longest=4.5, gap_count=4),
        _continuity(4, longest=5.0, gap_count=5),
    ]

    findings = PerformanceRaidReviewDDOutputContextService().findings(
        _base_rows(), continuity_observations=continuity
    )

    assert len(findings) == 1
    assert "Mechanic-adjusted boss contact was weaker on wipes" in findings[0].evidence
    assert "weaker boss-contact continuity" in findings[0].recommendation


def test_lower_output_with_missed_reacquisition_gets_context_finding() -> None:
    opportunities = [
        _opportunity(1, 1), _opportunity(1, 2),
        _opportunity(2, 1), _opportunity(2, 2),
        _opportunity(3, 1), _opportunity(3, 2),
        _opportunity(4, 1), _opportunity(4, 2),
    ]
    recoveries = [
        _recovery(1, 1), _recovery(1, 2),
        _recovery(2, 1), _recovery(2, 2),
        _recovery(3, 1),
        _recovery(4, 1),
    ]

    findings = PerformanceRaidReviewDDOutputContextService().findings(
        _base_rows(),
        recovery_opportunities=opportunities,
        recovery_observations=recoveries,
    )

    assert len(findings) == 1
    assert "4/4 kill opportunities vs 2/4 wipe opportunities" in findings[0].evidence
    assert "missed post-landing reacquisition" in findings[0].recommendation


def test_lower_output_without_supporting_context_adds_no_duplicate_noise() -> None:
    findings = PerformanceRaidReviewDDOutputContextService().findings(_base_rows())
    assert findings == ()


def test_report_scoped_actor_ids_do_not_link_without_member_key() -> None:
    rows = [
        _obs(1, kill=True, output=100_000, report="A", actor_id=7, member_key=""),
        _obs(2, kill=True, output=102_000, report="A", actor_id=7, member_key=""),
        _obs(1, kill=False, output=70_000, deaths=1, report="B", actor_id=7, member_key=""),
        _obs(2, kill=False, output=72_000, deaths=1, report="B", actor_id=7, member_key=""),
    ]

    findings = PerformanceRaidReviewDDOutputContextService().findings(rows)
    assert findings == ()
