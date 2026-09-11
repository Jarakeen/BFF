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
            rank=SimpleNamespace(skill_rank_id=10, entity_id="runtime_hot"),
            unresolved=(),
        )


class _Components:
    def __init__(self, classification):
        self.classification = classification

    def get_for_skill_rank(self, skill_rank_id):
        return (self.classification,)


class _Tooltip:
    def __init__(self, classification):
        self.coefficients = _Coefficients()
        self.components = _Components(classification)
        self.calls = []

    def evaluate_entity_id(self, *, build, context, entity_id):
        self.calls.append((build, context, entity_id))
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=10),
            components=(SimpleNamespace(coefficient_number=2, final_value=250.0),),
            component_actual_effect_trace=(
                SimpleNamespace(coefficient_number=2, output_value=context.actual_heal),
            ),
            unresolved=(),
        )


def _classification(*, temporal=HealTemporalScope.PERIODIC):
    return SkillComponentClassification(
        skill_rank_id=10,
        coefficient_number=2,
        effect_kind=SkillEffectKind.HEAL,
        is_dot=True if temporal is HealTemporalScope.PERIODIC else False,
        heal_temporal_scope=temporal,
        source="test",
        confidence=1.0,
    )


def test_periodic_component_magnitude_reuses_canonical_actual_effect_math():
    tooltip = _Tooltip(_classification())
    service = RotationHealerActionHealingService(".", tooltip_service=tooltip)
    context = SimpleNamespace(actual_heal=437.5)
    build = object()

    result = service.resolve_component_magnitude(
        build=build,
        context=context,
        source_name="Runtime HoT",
        coefficient_number=2,
    )

    assert result.resolved is True
    assert result.modeled_heal == pytest.approx(437.5)
    assert result.unresolved == ()
    assert tooltip.calls == [(build, context, "runtime_hot")]


def test_component_recalculation_rejects_nonperiodic_heal_component():
    tooltip = _Tooltip(_classification(temporal=HealTemporalScope.DIRECT))
    service = RotationHealerActionHealingService(".", tooltip_service=tooltip)

    result = service.resolve_component_magnitude(
        build=object(),
        context=SimpleNamespace(actual_heal=437.5),
        source_name="Runtime HoT",
        coefficient_number=2,
    )

    assert result.modeled_heal is None
    assert result.resolved is False
    assert result.unresolved == (
        "Runtime HoT coefficient 2: component is not canonical periodic healing",
    )
