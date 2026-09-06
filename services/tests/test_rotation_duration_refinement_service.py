from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import (
    RotationRecastAnalysis,
    RotationRecastRule,
    RotationRecastSummary,
)
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_duration_refinement_service import RotationDurationRefinementService


class _FakeDurationAnalysis:
    def __init__(self, *projections: RotationDurationProjection) -> None:
        self.projections = list(projections)
        self.calls = []

    def analyze(self, plan: RotationPlan) -> RotationDurationProjection:
        self.calls.append(plan)
        if not self.projections:
            raise AssertionError("No fake duration projection remains")
        return self.projections.pop(0)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=4.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Long Buff", "front"),
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Filler", "front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, "Long Buff", "front"),
            RotationAction(3.0, 0, RotationActionKind.SKILL, "Filler", "front"),
            RotationAction(4.0, 0, RotationActionKind.SKILL, "Long Buff", "front"),
        ),
        unresolved=("baseline unresolved",),
    )


def _projection(
    *,
    rules=(),
    unresolved=(),
    uptime_fraction: float | None = None,
) -> RotationDurationProjection:
    summaries = ()
    if uptime_fraction is not None:
        summaries = (
            RotationRecastSummary(
                skill_name="Long Buff",
                bar="front",
                duration_seconds=10.0,
                cast_count=1,
                active_seconds=4.0 * uptime_fraction,
                uptime_fraction=uptime_fraction,
                total_gap_seconds=0.0,
                total_premature_seconds=0.0,
            ),
        )
    return RotationDurationProjection(
        analysis=RotationRecastAnalysis(windows=(), summaries=summaries),
        rules=tuple(rules),
        unresolved=tuple(unresolved),
    )


def test_refinement_service_uses_duration_projection_rules() -> None:
    seed_projection = _projection(
        rules=(RotationRecastRule("Long Buff", 10.0, bar="front"),)
    )
    final_projection = _projection(uptime_fraction=1.0)
    fake = _FakeDurationAnalysis(seed_projection, final_projection)
    service = RotationDurationRefinementService(duration_analysis=fake)

    result = service.refine(_plan())

    assert len(fake.calls) == 2
    assert fake.calls[0].actions != fake.calls[1].actions
    names = [
        action.name
        for action in result.plan.actions
        if action.kind is RotationActionKind.SKILL
    ]
    assert names == ["Long Buff", "Filler", "Filler", "Filler", "Filler"]
    assert result.duration_projection is final_projection


def test_refinement_service_returns_post_refinement_duration_evidence() -> None:
    seed_projection = _projection(
        rules=(RotationRecastRule("Long Buff", 2.0, bar="front"),),
        uptime_fraction=0.5,
    )
    final_projection = _projection(
        rules=(RotationRecastRule("Long Buff", 2.0, bar="front"),),
        uptime_fraction=1.0,
    )
    service = RotationDurationRefinementService(
        duration_analysis=_FakeDurationAnalysis(seed_projection, final_projection)
    )

    result = service.refine(_plan())

    assert result.duration_projection.analysis.summaries[0].uptime_fraction == 1.0


def test_refinement_service_preserves_duration_resolution_unresolved() -> None:
    seed_projection = _projection(
        unresolved=("Unknown Skill: canonical duration unavailable",)
    )
    final_projection = _projection(
        unresolved=("Unknown Skill: canonical duration unavailable",)
    )
    service = RotationDurationRefinementService(
        duration_analysis=_FakeDurationAnalysis(seed_projection, final_projection)
    )

    result = service.refine(_plan())

    assert "baseline unresolved" in result.plan.unresolved
    assert "Unknown Skill: canonical duration unavailable" in result.plan.unresolved


def test_refinement_service_deduplicates_unresolved_evidence() -> None:
    seed_projection = _projection(unresolved=("baseline unresolved",))
    final_projection = _projection(unresolved=("baseline unresolved",))
    service = RotationDurationRefinementService(
        duration_analysis=_FakeDurationAnalysis(seed_projection, final_projection)
    )

    result = service.refine(_plan())

    assert result.plan.unresolved.count("baseline unresolved") == 1
