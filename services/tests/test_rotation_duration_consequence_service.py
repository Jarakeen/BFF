from minmax.rotation_recast import RotationRecastAnalysis, RotationRecastSummary
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_duration_consequence_service import RotationDurationConsequenceService


def _projection(*summaries: RotationRecastSummary) -> RotationDurationProjection:
    return RotationDurationProjection(
        analysis=RotationRecastAnalysis(windows=(), summaries=tuple(summaries)),
        rules=(),
        unresolved=(),
    )


def _summary(
    name: str,
    *,
    bar: str,
    casts: int,
    active: float,
    uptime: float,
    gap: float,
    premature: float = 0.0,
) -> RotationRecastSummary:
    return RotationRecastSummary(
        skill_name=name,
        bar=bar,
        duration_seconds=20.0,
        cast_count=casts,
        active_seconds=active,
        uptime_fraction=uptime,
        total_gap_seconds=gap,
        total_premature_seconds=premature,
    )


def test_reports_named_duration_changes_without_inventing_acceptability() -> None:
    baseline = _projection(
        _summary(
            "Expansive Frost Cloak",
            bar="back",
            casts=3,
            active=58.0,
            uptime=58.0 / 60.0,
            gap=2.0,
        ),
        _summary(
            "Winter's Revenge",
            bar="back",
            casts=3,
            active=54.0,
            uptime=0.9,
            gap=6.0,
        ),
    )
    candidate = _projection(
        _summary(
            "Expansive Frost Cloak",
            bar="back",
            casts=3,
            active=55.0,
            uptime=55.0 / 60.0,
            gap=5.0,
        ),
        _summary(
            "Winter's Revenge",
            bar="back",
            casts=3,
            active=52.0,
            uptime=52.0 / 60.0,
            gap=8.0,
        ),
    )

    result = RotationDurationConsequenceService().compare(
        baseline=baseline,
        candidate=candidate,
        skills=(
            ("Expansive Frost Cloak", "back"),
            ("Winter's Revenge", "back"),
        ),
    )

    assert len(result) == 2
    frost, winter = result
    assert frost.cast_count_delta == 0
    assert frost.active_seconds_delta == -3.0
    assert frost.total_gap_seconds_delta == 3.0
    assert frost.uptime_fraction_delta == (55.0 / 60.0) - (58.0 / 60.0)
    assert frost.unresolved == ()
    assert winter.active_seconds_delta == -2.0
    assert winter.total_gap_seconds_delta == 2.0


def test_missing_duration_evidence_stays_explicit() -> None:
    baseline = _projection(
        _summary(
            "Expansive Frost Cloak",
            bar="back",
            casts=3,
            active=58.0,
            uptime=58.0 / 60.0,
            gap=2.0,
        )
    )
    candidate = _projection()

    (result,) = RotationDurationConsequenceService().compare(
        baseline=baseline,
        candidate=candidate,
        skills=(("Expansive Frost Cloak", "back"),),
    )

    assert result.candidate is None
    assert result.active_seconds_delta is None
    assert result.unresolved


def test_duplicate_skill_requests_are_deduped() -> None:
    summary = _summary(
        "Expansive Frost Cloak",
        bar="back",
        casts=3,
        active=58.0,
        uptime=58.0 / 60.0,
        gap=2.0,
    )

    result = RotationDurationConsequenceService().compare(
        baseline=_projection(summary),
        candidate=_projection(summary),
        skills=(
            ("Expansive Frost Cloak", "back"),
            ("Expansive Frost Cloak", "back"),
        ),
    )

    assert len(result) == 1
