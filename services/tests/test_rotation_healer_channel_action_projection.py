from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.skill_component_classification import (
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from services.rotation_healer_action_healing_service import RotationHealerActionHealingService


class _Coefficients:
    def resolve_name(self, name):
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=10, entity_id="healing_channel"),
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
                heal_temporal_scope=HealTemporalScope.CHANNEL_TICK,
                source="test",
                confidence=1.0,
            ),
        )


class _Tooltip:
    def __init__(self):
        self.coefficients = _Coefficients()
        self.components = _Components()

    def evaluate_entity_id(self, *, build, context, entity_id):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=10),
            components=(SimpleNamespace(coefficient_number=1, final_value=250.0),),
            component_actual_effect_trace=(
                SimpleNamespace(coefficient_number=1, output_value=375.0),
            ),
            unresolved=(),
        )


def test_channel_tick_component_becomes_runtime_seed_instead_of_unresolved():
    plan = RotationPlan(
        character_name="Healer",
        build_name="Channel Build",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=3,
                kind=RotationActionKind.SKILL,
                name="Healing Channel",
                bar="front",
            ),
        ),
    )

    result = RotationHealerActionHealingService(
        ".",
        tooltip_service=_Tooltip(),
    ).project(
        plan=plan,
        build=object(),
        context=object(),
    )

    assert result.unresolved == ()
    assert result.direct_events == ()
    assert result.periodic_seeds == ()
    assert result.delayed_seeds == ()
    assert len(result.channel_seeds) == 1
    seed = result.channel_seeds[0]
    assert seed.time_seconds == 2.0
    assert seed.sequence == 3
    assert seed.source_name == "Healing Channel"
    assert seed.coefficient_number == 1
    assert seed.modeled_heal == 375.0
