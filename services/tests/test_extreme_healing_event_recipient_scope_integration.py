from __future__ import annotations

from types import SimpleNamespace

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


def _context():
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.20),
            }
        ),
        progression=None,
        active_bar="front",
    )


def _result(skill_name):
    return SimpleNamespace(
        skill=SimpleNamespace(skill_rank_id=42, name=skill_name),
        components=(
            SimpleNamespace(coefficient_number=1, final_value=1000.0),
            SimpleNamespace(coefficient_number=2, final_value=700.0),
        ),
        component_actual_effect_trace=(),
        unresolved=(),
    )


def _component(number):
    return SimpleNamespace(
        coefficient_number=number,
        effect_kind=SkillEffectKind.HEAL,
        can_crit=True,
    )


def _service(skill_name):
    tooltip = _FakeTooltipService(
        _result(skill_name),
        (_component(1), _component(2)),
    )
    return ExtremeHealingEventService(tooltip_service=tooltip)


def test_blood_of_the_elder_dragon_does_not_aggregate_distinct_recipients():
    result = _service("Blood of the Elder Dragon").evaluate(
        build=PlayerBuild(BuildName="DK"),
        context=_context(),
        entity_id="blood_of_the_elder_dragon",
    )

    assert result.heal_coefficient_numbers == (1, 2)
    assert result.normal_heal is None
    assert result.critical_heal is None
    assert result.critical_healing_bonus == 0.20
    assert result.critical_multiplier == 1.70
    assert any("one-recipient Extreme heal is unresolved" in message for message in result.unresolved)
    assert not result.mechanic_complete


def test_legacy_coagulating_blood_name_uses_same_recipient_guard():
    result = _service("Coagulating Blood").evaluate(
        build=PlayerBuild(BuildName="Legacy DK"),
        context=_context(),
        entity_id="coagulating_blood",
    )

    assert result.normal_heal is None
    assert result.critical_heal is None
    assert any("distinct self and nearby-ally healing" in message for message in result.unresolved)


def test_unmorphed_dragon_blood_remains_recipient_and_time_safe():
    result = _service("Dragon Blood").evaluate(
        build=PlayerBuild(BuildName="Base DK"),
        context=_context(),
        entity_id="dragon_blood",
    )

    assert result.normal_heal == 1700.0
    assert result.critical_heal == 2890.0
    assert result.unresolved == ()
    assert result.mechanic_complete
