from services.performance_raid_review_dd_ground_continuity_analysis_service import (
    PerformanceRaidReviewDDGroundContinuityAnalysisService,
)
from services.performance_raid_review_dd_ground_continuity_service import (
    RaidReviewDDGroundContinuityObservation,
)
from services.performance_raid_review_landing_recovery_analysis_service import RaidReviewPullOutcome


def _obs(fight_id, longest, *, gaps=4, long_gaps=1, member_key="dd-one", report="A"):
    return RaidReviewDDGroundContinuityObservation(
        report_code=report,
        fight_id=fight_id,
        actor_id=7,
        actor_label="DD One",
        member_key=member_key,
        damage_event_count=gaps + 1,
        measured_gap_count=gaps,
        inactivity_gap_count=long_gaps,
        total_inactivity_seconds=longest * long_gaps,
        longest_inactivity_seconds=longest,
        inactivity_windows=tuple((1.0 + i * 10.0, 1.0 + i * 10.0 + longest) for i in range(long_gaps)),
        inactivity_threshold_seconds=3.0,
    )


def _outcomes():
    return (
        RaidReviewPullOutcome("A", 1, True),
        RaidReviewPullOutcome("A", 2, True),
        RaidReviewPullOutcome("A", 3, False),
        RaidReviewPullOutcome("A", 4, False),
    )


def test_weaker_boss_contact_on_wipes_creates_coaching_finding() -> None:
    findings = PerformanceRaidReviewDDGroundContinuityAnalysisService().findings(
        [_obs(1, 3.5, long_gaps=1), _obs(2, 4.0, long_gaps=1), _obs(3, 7.0, long_gaps=2), _obs(4, 8.0, long_gaps=2)],
        _outcomes(),
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.priority == "medium"
    assert finding.category == "boss_contact"
    assert finding.title == "Boss-contact continuity is weaker on wipe pulls"
    assert "kills 3.75s vs wipes 7.50s" in finding.evidence
    assert "lost boss contact" in finding.recommendation


def test_better_boss_contact_on_wipes_is_explicitly_not_the_problem() -> None:
    findings = PerformanceRaidReviewDDGroundContinuityAnalysisService().findings(
        [_obs(1, 8.0, long_gaps=2), _obs(2, 7.0, long_gaps=2), _obs(3, 4.0, long_gaps=1), _obs(4, 3.5, long_gaps=1)],
        _outcomes(),
    )

    assert len(findings) == 1
    assert findings[0].priority == "note"
    assert findings[0].title == "Boss-contact continuity is not a wipe-side weakness"


def test_small_difference_produces_no_noise() -> None:
    findings = PerformanceRaidReviewDDGroundContinuityAnalysisService().findings(
        [_obs(1, 4.0), _obs(2, 4.2), _obs(3, 4.5), _obs(4, 4.7)],
        _outcomes(),
        minimum_longest_gap_delta_seconds=1.0,
        minimum_gap_rate_delta=0.10,
    )

    assert findings == ()


def test_requires_repeated_kill_and_wipe_samples() -> None:
    findings = PerformanceRaidReviewDDGroundContinuityAnalysisService().findings(
        [_obs(1, 3.0), _obs(2, 8.0)],
        [RaidReviewPullOutcome("A", 1, True), RaidReviewPullOutcome("A", 2, False)],
    )

    assert findings == ()


def test_missing_member_key_falls_back_to_report_scoped_actor_identity() -> None:
    findings = PerformanceRaidReviewDDGroundContinuityAnalysisService().findings(
        [
            _obs(1, 3.0, member_key="", report="A"),
            _obs(2, 3.0, member_key="", report="A"),
            _obs(3, 8.0, member_key="", report="A"),
            _obs(4, 8.0, member_key="", report="A"),
            _obs(1, 9.0, member_key="", report="B"),
            _obs(2, 9.0, member_key="", report="B"),
        ],
        [
            RaidReviewPullOutcome("A", 1, True),
            RaidReviewPullOutcome("A", 2, True),
            RaidReviewPullOutcome("A", 3, False),
            RaidReviewPullOutcome("A", 4, False),
            RaidReviewPullOutcome("B", 1, True),
            RaidReviewPullOutcome("B", 2, False),
        ],
    )

    assert len(findings) == 1
    assert findings[0].subject == "DD One"
    assert "kills 3.00s vs wipes 8.00s" in findings[0].evidence
