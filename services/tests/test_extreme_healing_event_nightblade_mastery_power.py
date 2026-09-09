from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.skill_component_classification import SkillEffectKind
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_healing_event_service import ExtremeHealingEventService


class _FakeComponents:
    def get_for_skill_rank(self, _skill_rank_id):
        return (
            SimpleNamespace(
                coefficient_number=1,
                effect_kind=SkillEffectKind.HEAL,
                can_crit=True,
            ),
        )


class _PowerAwareTooltipService:
    components = _FakeComponents()

    def evaluate_entity_id(self, **kwargs):
        assert kwargs["additional_power_bonus"] == pytest.approx(1500.0)
        assert kwargs["additional_power_sources"] == (
            "Nightblade Class Mastery: An Eye for Exploitation",
        )
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=42, name="Healthy Offering"),
            components=(SimpleNamespace(coefficient_number=1, final_value=3000.0),),
            component_actual_effect_trace=(
                SimpleNamespace(coefficient_number=1, output_value=5000.0),
            ),
            unresolved=(),
        )


class _EyeForExploitation:
    def resolve(self, **kwargs):
        assert kwargs["target_health_fraction"] == pytest.approx(0.25)
        assert kwargs["battle_spirit_active"] is False
        return SimpleNamespace(
            selected_masteries=("An Eye for Exploitation",),
            critical_healing_bonus=0.0,
            critical_healing_cap=1.25,
            weapon_spell_damage_bonus=1500.0,
            unresolved=(),
        )


class _NeutralLivingDeath:
    def resolve(self, **_kwargs):
        return SimpleNamespace(multiplier=1.0, unresolved=())


class _NeutralSkillLines:
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


def test_eye_for_exploitation_power_is_applied_before_heal_event_scoring():
    service = ExtremeHealingEventService(
        tooltip_service=_PowerAwareTooltipService(),
        skill_line_repository=_NeutralSkillLines(),
        temporal_scope=_SingleInstant(),
        recipient_scope=_SingleRecipient(),
        nightblade_class_mastery_healing=_EyeForExploitation(),
        necromancer_living_death_slotted_healing=_NeutralLivingDeath(),
    )
    context = SimpleNamespace(
        core_state=SimpleNamespace(
            derived={StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.0)}
        ),
        progression=None,
        active_bar="front",
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="Nightblade mastery proof", EsoClass="Nightblade"),
        context=context,
        entity_id="healthy_offering",
        target_health_fraction=0.25,
    )

    assert result.normal_heal == pytest.approx(5000.0)
    assert result.critical_heal == pytest.approx(7500.0)
    assert result.unresolved == ()
