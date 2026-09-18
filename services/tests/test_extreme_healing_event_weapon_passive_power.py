from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.skill_component_classification import SkillEffectKind
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_healing_event_service import ExtremeHealingEventService


class _Components:
    def get_for_skill_rank(self, _skill_rank_id):
        return (
            SimpleNamespace(
                coefficient_number=1,
                effect_kind=SkillEffectKind.HEAL,
                can_crit=True,
            ),
        )


class _Tooltip:
    components = _Components()

    def evaluate_entity_id(self, **kwargs):
        assert kwargs["additional_power_bonus"] == pytest.approx(275.0)
        assert kwargs["additional_power_sources"] == ("Twin Blade and Blunt: 2 sword(s)",)
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=7, name="Test Heal"),
            components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
            component_actual_effect_trace=(
                SimpleNamespace(coefficient_number=1, output_value=2000.0),
            ),
            unresolved=(),
        )


class _WeaponPower:
    def resolve(self, **kwargs):
        assert kwargs["active_bar"] == "front"
        return SimpleNamespace(
            power_bonus=275.0,
            sources=("Twin Blade and Blunt: 2 sword(s)",),
            unresolved=(),
        )


class _Mastery:
    def resolve(self, **_kwargs):
        return SimpleNamespace(
            selected_masteries=(),
            critical_healing_bonus=0.0,
            critical_healing_cap=1.25,
            weapon_spell_damage_bonus=0.0,
            unresolved=(),
        )


class _LivingDeath:
    def resolve(self, **_kwargs):
        return SimpleNamespace(multiplier=1.0, unresolved=())


class _SkillLines:
    def skill_line_for_ability_name(self, _name):
        return None

    def passive_max_rank(self, _name):
        return None


class _SingleInstant:
    def resolve(self, **_kwargs):
        return SimpleNamespace(single_instant_safe=True, unresolved=())


class _SingleRecipient:
    def resolve(self, **_kwargs):
        return SimpleNamespace(
            single_recipient_safe=True,
            recipient_selection_required=False,
            selected_coefficient_numbers=None,
            unresolved=(),
        )


def test_standing_weapon_passive_power_is_added_before_h1_coefficient_scoring() -> None:
    service = ExtremeHealingEventService(
        tooltip_service=_Tooltip(),
        skill_line_repository=_SkillLines(),
        temporal_scope=_SingleInstant(),
        recipient_scope=_SingleRecipient(),
        nightblade_class_mastery_healing=_Mastery(),
        necromancer_living_death_slotted_healing=_LivingDeath(),
        weapon_passive_power=_WeaponPower(),
    )
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.0)}
        ),
        progression=None,
        active_bar="front",
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="weapon passive H1 proof"),
        context=context,
        entity_id="test_heal",
    )

    assert result.normal_heal == pytest.approx(2000.0)
    assert result.critical_heal == pytest.approx(3000.0)
    assert result.unresolved == ()
