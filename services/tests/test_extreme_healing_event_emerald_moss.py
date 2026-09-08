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

    def evaluate_entity_id(self, **_kwargs):
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=42, name="Budding Seeds"),
            components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
            component_actual_effect_trace=(),
            unresolved=(),
        )


class _SkillLines:
    def __init__(self):
        self.lines = {
            "Budding Seeds": "Green Balance",
            "Enchanted Growth": "Green Balance",
            "Blue Betty": "Animal Companions",
        }

    def skill_line_for_ability_name(self, name):
        return self.lines.get(name)

    @staticmethod
    def passive_max_rank(name):
        return 2 if name == "Emerald Moss" else None


def _context(progression):
    return SimpleNamespace(
        progression=progression,
        active_bar="front",
        core_state=SimpleNamespace(
            derived={
                StatId.CRITICAL_HEALING: SimpleNamespace(final_value=0.20),
            }
        ),
    )


def test_actual_heal_event_applies_emerald_moss_family_multiplier_before_crit():
    skill_lines = _SkillLines()
    service = ExtremeHealingEventService(
        tooltip_service=_Tooltip(),
        skill_line_repository=skill_lines,
    )
    build = PlayerBuild(
        BuildName="Emerald Moss Warden",
        EsoClass="warden",
        FrontBarSkills=[
            "Budding Seeds",
            "Enchanted Growth",
            "Blue Betty",
            "",
            "",
            "",
        ],
    )
    progression = CharacterProgression(passive_ranks={"Emerald Moss": 2})

    result = service.evaluate(
        build=build,
        context=_context(progression),
        entity_id="budding_seeds",
    )

    assert result.normal_heal == pytest.approx(1100.0)
    assert result.critical_heal == pytest.approx(1870.0)
    assert result.unresolved == ()
    assert result.mechanic_complete


def test_actual_heal_event_keeps_emerald_moss_unknown_slot_as_lower_bound_blocker():
    skill_lines = _SkillLines()
    service = ExtremeHealingEventService(
        tooltip_service=_Tooltip(),
        skill_line_repository=skill_lines,
    )
    build = PlayerBuild(
        BuildName="Emerald Moss Unknown Slot",
        EsoClass="warden",
        FrontBarSkills=["Budding Seeds", "Mystery Skill", "", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Emerald Moss": 2})

    result = service.evaluate(
        build=build,
        context=_context(progression),
        entity_id="budding_seeds",
    )

    assert result.normal_heal == pytest.approx(1050.0)
    assert result.critical_heal == pytest.approx(1785.0)
    assert any("Mystery Skill" in message for message in result.unresolved)
    assert not result.mechanic_complete
