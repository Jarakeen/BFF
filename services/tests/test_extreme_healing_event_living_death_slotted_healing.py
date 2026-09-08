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
            skill=SimpleNamespace(skill_rank_id=42, name="Combat Prayer"),
            components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
            component_actual_effect_trace=(),
            unresolved=(),
        )


class _SkillLines:
    def __init__(self, *, resolve_mortal_coil=True):
        self.lines = {
            "Combat Prayer": "Restoration Staff",
        }
        if resolve_mortal_coil:
            self.lines["Mortal Coil"] = "Living Death"

    def skill_line_for_ability_name(self, name):
        return self.lines.get(name)

    @staticmethod
    def passive_max_rank(_name):
        return None


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


def test_living_death_slotted_bonus_increases_non_living_death_heal_before_crit():
    skill_lines = _SkillLines()
    service = ExtremeHealingEventService(
        tooltip_service=_Tooltip(),
        skill_line_repository=skill_lines,
    )
    build = PlayerBuild(
        BuildName="Tether Carrier Necromancer",
        EsoClass="necromancer",
        FrontBarSkills=["Combat Prayer", "Mortal Coil", "", "", "", ""],
    )

    result = service.evaluate(
        build=build,
        context=_context(),
        entity_id="combat_prayer",
    )

    assert result.normal_heal == pytest.approx(1030.0)
    assert result.critical_heal == pytest.approx(1751.0)
    assert result.unresolved == ()
    assert result.mechanic_complete


def test_unknown_tether_skill_line_preserves_base_heal_as_lower_bound_blocker():
    skill_lines = _SkillLines(resolve_mortal_coil=False)
    service = ExtremeHealingEventService(
        tooltip_service=_Tooltip(),
        skill_line_repository=skill_lines,
    )
    build = PlayerBuild(
        BuildName="Unknown Tether Carrier",
        EsoClass="necromancer",
        FrontBarSkills=["Combat Prayer", "Mortal Coil", "", "", "", ""],
    )

    result = service.evaluate(
        build=build,
        context=_context(),
        entity_id="combat_prayer",
    )

    assert result.normal_heal == pytest.approx(1000.0)
    assert result.critical_heal == pytest.approx(1700.0)
    assert any("Mortal Coil" in message for message in result.unresolved)
    assert not result.mechanic_complete
