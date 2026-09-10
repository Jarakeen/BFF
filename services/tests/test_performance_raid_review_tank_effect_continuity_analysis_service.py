from services.performance_raid_review_landing_recovery_analysis_service import RaidReviewPullOutcome
from services.performance_raid_review_tank_effect_continuity_analysis_service import (
    PerformanceRaidReviewTankEffectContinuityAnalysisService,
)
from services.performance_raid_review_tank_effect_continuity_service import (
    RaidReviewTankEffectContinuityObservation,
)


def _row(fight_id: int, coverage: float, *, report: str = "A", member_key: str = "main-tank") -> RaidReviewTankEffectContinuityObservation:
    return RaidReviewTankEffectContinuityObservation(
        report_code=report,
        fight_id=fight_id,
        actor_id=5,
        actor_label="Main Tank",
        member_key=member_key,
        requirement_semantic_key="major_breach_assignment",
        requirement_label="Major Breach",
        eligible_seconds=100.0,
        covered_seconds=coverage,
        coverage_percent=coverage,
        active_effect_names=("Major Breach",) if coverage else (),
    )


def _outcomes() -> tuple[RaidReviewPullOutcome, ...]:
    return (
        RaidReviewPullOutcome("A", 1, True),
        RaidReviewPullOutcome("A", 2, True),
        RaidReviewPullOutcome("A", 3, False),
        RaidReviewPullOutcome("A", 4, False),
    )


def test_weaker_wipe_side_coverage_creates_medium_tank_finding() -> None:
    findings = PerformanceRaidReviewTankEffectContinuityAnalysisService().findings(
        (_row(1, 96.0), _row(2, 94.0), _row(3, 70.0), _row(4, 72.0)),
        _outcomes(),
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.role == "Tank"
    assert finding.priority == "medium"
    assert finding.category == "tank_effect_continuity"
    assert "weaker on wipe pulls" in finding.title
    assert "kills 95.0% vs wipes 71.0%" in finding.evidence


def test_stronger_wipe_side_coverage_is_note_not_blame() -> None:
    findings = PerformanceRaidReviewTankEffectContinuityAnalysisService().findings(
        (_row(1, 70.0), _row(2, 72.0), _row(3, 95.0), _row(4, 97.0)),
        _outcomes(),
    )

    assert len(findings) == 1
    assert findings[0].priority == "note"
    assert "not a wipe-side weakness" in findings[0].title


def test_small_coverage_difference_creates_no_noise() -> None:
    findings = PerformanceRaidReviewTankEffectContinuityAnalysisService().findings(
        (_row(1, 91.0), _row(2, 90.0), _row(3, 86.0), _row(4, 87.0)),
        _outcomes(),
    )

    assert findings == ()


def test_requires_repeated_kill_and_wipe_samples() -> None:
    findings = PerformanceRaidReviewTankEffectContinuityAnalysisService().findings(
        (_row(1, 95.0), _row(3, 60.0)),
        (RaidReviewPullOutcome("A", 1, True), RaidReviewPullOutcome("A", 3, False)),
    )

    assert findings == ()


def test_actor_id_fallback_does_not_link_across_reports() -> None:
    findings = PerformanceRaidReviewTankEffectContinuityAnalysisService().findings(
        (
            _row(1, 95.0, report="A", member_key=""),
            _row(2, 96.0, report="A", member_key=""),
            _row(3, 60.0, report="B", member_key=""),
            _row(4, 62.0, report="B", member_key=""),
        ),
        (
            RaidReviewPullOutcome("A", 1, True),
            RaidReviewPullOutcome("A", 2, True),
            RaidReviewPullOutcome("B", 3, False),
            RaidReviewPullOutcome("B", 4, False),
        ),
    )

    assert findings == ()
