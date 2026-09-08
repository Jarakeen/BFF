from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_progression import CharacterProgression
from minmax.skill_component_actual_effect_modifiers import SkillComponentActualEffectTrace
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
        additional = float(kwargs.get("additional_healing_done_percent", 0.0) or 0.0)
        output = 1000.0 * (1.0 + additional / 100.0)
        traces = ()
        if additional:
            traces = (
                SkillComponentActualEffectTrace(
                    coefficient_number=1,
                    base_power=0.0,
                    power_bonus=0.0,
                    effective_power=0.0,
                    coefficient_value=1000.0,
                    additive_percent=additional,
                    output_value=output,
                    sources=tuple(kwargs.get("additional_healing_done_sources", ()) or ()),
                ),
            )
        return SimpleNamespace(
            skill=SimpleNamespace(skill_rank_id=42, name="Combat Prayer"),
            components=(SimpleNamespace(coefficient_number=1, final_value=1000.0),),
            component_actual_effect_trace=traces,
            unresolved=(),
        )


class _SkillLines:
    def __init__(self):
        self.lines = {
            "Combat Prayer": "Restoration Staff",
            "Funnel Health": "Siphoning",
            "Siphoning Attacks": "Siphoning",
        }

    def skill_line_for_ability_name(self, name):
        return self.lines.get(name)

    @staticmethod
    def passive_max_rank(name):
        if name == "Soul Siphoner":
            return 2
        return None


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


def test_actual_heal_event_applies_soul_siphoner_to_non_siphoning_heal_before_crit():
    skill_lines = _SkillLines()
    service = ExtremeHealingEventService(
        tooltip_service=_Tooltip(),
        skill_line_repository=skill_lines,
    )
    build = PlayerBuild(
        BuildName="Soul Siphoner Nightblade",
        EsoClass="nightblade",
        FrontBarSkills=[
            "Combat Prayer",
            "Funnel Health",
            "Siphoning Attacks",
            "",
            "",
            "",
        ],
    )
    progression = CharacterProgression(passive_ranks={"Soul Siphoner": 2})

    result = service.evaluate(
        build=build,
        context=_context(progression),
        entity_id="combat_prayer",
    )

    assert result.normal_heal == pytest.approx(1060.0)
    assert result.critical_heal == pytest.approx(1802.0)
    assert result.unresolved == ()
    assert result.mechanic_complete


def test_actual_heal_event_keeps_unknown_soul_siphoner_slot_as_lower_bound_blocker():
    skill_lines = _SkillLines()
    service = ExtremeHealingEventService(
        tooltip_service=_Tooltip(),
        skill_line_repository=skill_lines,
    )
    build = PlayerBuild(
        BuildName="Soul Siphoner Unknown Slot",
        EsoClass="nightblade",
        FrontBarSkills=["Combat Prayer", "Funnel Health", "Mystery Skill", "", "", ""],
    )
    progression = CharacterProgression(passive_ranks={"Soul Siphoner": 2})

    result = service.evaluate(
        build=build,
        context=_context(progression),
        entity_id="combat_prayer",
    )

    assert result.normal_heal == pytest.approx(1030.0)
    assert result.critical_heal == pytest.approx(1751.0)
    assert any("Mystery Skill" in message for message in result.unresolved)
    assert not result.mechanic_complete
