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


class _Mastery:
    def __init__(
        self,
        *,
        selected=(),
        critical_bonus=0.0,
        critical_cap=1.25,
        power_bonus=0.0,
        unresolved=(),
    ):
        self.selected = tuple(selected)
        self.critical_bonus = float(critical_bonus)
        self.critical_cap = float(critical_cap)
        self.power_bonus = float(power_bonus)
        self.unresolved = tuple(unresolved)

    def resolve(self, *, build, target_health_fraction, battle_spirit_active):
        _ = build, target_health_fraction, battle_spirit_active
        return SimpleNamespace(
            selected_masteries=self.selected,
            critical_healing_bonus=self.critical_bonus,
            critical_healing_cap=self.critical_cap,
            weapon_spell_damage_bonus=self.power_bonus,
            unresolved=self.unresolved,
        )


def _context(critical_healing_bonus):
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                StatId.CRITICAL_HEALING: SimpleNamespace(
                    final_value=float(critical_healing_bonus)
                ),
            }
        ),
        progression=None,
        active_bar="front",
    )


def _result():
    return SimpleNamespace(
        skill=SimpleNamespace(skill_rank_id=42, name="Test Heal"),
        components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
        component_actual_effect_trace=(),
        unresolved=(),
    )


def _component(*, can_crit=True):
    return SimpleNamespace(
        coefficient_number=1,
        effect_kind=SkillEffectKind.HEAL,
        can_crit=can_crit,
    )


def _service(mastery):
    return ExtremeHealingEventService(
        tooltip_service=_FakeTooltipService(_result(), (_component(),)),
        nightblade_class_mastery_healing=mastery,
    )


def test_ordinary_event_is_capped_at_125_percent_critical_healing_bonus():
    event = _service(_Mastery()).evaluate(
        build=PlayerBuild(BuildName="Ordinary"),
        context=_context(1.00),
        entity_id="test_heal",
    )

    assert event.normal_heal == pytest.approx(1000.0)
    assert event.critical_healing_bonus == pytest.approx(0.75)
    assert event.critical_multiplier == pytest.approx(2.25)
    assert event.critical_heal == pytest.approx(2250.0)
    assert event.unresolved == ()


def test_above_and_beyond_can_raise_event_cap_to_155_percent_bonus():
    event = _service(
        _Mastery(
            selected=("Above and Beyond",),
            critical_bonus=0.25,
            critical_cap=1.55,
        )
    ).evaluate(
        build=PlayerBuild(BuildName="Pure NB", EsoClass="Nightblade"),
        context=_context(1.00),
        entity_id="test_heal",
    )

    assert event.normal_heal == pytest.approx(1000.0)
    assert event.critical_healing_bonus == pytest.approx(1.05)
    assert event.critical_multiplier == pytest.approx(2.55)
    assert event.critical_heal == pytest.approx(2550.0)
    assert event.unresolved == ()


def test_eye_for_exploitation_remains_explicit_until_power_rebuild_is_wired():
    event = _service(
        _Mastery(
            selected=("An Eye for Exploitation",),
            power_bonus=1500.0,
        )
    ).evaluate(
        build=PlayerBuild(BuildName="Eye NB", EsoClass="Nightblade"),
        context=_context(0.20),
        entity_id="test_heal",
        target_health_fraction=0.25,
    )

    assert event.normal_heal == pytest.approx(1000.0)
    assert event.critical_heal == pytest.approx(1700.0)
    assert any(
        "An Eye for Exploitation Weapon/Spell Damage contribution is not yet applied"
        in message
        for message in event.unresolved
    )
    assert not event.mechanic_complete
