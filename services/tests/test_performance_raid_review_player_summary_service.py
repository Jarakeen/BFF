from services.performance_raid_review_player_summary_service import (
    PerformanceRaidReviewPlayerSummaryService,
)
from services.performance_raid_review_service import RaidReviewFinding, RaidReviewObservation


def _obs(
    report: str,
    fight_id: int,
    *,
    actor_id: int,
    label: str,
    role: str,
    member_key: str,
    kill: bool,
) -> RaidReviewObservation:
    return RaidReviewObservation(
        report_code=report,
        fight_id=fight_id,
        fight_name="Lokkestiiz",
        kill=kill,
        actor_id=actor_id,
        actor_label=label,
        role=role,
        fight_duration_seconds=100.0,
        member_key=member_key,
    )


def _finding(
    *,
    subject: str,
    role: str,
    category: str,
    priority: str,
    title: str,
    confidence: str = "medium",
) -> RaidReviewFinding:
    return RaidReviewFinding(
        scope="player",
        subject=subject,
        role=role,
        category=category,
        priority=priority,
        title=title,
        evidence=f"Evidence for {title}",
        recommendation=f"Recommendation for {title}",
        confidence=confidence,
    )


def test_cross_report_rows_with_member_key_become_one_player_summary() -> None:
    observations = (
        _obs("A", 1, actor_id=7, label="DD One", role="DPS", member_key="dd-one", kill=True),
        _obs("B", 4, actor_id=21, label="DD One", role="DPS", member_key="dd-one", kill=False),
    )
    findings = (
        _finding(subject="DD One", role="DPS", category="damage_context", priority="medium", title="Output context"),
    )

    result = PerformanceRaidReviewPlayerSummaryService().summarize(observations, findings)

    assert result.unresolved == ()
    assert len(result.summaries) == 1
    summary = result.summaries[0]
    assert summary.member_key == "dd-one"
    assert summary.pull_count == 2
    assert summary.kill_count == 1
    assert summary.wipe_count == 1
    assert [item.title for item in summary.improvements] == ["Output context"]


def test_same_display_name_for_two_stable_players_stays_unresolved() -> None:
    observations = (
        _obs("A", 1, actor_id=7, label="Player", role="DPS", member_key="one", kill=False),
        _obs("B", 2, actor_id=9, label="Player", role="DPS", member_key="two", kill=False),
    )
    finding = _finding(
        subject="Player",
        role="DPS",
        category="survival",
        priority="high",
        title="Repeated deaths",
    )

    result = PerformanceRaidReviewPlayerSummaryService().summarize(observations, (finding,))

    assert len(result.summaries) == 2
    assert all(summary.improvements == () for summary in result.summaries)
    assert len(result.unresolved) == 1
    assert "Ambiguous player finding" in result.unresolved[0]


def test_same_label_across_roles_does_not_cross_assign_findings() -> None:
    observations = (
        _obs("A", 1, actor_id=5, label="Alex", role="Tank", member_key="tank-alex", kill=True),
        _obs("A", 1, actor_id=6, label="Alex", role="Healer", member_key="healer-alex", kill=True),
    )
    findings = (
        _finding(subject="Alex", role="Tank", category="tank_effect_continuity", priority="note", title="Tank coverage held"),
        _finding(subject="Alex", role="Healer", category="healer_effect_coverage", priority="medium", title="Pre-coverage weaker"),
    )

    result = PerformanceRaidReviewPlayerSummaryService().summarize(observations, findings)

    by_key = {summary.member_key: summary for summary in result.summaries}
    assert [item.title for item in by_key["tank-alex"].strengths] == ["Tank coverage held"]
    assert [item.title for item in by_key["healer-alex"].improvements] == ["Pre-coverage weaker"]


def test_limits_and_theme_deduplication_prefer_higher_ranked_finding() -> None:
    observations = (
        _obs("A", 1, actor_id=7, label="DD One", role="DPS", member_key="dd-one", kill=False),
    )
    findings = (
        _finding(subject="DD One", role="DPS", category="damage", priority="medium", title="Raw damage"),
        _finding(subject="DD One", role="DPS", category="damage_context", priority="high", title="Contextual damage", confidence="high"),
        _finding(subject="DD One", role="DPS", category="survival", priority="medium", title="Deaths"),
        _finding(subject="DD One", role="DPS", category="landing_recovery", priority="medium", title="Landing timing"),
        _finding(subject="DD One", role="DPS", category="boss_contact", priority="note", title="Boss contact okay"),
        _finding(subject="DD One", role="DPS", category="damage", priority="note", title="Raw damage okay"),
    )

    result = PerformanceRaidReviewPlayerSummaryService().summarize(
        observations,
        findings,
        improvement_limit=2,
        strength_limit=1,
    )

    summary = result.summaries[0]
    assert [item.title for item in summary.improvements] == ["Contextual damage", "Landing timing"]
    assert [item.title for item in summary.strengths] == ["Boss contact okay"]


def test_unmatched_player_finding_is_reported_without_creating_phantom_summary() -> None:
    observations = (
        _obs("A", 1, actor_id=5, label="Tank One", role="Tank", member_key="tank-one", kill=True),
    )
    finding = _finding(
        subject="Missing Healer",
        role="Healer",
        category="healer_effect_coverage",
        priority="medium",
        title="Coverage gap",
    )

    result = PerformanceRaidReviewPlayerSummaryService().summarize(observations, (finding,))

    assert len(result.summaries) == 1
    assert result.summaries[0].member_key == "tank-one"
    assert result.summaries[0].improvements == ()
    assert len(result.unresolved) == 1
    assert "Could not resolve player finding" in result.unresolved[0]
