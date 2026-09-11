from types import SimpleNamespace

import pytest

from minmax.skill_component_classification import (
    HealTemporalScope,
    SkillComponentClassification,
    SkillEffectKind,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingService,
)


class _Coefficients:
    def resolve_name(self, name):
        return SimpleNamespace(
            rank=SimpleNamespace(skill_rank_id=10, entity_id="runtime_heal"),
            unresolved=(),
        )


class _Components:
    def __init__(self, temporal):
        self.classification = SkillComponentClassification(
            skill_rank_id=10,
            coefficient_number=2,
            effect_kind=SkillEffectKind.HEAL,
            is_dot=temporal is HealTemporalScope.PERIODIC,
            heal_temporal_scope=temporal,
            source="test",
            confidence=1.0,
        )

    def get_for_skill_rank(self, skill_rank_id):
        return (self.classification,)


class _Tooltip:
    def __init__(self, temporal):
        self.coefficients = _Coefficients()
        self.components = _Components(temporal)

    def evaluate_entity_id(self, *, build, context, entity_id):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=10),
            components=(SimpleNamespace(coefficient_number=2, final_value=250.0),),
            component_actual_effect_trace=(
                SimpleNamespace(coefficient_number=2, output_value=context.actual_heal),
            ),
            unresolved=(),
        )


def _service(temporal):
    return RotationHealerActionHealingService(
        ".",
        tooltip_service=_Tooltip(temporal),
    )


def test_delayed_component_can_be_recalculated_when_delayed_scope_is_requested():
    result = _service(HealTemporalScope.DELAYED).resolve_component_magnitude(
        build=object(),
        context=SimpleNamespace(actual_heal=812.5),
        source_name="Delayed Bloom",
        coefficient_number=2,
        expected_temporal_scope=HealTemporalScope.DELAYED,
    )

    assert result.resolved is True
    assert result.modeled_heal == pytest.approx(812.5)
    assert result.unresolved == ()


def test_delayed_component_is_rejected_when_periodic_scope_is_requested():
    result = _service(HealTemporalScope.DELAYED).resolve_component_magnitude(
        build=object(),
        context=SimpleNamespace(actual_heal=812.5),
        source_name="Delayed Bloom",
        coefficient_number=2,
        expected_temporal_scope=HealTemporalScope.PERIODIC,
    )

    assert result.resolved is False
    assert result.modeled_heal is None
    assert result.unresolved == (
        "Delayed Bloom coefficient 2: component is not canonical periodic healing",
    )


def test_channel_tick_component_is_supported_by_scoped_component_evaluator():
    result = _service(HealTemporalScope.CHANNEL_TICK).resolve_component_magnitude(
        build=object(),
        context=SimpleNamespace(actual_heal=625.0),
        source_name="Channel Heal",
        coefficient_number=2,
        expected_temporal_scope=HealTemporalScope.CHANNEL_TICK,
    )

    assert result.resolved is True
    assert result.modeled_heal == pytest.approx(625.0)
    assert result.unresolved == ()
