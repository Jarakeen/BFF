from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
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
    def __init__(self):
        self.components = _Components()

    def evaluate_entity_id(self, **kwargs):
        reviewed_percent = float(kwargs.get("additional_healing_done_percent", 0.0))
        output = 1000.0 * (1.0 + reviewed_percent / 100.0)
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=42, name="Test Heal"),
            components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
            component_actual_effect_trace=(
                SimpleNamespace(coefficient_number=1, output_value=output),
            ),
            unresolved=(),
        )


class _SkillLines:
    @staticmethod
    def skill_line_for_ability_name(_name):
        return None

    @staticmethod
    def passive_max_rank(_name):
        return None


class _Siphoner:
    @staticmethod
    def resolve(**_kwargs):
        return SimpleNamespace(multiplier=1.09, unresolved=())


class _LivingDeath:
    @staticmethod
    def resolve(**_kwargs):
        return SimpleNamespace(multiplier=1.03, unresolved=())


class _Warden:
    @staticmethod
    def resolve(**_kwargs):
        return SimpleNamespace(multiplier=1.0, unresolved=())


class _Mastery:
    @staticmethod
    def resolve(**_kwargs):
        return SimpleNamespace(
            selected_masteries=(),
            critical_healing_bonus=0.0,
            critical_healing_cap=1.25,
            unresolved=(),
        )


def _context():
    return SimpleNamespace(
        progression=CharacterProgression(passive_ranks={}),
        active_bar="front",
        core_state=SimpleNamespace(
            derived={
                StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.20),
            }
        ),
    )


def test_reviewed_bar_healing_done_sources_add_in_one_bucket():
    service = ExtremeHealingEventService(
        tooltip_service=_Tooltip(),
        skill_line_repository=_SkillLines(),
        nightblade_siphoning_healing=_Siphoner(),
        necromancer_living_death_slotted_healing=_LivingDeath(),
        warden_green_balance_healing=_Warden(),
        nightblade_class_mastery_healing=_Mastery(),
    )

    result = service.evaluate(
        build=PlayerBuild(BuildName="Healing Done Stack"),
        context=_context(),
        entity_id="test_heal",
    )

    assert result.normal_heal == pytest.approx(1120.0)
    assert result.critical_heal == pytest.approx(1904.0)
    assert result.normal_heal != pytest.approx(1122.7)
    assert result.unresolved == ()
    assert result.mechanic_complete
