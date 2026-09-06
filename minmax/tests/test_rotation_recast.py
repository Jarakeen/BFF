from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastAnalyzer, RotationRecastRule


def _plan(*times: float, duration: float = 30.0) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=duration,
        actions=tuple(
            RotationAction(
                time_seconds=time,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            )
            for time in times
        ),
    )


def test_recast_analysis_reports_premature_refresh_and_union_uptime() -> None:
    analysis = RotationRecastAnalyzer().analyze(
        _plan(0.0, 4.0, 8.0, duration=12.0),
        (RotationRecastRule("Combat Prayer", duration_seconds=10.0, bar="front"),),
    )

    summary = analysis.summaries[0]
    assert summary.cast_count == 3
    assert summary.active_seconds == 12.0
    assert summary.uptime_fraction == 1.0
    assert summary.total_gap_seconds == 0.0
    assert summary.total_premature_seconds == 12.0
    assert analysis.windows[0].premature_seconds == 6.0
    assert analysis.windows[1].premature_seconds == 6.0


def test_recast_analysis_reports_expiry_gap() -> None:
    analysis = RotationRecastAnalyzer().analyze(
        _plan(0.0, 13.0, duration=20.0),
        (RotationRecastRule("Combat Prayer", duration_seconds=10.0),),
    )

    summary = analysis.summaries[0]
    assert summary.total_gap_seconds == 3.0
    assert summary.total_premature_seconds == 0.0
    assert summary.active_seconds == 17.0
    assert summary.uptime_fraction == 0.85
    assert analysis.windows[0].gap_seconds == 3.0


def test_refresh_lead_allows_intentional_overlap_without_premature_penalty() -> None:
    analysis = RotationRecastAnalyzer().analyze(
        _plan(0.0, 9.0, duration=12.0),
        (
            RotationRecastRule(
                "Combat Prayer",
                duration_seconds=10.0,
                refresh_lead_seconds=2.0,
            ),
        ),
    )

    assert analysis.windows[0].preferred_refresh_seconds == 8.0
    assert analysis.windows[0].premature_seconds == 0.0
    assert analysis.summaries[0].total_premature_seconds == 0.0


def test_recast_rule_can_be_scoped_to_bar_and_missing_casts_remain_unresolved() -> None:
    analysis = RotationRecastAnalyzer().analyze(
        _plan(0.0, duration=10.0),
        (RotationRecastRule("Combat Prayer", duration_seconds=10.0, bar="back"),),
    )

    assert analysis.summaries == ()
    assert len(analysis.unresolved) == 1
    assert "matched no scheduled casts" in analysis.unresolved[0]


def test_recast_contract_rejects_invalid_rules_and_duplicates() -> None:
    invalid = (
        lambda: RotationRecastRule("", duration_seconds=10.0),
        lambda: RotationRecastRule("Skill", duration_seconds=0.0),
        lambda: RotationRecastRule("Skill", duration_seconds=float("inf")),
        lambda: RotationRecastRule("Skill", duration_seconds=10.0, refresh_lead_seconds=-1.0),
        lambda: RotationRecastRule("Skill", duration_seconds=10.0, refresh_lead_seconds=11.0),
        lambda: RotationRecastRule("Skill", duration_seconds=10.0, bar="side"),
    )
    for factory in invalid:
        try:
            factory()
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid recast rule to be rejected")

    rule = RotationRecastRule("Combat Prayer", duration_seconds=10.0)
    try:
        RotationRecastAnalyzer().analyze(_plan(0.0), (rule, rule))
    except ValueError as exc:
        assert "duplicate recast rule" in str(exc)
    else:
        raise AssertionError("Expected duplicate recast rules to be rejected")
