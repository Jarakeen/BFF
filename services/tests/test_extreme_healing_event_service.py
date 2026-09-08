from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.skill_component_classification import SkillEffectKind
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_healing_event_service import ExtremeHealingEventService


class _FakeComponents:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def get_for_skill_rank(self, _skill_rank_id):
        return self.rows


class _FakeTooltipService:
    def __init__(self, result, rows):
        self.result = result
        self.components = _FakeComponents(rows)

    def evaluate_entity_id(self, **_kwargs):
        return self.result


def _context(*, critical_healing: float):
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.CRITICAL_HEALING: SimpleNamespace(final_value=critical_healing),
            }
        )
    )


def _result(*, component_values, actual_values=(), unresolved=()):
    return SimpleNamespace(
        skill=SimpleNamespace(skill_rank_id=42),
        components=tuple(
            SimpleNamespace(coefficient_number=number, final_value=value)
            for number, value in component_values
        ),
        component_actual_effect_trace=tuple(
            SimpleNamespace(coefficient_number=number, output_value=value)
            for number, value in actual_values
        ),
        unresolved=tuple(unresolved),
    )


def _component(number, kind, *, can_crit=True):
    return SimpleNamespace(
        coefficient_number=number,
        effect_kind=kind,
        can_crit=can_crit,
    )


def test_healing_event_uses_actual_effect_heal_component_and_critical_healing_bonus():
    tooltip = _FakeTooltipService(
        _result(
            component_values=((1, 1000.0),),
            actual_values=((1, 1200.0),),
        ),
        (_component(1, SkillEffectKind.HEAL),),
    )
    service = ExtremeHealingEventService(tooltip_service=tooltip)

    result = service.evaluate(
        build=PlayerBuild(BuildName="Healer"),
        context=_context(critical_healing=0.20),
        entity_id="test_heal",
    )

    assert result.normal_heal == pytest.approx(1200.0)
    assert result.critical_healing_bonus == pytest.approx(0.20)
    assert result.critical_multiplier == pytest.approx(1.70)
    assert result.critical_heal == pytest.approx(2040.0)
    assert result.heal_coefficient_numbers == (1,)
    assert result.crit_eligible_coefficient_numbers == (1,)
    assert result.noncrit_coefficient_numbers == ()
    assert result.mechanic_complete


def test_healing_event_excludes_non_heal_components_from_mixed_ability():
    tooltip = _FakeTooltipService(
        _result(
            component_values=((1, 900.0), (2, 5000.0)),
            actual_values=((1, 990.0),),
        ),
        (
            _component(1, SkillEffectKind.HEAL),
            _component(2, SkillEffectKind.DAMAGE),
        ),
    )
    service = ExtremeHealingEventService(tooltip_service=tooltip)

    result = service.evaluate(
        build=PlayerBuild(BuildName="Mixed"),
        context=_context(critical_healing=0.10),
        entity_id="mixed_skill",
    )

    assert result.normal_heal == pytest.approx(990.0)
    assert result.critical_heal == pytest.approx(1584.0)


def test_noncrittable_heal_component_stays_normal_inside_critical_event():
    tooltip = _FakeTooltipService(
        _result(component_values=((1, 1000.0), (2, 500.0))),
        (
            _component(1, SkillEffectKind.HEAL, can_crit=True),
            _component(2, SkillEffectKind.HEAL, can_crit=False),
        ),
    )
    service = ExtremeHealingEventService(tooltip_service=tooltip)

    result = service.evaluate(
        build=PlayerBuild(BuildName="Mixed Crit Eligibility"),
        context=_context(critical_healing=0.20),
        entity_id="mixed_crit_heal",
    )

    assert result.normal_heal == pytest.approx(1500.0)
    assert result.critical_heal == pytest.approx(2200.0)
    assert result.crit_eligible_coefficient_numbers == (1,)
    assert result.noncrit_coefficient_numbers == (2,)
    assert result.mechanic_complete


def test_unknown_heal_critical_eligibility_blocks_critical_maximum():
    tooltip = _FakeTooltipService(
        _result(component_values=((1, 1000.0),)),
        (_component(1, SkillEffectKind.HEAL, can_crit=None),),
    )
    service = ExtremeHealingEventService(tooltip_service=tooltip)

    result = service.evaluate(
        build=PlayerBuild(BuildName="Unknown Crit"),
        context=_context(critical_healing=0.20),
        entity_id="unknown_crit_heal",
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal is None
    assert any("critical eligibility unresolved" in message for message in result.unresolved)
    assert not result.mechanic_complete


def test_healing_event_preserves_unresolved_mechanics_instead_of_claiming_complete():
    tooltip = _FakeTooltipService(
        _result(
            component_values=((1, 1000.0),),
            unresolved=("unresolved healing passive",),
        ),
        (_component(1, SkillEffectKind.HEAL),),
    )
    service = ExtremeHealingEventService(tooltip_service=tooltip)

    result = service.evaluate(
        build=PlayerBuild(BuildName="Healer"),
        context=_context(critical_healing=0.0),
        entity_id="test_heal",
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1500.0)
    assert "unresolved healing passive" in result.unresolved
    assert not result.mechanic_complete


def test_healing_event_requires_heal_classification():
    tooltip = _FakeTooltipService(
        _result(component_values=((1, 5000.0),)),
        (_component(1, SkillEffectKind.DAMAGE),),
    )
    service = ExtremeHealingEventService(tooltip_service=tooltip)

    result = service.evaluate(
        build=PlayerBuild(BuildName="Not A Healer"),
        context=_context(critical_healing=0.0),
        entity_id="damage_skill",
    )

    assert result.normal_heal is None
    assert result.critical_heal is None
    assert any("no HEAL-classified" in message for message in result.unresolved)
    assert not result.mechanic_complete
