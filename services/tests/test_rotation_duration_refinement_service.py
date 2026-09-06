from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastAnalysis, RotationRecastRule
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_duration_refinement_service import RotationDurationRefinementService


class _FakeDurationAnalysis:
    def __init__(self, projection: RotationDurationProjection) -> None:
        self.projection = projection
        self.calls = []

    def analyze(self, plan: RotationPlan) -> RotationDurationProjection:
        self.calls.append(plan)
        return self.projection


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


def test_refinement_service_uses_duration_projection_rules() -> None:
    projection = RotationDurationProjection(
        analysis=RotationRecastAnalysis(windows=(), summaries=()),
        rules=(RotationRecastRule("Long Buff", 10.0, bar="front"),),
        unresolved=(),
    )
    fake = _FakeDurationAnalysis(projection)
    service = RotationDurationRefinementService(duration_analysis=fake)

    result = service.refine(_plan())

    assert len(fake.calls) == 1
    names = [
        action.name
        for action in result.plan.actions
        if action.kind is RotationActionKind.SKILL
    ]
    assert names == ["Long Buff", "Filler", "Filler", "Filler", "Filler"]
    assert result.duration_projection is projection


def test_refinement_service_preserves_duration_resolution_unresolved() -> None:
    projection = RotationDurationProjection(
        analysis=RotationRecastAnalysis(windows=(), summaries=()),
        rules=(),
        unresolved=("Unknown Skill: canonical duration unavailable",),
    )
    service = RotationDurationRefinementService(
        duration_analysis=_FakeDurationAnalysis(projection)
    )

    result = service.refine(_plan())

    assert "baseline unresolved" in result.plan.unresolved
    assert "Unknown Skill: canonical duration unavailable" in result.plan.unresolved


def test_refinement_service_deduplicates_unresolved_evidence() -> None:
    projection = RotationDurationProjection(
        analysis=RotationRecastAnalysis(windows=(), summaries=()),
        rules=(),
        unresolved=("baseline unresolved",),
    )
    service = RotationDurationRefinementService(
        duration_analysis=_FakeDurationAnalysis(projection)
    )

    result = service.refine(_plan())

    assert result.plan.unresolved.count("baseline unresolved") == 1
