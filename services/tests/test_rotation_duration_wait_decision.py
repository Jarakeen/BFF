from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastAnalysis, RotationRecastRule
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_duration_refinement_service import RotationDurationRefinementService


class _FakeDurationAnalysis:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, plan: RotationPlan) -> RotationDurationProjection:
        self.calls += 1
        rules = (
            (RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),)
            if self.calls == 1
            else ()
        )
        return RotationDurationProjection(
            analysis=RotationRecastAnalysis(windows=(), summaries=()),
            rules=rules,
            unresolved=(),
        )


def test_duration_service_passes_wait_decision_provider_to_scheduler() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=2.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Long Buff", "front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, "Long Buff", "front"),
        ),
    )

    def decide(context):
        return RotationAction(
            time_seconds=context.time_seconds,
            sequence=context.slot.sequence,
            kind=RotationActionKind.HEAVY_ATTACK,
            name="Restoration Staff Heavy Attack",
            bar=context.bar,
        )

    result = RotationDurationRefinementService(
        duration_analysis=_FakeDurationAnalysis()
    ).refine(
        plan,
        wait_decision=decide,
    )

    at_two = next(action for action in result.plan.actions if action.time_seconds == 2.0)
    assert at_two.kind is RotationActionKind.HEAVY_ATTACK
    assert at_two.bar == "front"
