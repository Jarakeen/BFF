from services.performance_raid_review_landing_recovery_analysis_service import (
    PerformanceRaidReviewLandingRecoveryAnalysisService,
    RaidReviewPullOutcome,
)
from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
)


def _obs(
    *,
    fight_id: int,
    delay: float,
    report_code: str = "A",
    member_key: str = "magrat",
    actor_id: int = 11,
    actor_label: str = "Magrat",
    role: str = "Healer",
    signal_key: str = "horn_reapplication",
    signal_label: str = "Aggressive Horn",
):
    return RaidReviewLandingRecoveryObservation(
        report_code=report_code,
        fight_id=fight_id,
        occurrence=1,
        actor_id=actor_id,
        actor_label=actor_label,
        role=role,
        member_key=member_key,
        landing_seconds=50.0,
        recovery_seconds=50.0 + delay,
        delay_seconds=delay,
        signal_semantic_key=signal_key,
        signal_label=signal_label,
        evidence_ability_name=signal_label,
    )


def _outcomes(*, kills=(1, 2), wipes=(3, 4), report_code="A"):
    return [
        *(RaidReviewPullOutcome(report_code, fight_id, True) for fight_id in kills),
        *(RaidReviewPullOutcome(report_code, fight_id, False) for fight_id in wipes),
    ]


def test_slower_recovery_on_wipes_creates_coaching_finding() -> None:
    findings = PerformanceRaidReviewLandingRecoveryAnalysisService().findings(
        [
            _obs(fight_id=1, delay=0.7),
            _obs(fight_id=2, delay=0.9),
            _obs(fight_id=3, delay=2.1),
            _obs(fight_id=4, delay=2.5),
        ],
        _outcomes(),
    )

    finding = findings[0]
    assert finding.subject == "Magrat"
    assert finding.category == "landing_recovery"
    assert finding.priority == "medium"
    assert finding.title == "Aggressive Horn is slower on wipe pulls"
    assert "kills 0.80s vs wipes 2.30s" in finding.evidence
    assert "movement" in finding.recommendation


def test_small_difference_does_not_create_noise() -> None:
    findings = PerformanceRaidReviewLandingRecoveryAnalysisService().findings(
        [
            _obs(fight_id=1, delay=1.0),
            _obs(fight_id=2, delay=1.1),
            _obs(fight_id=3, delay=1.3),
            _obs(fight_id=4, delay=1.4),
        ],
        _outcomes(),
    )

    assert findings == ()


def test_faster_recovery_on_wipes_is_protected_from_false_blame() -> None:
    findings = PerformanceRaidReviewLandingRecoveryAnalysisService().findings(
        [
            _obs(fight_id=1, delay=2.2),
            _obs(fight_id=2, delay=2.0),
            _obs(fight_id=3, delay=0.8),
            _obs(fight_id=4, delay=0.9),
        ],
        _outcomes(),
    )

    finding = findings[0]
    assert finding.priority == "note"
    assert finding.title == "Aggressive Horn timing is not a wipe-side weakness"
    assert "Do not prioritize speeding up" in finding.recommendation


def test_requires_repeated_kill_and_wipe_evidence() -> None:
    findings = PerformanceRaidReviewLandingRecoveryAnalysisService().findings(
        [
            _obs(fight_id=1, delay=0.5),
            _obs(fight_id=3, delay=3.0),
            _obs(fight_id=4, delay=3.2),
        ],
        _outcomes(kills=(1,), wipes=(3, 4)),
    )

    assert findings == ()


def test_missing_member_key_stays_report_scoped() -> None:
    observations = [
        _obs(report_code="A", fight_id=1, delay=0.5, member_key="", actor_id=7, actor_label="Player"),
        _obs(report_code="A", fight_id=2, delay=0.6, member_key="", actor_id=7, actor_label="Player"),
        _obs(report_code="B", fight_id=3, delay=3.0, member_key="", actor_id=7, actor_label="Player"),
        _obs(report_code="B", fight_id=4, delay=3.1, member_key="", actor_id=7, actor_label="Player"),
    ]
    outcomes = [
        RaidReviewPullOutcome("A", 1, True),
        RaidReviewPullOutcome("A", 2, True),
        RaidReviewPullOutcome("B", 3, False),
        RaidReviewPullOutcome("B", 4, False),
    ]

    findings = PerformanceRaidReviewLandingRecoveryAnalysisService().findings(observations, outcomes)

    assert findings == ()
