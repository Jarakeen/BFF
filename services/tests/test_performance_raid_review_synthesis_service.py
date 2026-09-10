from services.performance_raid_review_priority_service import RaidReviewPriorityItem
from services.performance_raid_review_service import RaidReviewFinding, RaidReviewReport
from services.performance_raid_review_synthesis_service import (
    PerformanceRaidReviewSynthesisService,
)


def _finding(
    *,
    scope: str,
    subject: str,
    role: str,
    category: str,
    priority: str,
    confidence: str = "medium",
    title: str | None = None,
) -> RaidReviewFinding:
    return RaidReviewFinding(
        scope=scope,
        subject=subject,
        role=role,
        category=category,
        priority=priority,
        title=title or f"{subject} {category}",
        evidence=f"evidence {subject} {category}",
        recommendation=f"recommendation {subject} {category}",
        confidence=confidence,
    )


def _priority_item() -> RaidReviewPriorityItem:
    return RaidReviewPriorityItem(
        rank=1,
        scope="raid",
        subject="Raid",
        role="Group",
        category="death_window",
        priority="high",
        title="First deaths cluster",
        evidence="cluster evidence",
        recommendation="review the window",
        confidence="high",
    )


def test_synthesis_preserves_report_counts_and_priority_rows() -> None:
    report = RaidReviewReport(
        encounter_name="Lokkestiiz",
        pull_count=6,
        kill_count=2,
        wipe_count=4,
        findings=(),
    )
    priority = _priority_item()

    result = PerformanceRaidReviewSynthesisService().synthesize(report, (priority,))

    assert result.encounter_name == "Lokkestiiz"
    assert result.pull_count == 6
    assert result.kill_count == 2
    assert result.wipe_count == 4
    assert result.top_priorities == (priority,)


def test_note_findings_become_what_is_working_without_reinterpreting_them() -> None:
    note = _finding(
        scope="player",
        subject="DD One",
        role="DPS",
        category="damage",
        priority="note",
        confidence="high",
        title="Raw damage is not the wipe signal",
    )
    report = RaidReviewReport("Lokkestiiz", 4, 2, 2, (note,))

    result = PerformanceRaidReviewSynthesisService().synthesize(report, ())

    assert result.what_is_working == (note,)
    assert result.what_is_working[0].evidence == note.evidence
    assert result.what_is_working[0].recommendation == note.recommendation


def test_working_notes_dedupe_overlapping_subject_theme() -> None:
    damage = _finding(
        scope="player",
        subject="DD One",
        role="DPS",
        category="damage",
        priority="note",
        confidence="high",
    )
    contact = _finding(
        scope="player",
        subject="DD One",
        role="DPS",
        category="boss_contact",
        priority="note",
        confidence="medium",
    )
    healer = _finding(
        scope="player",
        subject="Healer One",
        role="Healer",
        category="coverage",
        priority="note",
    )
    report = RaidReviewReport("Lokkestiiz", 4, 2, 2, (contact, healer, damage))

    result = PerformanceRaidReviewSynthesisService().synthesize(report, ())

    assert len(result.what_is_working) == 2
    assert any(row.subject == "DD One" for row in result.what_is_working)
    assert any(row.subject == "Healer One" for row in result.what_is_working)


def test_role_focus_counts_actionable_findings_and_categories() -> None:
    findings = (
        _finding(scope="raid", subject="Raid", role="Group", category="death_window", priority="high"),
        _finding(scope="player", subject="Tank One", role="Tank", category="tank_effect_continuity", priority="medium"),
        _finding(scope="player", subject="Tank One", role="Tank", category="landing_recovery", priority="note"),
        _finding(scope="player", subject="DD One", role="DPS", category="damage_context", priority="medium"),
        _finding(scope="player", subject="Healer One", role="Healer", category="coverage", priority="note"),
    )
    report = RaidReviewReport("Lokkestiiz", 4, 2, 2, findings)

    result = PerformanceRaidReviewSynthesisService().synthesize(report, ())
    by_role = {row.role: row for row in result.role_focus}

    assert by_role["Group"].actionable_count == 1
    assert by_role["Tank"].actionable_count == 1
    assert by_role["Tank"].note_count == 1
    assert by_role["Tank"].categories == ("landing_recovery", "tank_effect_continuity")
    assert by_role["DPS"].categories == ("damage_context",)
    assert by_role["Healer"].note_count == 1


def test_working_limit_can_disable_or_bound_working_section() -> None:
    notes = tuple(
        _finding(
            scope="player",
            subject=f"Player {index}",
            role="DPS",
            category="damage",
            priority="note",
        )
        for index in range(4)
    )
    report = RaidReviewReport("Lokkestiiz", 4, 2, 2, notes)
    service = PerformanceRaidReviewSynthesisService()

    assert service.synthesize(report, (), working_limit=0).what_is_working == ()
    assert len(service.synthesize(report, (), working_limit=2).what_is_working) == 2
