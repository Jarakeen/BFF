from services.performance_raid_review_landing_recovery_analysis_service import RaidReviewPullOutcome
from services.performance_raid_review_landing_recovery_completion_analysis_service import (
    PerformanceRaidReviewLandingRecoveryCompletionAnalysisService,
    RaidReviewRecoveryOpportunity,
)
from services.performance_raid_review_landing_recovery_service import RaidReviewLandingRecoveryObservation


def _chance(fight_id: int, *, member_key="dd-one") -> RaidReviewRecoveryOpportunity:
    return RaidReviewRecoveryOpportunity(
        report_code="A",
        fight_id=fight_id,
        occurrence=1,
        actor_id=7,
        actor_label="DD One",
        role="DPS",
        member_key=member_key,
        signal_semantic_key="boss_damage_reacquisition_after_landing",
        signal_label="Boss Damage Reacquisition",
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


def _outcomes():
    return (
        RaidReviewPullOutcome("A", 1, True),
        RaidReviewPullOutcome("A", 2, True),
        RaidReviewPullOutcome("A", 3, False),
        RaidReviewPullOutcome("A", 4, False),
    )


def test_missing_reacquisition_on_wipes_becomes_actionable_finding() -> None:
    findings = PerformanceRaidReviewLandingRecoveryCompletionAnalysisService().findings(
        [_chance(1), _chance(2), _chance(3), _chance(4)],
        [_done(1), _done(2)],
        _outcomes(),
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.priority == "medium"
    assert finding.category == "landing_recovery_completion"
    assert "missed more often on wipe pulls" in finding.title
    assert "2/2 kill opportunities" in finding.evidence
    assert "0/2 wipe opportunities" in finding.evidence


def test_equal_completion_rates_do_not_create_noise() -> None:
    findings = PerformanceRaidReviewLandingRecoveryCompletionAnalysisService().findings(
        [_chance(1), _chance(2), _chance(3), _chance(4)],
        [_done(1), _done(3)],
        _outcomes(),
    )
    assert findings == ()


def test_better_completion_on_wipes_is_note_not_fault() -> None:
    findings = PerformanceRaidReviewLandingRecoveryCompletionAnalysisService().findings(
        [_chance(1), _chance(2), _chance(3), _chance(4)],
        [_done(1), _done(3), _done(4)],
        _outcomes(),
    )

    assert len(findings) == 1
    assert findings[0].priority == "note"
    assert "not a wipe-side weakness" in findings[0].title


def test_requires_repeated_opportunities_on_both_outcomes() -> None:
    findings = PerformanceRaidReviewLandingRecoveryCompletionAnalysisService().findings(
        [_chance(1), _chance(3), _chance(4)],
        [_done(1)],
        _outcomes(),
    )
    assert findings == ()


def test_missing_member_key_falls_back_to_report_scoped_actor_identity() -> None:
    chances = [
        _chance(1, member_key=""),
        _chance(2, member_key=""),
        _chance(3, member_key=""),
        _chance(4, member_key=""),
    ]
    findings = PerformanceRaidReviewLandingRecoveryCompletionAnalysisService().findings(
        chances,
        [_done(1), _done(2)],
        _outcomes(),
    )
    assert len(findings) == 1
