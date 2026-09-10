from services.performance_raid_review_healer_effect_coverage_analysis_service import (
    PerformanceRaidReviewHealerEffectCoverageAnalysisService,
)
from services.performance_raid_review_healer_effect_coverage_service import (
    RaidReviewHealerEffectCoverageObservation,
)
from services.performance_raid_review_service import RaidReviewObservation


def _raid(fight_id: int, *, kill: bool, actor_id: int = 11, report_code: str = "A") -> RaidReviewObservation:
    return RaidReviewObservation(
        report_code=report_code,
        fight_id=fight_id,
        fight_name="Lokkestiiz",
        kill=kill,
        actor_id=actor_id,
        actor_label="Healer One",
        role="Healer",
        fight_duration_seconds=120.0,
        member_key="healer-one",
    )


def _coverage(
    fight_id: int,
    *,
    covered: bool,
    actor_id: int | None = 11,
    report_code: str = "A",
) -> RaidReviewHealerEffectCoverageObservation:
    return RaidReviewHealerEffectCoverageObservation(
        report_code=report_code,
        fight_id=fight_id,
        mechanic_semantic_key="ice_cage_one",
        mechanic_label="Ice Cage One",
        mechanic_start_seconds=50.0,
        requirement_semantic_key="budding_seeds_precoverage",
        requirement_label="Budding Seeds Pre-Coverage",
        source_actor_id=actor_id,
        covered=covered,
        active_target_count=1 if covered else 0,
        active_effect_names=(("Budding Seeds",) if covered else ()),
    )


def test_successful_pull_precoverage_pattern_becomes_medium_finding() -> None:
    raid = (
        _raid(1, kill=True),
        _raid(2, kill=True),
        _raid(3, kill=False),
        _raid(4, kill=False),
    )
    coverage = (
        _coverage(1, covered=True),
        _coverage(2, covered=True),
        _coverage(3, covered=False),
        _coverage(4, covered=False),
    )

    findings = PerformanceRaidReviewHealerEffectCoverageAnalysisService().analyze(coverage, raid)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.scope == "player"
    assert finding.subject == "Healer One"
    assert finding.role == "Healer"
    assert finding.category == "mechanic_precoverage"
    assert finding.priority == "medium"
    assert "stronger on successful pulls" in finding.title
    assert "2/2 kills" in finding.evidence
    assert "0/2 wipes" in finding.evidence
    assert "not proof" in finding.recommendation


def test_higher_wipe_coverage_is_reported_as_not_obvious_wipe_signal() -> None:
    raid = (
        _raid(1, kill=True),
        _raid(2, kill=True),
        _raid(3, kill=False),
        _raid(4, kill=False),
    )
    coverage = (
        _coverage(1, covered=False),
        _coverage(2, covered=False),
        _coverage(3, covered=True),
        _coverage(4, covered=True),
    )

    findings = PerformanceRaidReviewHealerEffectCoverageAnalysisService().analyze(coverage, raid)

    assert len(findings) == 1
    assert findings[0].priority == "note"
    assert "not the obvious wipe signal" in findings[0].title


def test_repeated_missing_precoverage_is_coaching_lead_without_causal_claim() -> None:
    raid = tuple(_raid(i, kill=False) for i in range(1, 5))
    coverage = (
        _coverage(1, covered=False),
        _coverage(2, covered=False),
        _coverage(3, covered=True),
        _coverage(4, covered=False),
    )

    findings = PerformanceRaidReviewHealerEffectCoverageAnalysisService().analyze(coverage, raid)

    assert len(findings) == 1
    assert "repeatedly missing" in findings[0].title
    assert "1/4" in findings[0].evidence
    assert "not automatic proof" in findings[0].recommendation


def test_consistent_precoverage_is_preserved_as_what_is_working() -> None:
    raid = tuple(_raid(i, kill=(i % 2 == 0)) for i in range(1, 6))
    coverage = tuple(_coverage(i, covered=True) for i in range(1, 6))

    findings = PerformanceRaidReviewHealerEffectCoverageAnalysisService().analyze(coverage, raid)

    assert len(findings) == 1
    assert findings[0].priority == "note"
    assert "consistently in place" in findings[0].title
    assert "5/5" in findings[0].evidence


def test_unowned_or_wrong_report_actor_is_not_reconstructed_by_numeric_id() -> None:
    raid = (
        _raid(1, kill=True, actor_id=11, report_code="A"),
        _raid(1, kill=False, actor_id=11, report_code="B"),
        _raid(2, kill=False, actor_id=11, report_code="B"),
    )
    coverage = (
        _coverage(1, covered=False, actor_id=None, report_code="A"),
        _coverage(1, covered=True, actor_id=11, report_code="C"),
        _coverage(2, covered=True, actor_id=11, report_code="C"),
    )

    findings = PerformanceRaidReviewHealerEffectCoverageAnalysisService().analyze(coverage, raid)

    assert findings == ()
