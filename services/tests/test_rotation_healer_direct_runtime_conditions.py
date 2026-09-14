from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_output_eligibility import RuntimeOutputEligibilityRule
from minmax.skill_component_classification import (
    SkillComponentClassification,
    SkillEffectKind,
)
from models.build_model import PlayerBuild
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingService,
)
from services.rotation_runtime_output_eligibility_service import (
    RotationRuntimeOutputConditionRule,
    RotationRuntimeOutputEligibilityService,
)


class _Coefficients:
    @staticmethod
    def resolve_name(name):
        entity_id = "overflowing_altar" if name == "Altar" else "conditional_heal"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=10, entity_id=entity_id),
            unresolved=(),
        )


class _Components:
    @staticmethod
    def get_for_skill_rank(_skill_rank_id):
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

    @staticmethod
    def is_intentionally_excluded_caster_healing_component(**_kwargs):
        return False


class _Tooltip:
    coefficients = _Coefficients()
    components = _Components()

    def __init__(self):
        self.calls = []

    def evaluate_entity_id(self, *, build, context, entity_id):
        self.calls.append((build, context, entity_id))
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=10, entity_id=entity_id, name="Conditional Heal"),
            components=(SimpleNamespace(coefficient_number=1, final_value=1200.0),),
            component_actual_effect_trace=(),
            unresolved=(),
        )


def _eligibility():
    return RotationRuntimeOutputEligibilityService(
        rules=(
            RotationRuntimeOutputConditionRule(
                skill_entity_id="conditional_heal",
                coefficient_number=1,
                eligibility=RuntimeOutputEligibilityRule(
                    required_conditions=("target_in_direct_heal_condition",),
                    source="reviewed direct-heal test condition",
                ),
            ),
        )
    )


def _plan(name="Heal"):
    return RotationPlan(
        character_name="Healer",
        build_name="Conditional Direct",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=3.0,
                sequence=2,
                kind=RotationActionKind.SKILL,
                name=name,
                bar="front",
            ),
        ),
    )


def _service(*, resolver=None):
    tooltip = _Tooltip()
    return (
        RotationHealerActionHealingService(
            ".",
            tooltip_service=tooltip,
            output_eligibility_service=_eligibility(),
            condition_context_resolver=resolver,
        ),
        tooltip,
    )


def test_reviewed_direct_heal_missing_condition_context_fails_closed_after_projection():
    service, tooltip = _service()

    result = service.project(
        plan=_plan(),
        build=PlayerBuild(),
        context=object(),
    )

    assert result.direct_events == ()
    assert len(tooltip.calls) == 1
    assert result.unresolved == (
        "Heal coefficient 1 at 3s: conditional_heal coefficient 1: runtime output eligibility requires authoritative ConditionContext for target_in_direct_heal_condition",
    )


def test_reviewed_direct_heal_known_false_condition_drops_event_without_unresolved():
    service, _ = _service(resolver=lambda _event: frozenset())

    result = service.project(
        plan=_plan(),
        build=PlayerBuild(),
        context=object(),
    )

    assert result.direct_events == ()
    assert result.unresolved == ()


def test_reviewed_direct_heal_known_true_condition_keeps_event():
    service, _ = _service(
        resolver=lambda _event: frozenset({"target_in_direct_heal_condition"})
    )

    result = service.project(
        plan=_plan(),
        build=PlayerBuild(),
        context=object(),
    )

    assert result.unresolved == ()
    assert len(result.direct_events) == 1
    event = result.direct_events[0]
    assert event.time_seconds == 3.0
    assert event.sequence == 2
    assert event.modeled_heal == 1200.0


def test_per_call_direct_condition_resolver_overrides_service_default():
    service, _ = _service(resolver=lambda _event: frozenset())

    result = service.project(
        plan=_plan(),
        build=PlayerBuild(),
        context=object(),
        condition_context_resolver=(
            lambda _event: frozenset({"target_in_direct_heal_condition"})
        ),
    )

    assert result.unresolved == ()
    assert len(result.direct_events) == 1


def test_external_conditional_healing_stays_on_separate_path_before_direct_gate():
    service, tooltip = _service()

    result = service.project(
        plan=_plan(name="Altar"),
        build=PlayerBuild(),
        context=object(),
    )

    assert result.direct_events == ()
    assert result.unresolved == ()
    assert len(result.external_conditional_seeds) == 1
    assert result.external_conditional_seeds[0].skill_id == "overflowing_altar"
    assert tooltip.calls == []
