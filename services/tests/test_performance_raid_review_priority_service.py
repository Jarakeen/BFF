from services.performance_raid_review_priority_service import (
    PerformanceRaidReviewPriorityService,
)
from services.performance_raid_review_service import RaidReviewFinding


def _finding(
    *,
    subject: str,
    category: str,
    priority: str = "medium",
    confidence: str = "medium",
    scope: str = "player",
    title: str | None = None,
) -> RaidReviewFinding:
    return RaidReviewFinding(
        scope=scope,
        subject=subject,
        role="DPS" if subject != "Raid" else "Group",
        category=category,
        priority=priority,
        title=title or f"{subject} {category}",
        evidence=f"evidence for {subject} {category}",
        recommendation=f"recommendation for {subject} {category}",
        confidence=confidence,
    )


def test_rank_prefers_high_priority_then_confidence_deterministically() -> None:
    service = PerformanceRaidReviewPriorityService()
    result = service.rank(
        [
            _finding(subject="DD Two", category="boss_contact", priority="medium", confidence="high"),
            _finding(subject="DD One", category="survival", priority="high", confidence="medium"),
            _finding(subject="Raid", category="death_window", priority="high", confidence="high", scope="raid"),
        ]
    )

    assert [item.rank for item in result] == [1, 2, 3]
    assert [item.subject for item in result] == ["Raid", "DD One", "DD Two"]


def test_contextual_dd_finding_replaces_narrower_raw_damage_in_shortlist() -> None:
    service = PerformanceRaidReviewPriorityService()
    result = service.rank(
        [
            _finding(subject="DD One", category="damage", title="Damage is stronger on successful pulls"),
            _finding(subject="DD One", category="output_context", title="Lower wipe-side damage has measured context"),
            _finding(subject="Healer One", category="sustain"),
        ]
    )

    dd_rows = [item for item in result if item.subject == "DD One"]
    assert len(dd_rows) == 1
    assert dd_rows[0].category == "output_context"
    assert dd_rows[0].title == "Lower wipe-side damage has measured context"


def test_notes_are_excluded_by_default_and_can_be_included_explicitly() -> None:
    service = PerformanceRaidReviewPriorityService()
    note = _finding(subject="DD One", category="boss_contact", priority="note")

    assert service.rank([note]) == ()
    included = service.rank([note], include_notes=True)
    assert len(included) == 1
    assert included[0].priority == "note"


def test_limit_is_respected_and_zero_limit_returns_empty() -> None:
    service = PerformanceRaidReviewPriorityService()
    findings = [
        _finding(subject="One", category="survival", priority="high"),
        _finding(subject="Two", category="sustain", priority="medium"),
        _finding(subject="Three", category="uptime", priority="medium"),
        _finding(subject="Four", category="boss_contact", priority="medium"),
    ]

    assert len(service.rank(findings, limit=2)) == 2
    assert service.rank(findings, limit=0) == ()


def test_priority_items_preserve_original_evidence_and_recommendation() -> None:
    service = PerformanceRaidReviewPriorityService()
    finding = RaidReviewFinding(
        scope="player",
        subject="DD One",
        role="DPS",
        category="output_context",
        priority="medium",
        title="Lower wipe-side damage has measured context",
        evidence="Deaths and weaker boss contact were both observed on the lower-output wipes.",
        recommendation="Inspect those windows before changing the base rotation.",
        confidence="high",
    )

    item = service.rank([finding])[0]
    assert item.evidence == finding.evidence
    assert item.recommendation == finding.recommendation
    assert item.title == finding.title
    assert item.confidence == finding.confidence
