from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.rotation_healer_action_healing_service import RotationHealerActionHealingService
from services.rotation_plan_runtime_build_context_service import (
    RotationPlanRuntimeBuildContextResult,
)


class _Coefficients:
    def resolve_name(self, name):
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=10, entity_id="heal_entity"),
            unresolved=(),
        )


class _Components:
    def get_for_skill_rank(self, skill_rank_id):
        return (
            SkillComponentClassification(
                skill_rank_id=10,
                coefficient_number=1,
                effect_kind=SkillEffectKind.HEAL,
                is_dot=False,
                source="test",
                confidence=1.0,
            ),
        )

    def is_intentionally_excluded_caster_healing_component(self, **kwargs):
        return False


class _Tooltip:
    def __init__(self) -> None:
        self.coefficients = _Coefficients()
        self.components = _Components()
        self.calls = []

    def evaluate_entity_id(self, *, build, context, entity_id):
        self.calls.append((context, entity_id))
        value = float(getattr(context, "heal_value"))
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=10),
            components=(SimpleNamespace(coefficient_number=1, final_value=value),),
            component_actual_effect_trace=(),
            unresolved=(),
        )


def _plan():
    return RotationPlan(
        character_name="Runtime Healer",
        build_name="Exact State",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                time_seconds=4.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Heal",
                bar="front",
            ),
            RotationAction(
                time_seconds=12.0,
                sequence=2,
                kind=RotationActionKind.SKILL,
                name="Heal",
                bar="back",
            ),
        ),
    )


def test_healer_actions_use_exact_runtime_context_for_each_cast() -> None:
    tooltip = _Tooltip()
    service = RotationHealerActionHealingService(".", tooltip_service=tooltip)
    front = SimpleNamespace(heal_value=1100.0)
    back = SimpleNamespace(heal_value=1450.0)
    calls = []

    def runtime_context(time_seconds, sequence=None):
        calls.append((time_seconds, sequence))
        if time_seconds < 10.0:
            return RotationPlanRuntimeBuildContextResult(
                time_seconds=time_seconds,
                sequence=sequence,
                active_bar="front",
                context=front,
                unresolved=(),
            )
        return RotationPlanRuntimeBuildContextResult(
            time_seconds=time_seconds,
            sequence=sequence,
            active_bar="back",
            context=back,
            unresolved=(),
        )

    projection = service.project(
        plan=_plan(),
        build=PlayerBuild(),
        context=SimpleNamespace(heal_value=999.0),
        runtime_build_context_resolver=runtime_context,
    )

    assert projection.unresolved == ()
    assert calls == [(4.0, 1), (12.0, 2)]
    assert [call[0] for call in tooltip.calls] == [front, back]
    assert [event.modeled_heal for event in projection.direct_events] == [1100.0, 1450.0]


def test_unresolved_runtime_context_blocks_only_that_heal() -> None:
    tooltip = _Tooltip()
    service = RotationHealerActionHealingService(".", tooltip_service=tooltip)

    def runtime_context(time_seconds, sequence=None):
        if time_seconds == 4.0:
            return RotationPlanRuntimeBuildContextResult(
                time_seconds=time_seconds,
                sequence=sequence,
                active_bar="front",
                context=None,
                unresolved=("proc window unresolved",),
            )
        return RotationPlanRuntimeBuildContextResult(
            time_seconds=time_seconds,
            sequence=sequence,
            active_bar="back",
            context=SimpleNamespace(heal_value=1450.0),
            unresolved=(),
        )

    projection = service.project(
        plan=_plan(),
        build=PlayerBuild(),
        context=SimpleNamespace(heal_value=999.0),
        runtime_build_context_resolver=runtime_context,
    )

    assert len(projection.direct_events) == 1
    assert projection.direct_events[0].time_seconds == 12.0
    assert projection.unresolved == (
        "Heal at 4s: runtime context: proc window unresolved",
    )


def test_runtime_active_bar_mismatch_fails_closed_before_tooltip_math() -> None:
    tooltip = _Tooltip()
    service = RotationHealerActionHealingService(".", tooltip_service=tooltip)

    def runtime_context(time_seconds, sequence=None):
        return RotationPlanRuntimeBuildContextResult(
            time_seconds=time_seconds,
            sequence=sequence,
            active_bar="back",
            context=SimpleNamespace(heal_value=1400.0),
            unresolved=(),
        )

    plan = RotationPlan(
        character_name="Runtime Healer",
        build_name="Bar Mismatch",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=3.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Heal",
                bar="front",
            ),
        ),
    )
    projection = service.project(
        plan=plan,
        build=PlayerBuild(),
        context=SimpleNamespace(heal_value=999.0),
        runtime_build_context_resolver=runtime_context,
    )

    assert projection.direct_events == ()
    assert tooltip.calls == []
    assert projection.unresolved == (
        "Heal at 3s: scheduled front bar does not match runtime active back bar",
    )
