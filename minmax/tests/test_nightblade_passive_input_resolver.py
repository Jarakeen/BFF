from __future__ import annotations

from dataclasses import replace

import pytest

from minmax.base_character_state import BaseCharacterCalculator, PercentContribution
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.nightblade_passive_input_resolver import NightbladePassiveInputResolver
from models.build_model import PlayerBuild


class _SkillLines:
    def __init__(self, mapping):
        self.mapping = dict(mapping)

    def skill_line_for_ability_name(self, name):
        return self.mapping.get(str(name))


def _resolver(mapping):
    return NightbladePassiveInputResolver(_SkillLines(mapping))


def test_native_nightblade_with_siphoning_slot_gets_six_percent_max_resources():
    resolver = _resolver({"Healthy Offering": "Siphoning"})
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Nightblade",
            FrontBarSkills=["Healthy Offering"],
        ),
        active_bar="front",
        magicka_flood_owned=True,
    )

    expected = (PercentContribution("Nightblade: Magicka Flood", 0.06),)
    assert result.magicka.skill_percent_contributions == expected
    assert result.stamina.skill_percent_contributions == expected
    state = BaseCharacterCalculator().calculate(
        magicka=result.magicka,
        stamina=result.stamina,
    )
    assert state.max_magicka == 12720
    assert state.max_stamina == 12720


def test_magicka_flood_is_active_bar_only():
    resolver = _resolver({"Healthy Offering": "Siphoning"})
    build = PlayerBuild(
        EsoClass="Nightblade",
        FrontBarSkills=["Combat Prayer"],
        BackBarSkills=["Healthy Offering"],
    )

    front = resolver.apply(
        GearCalculationInputs(),
        build,
        active_bar="front",
        magicka_flood_owned=True,
    )
    back = resolver.apply(
        GearCalculationInputs(),
        build,
        active_bar="back",
        magicka_flood_owned=True,
    )

    assert front.magicka.skill_percent_contributions == ()
    assert front.stamina.skill_percent_contributions == ()
    assert back.magicka.skill_percent_contributions[-1].value == pytest.approx(0.06)
    assert back.stamina.skill_percent_contributions[-1].value == pytest.approx(0.06)


def test_explicit_class_route_can_remove_native_siphoning_access():
    resolver = _resolver({"Healthy Offering": "Siphoning"})
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Nightblade",
            ClassSkillLines=["Assassination", "Shadow", "Green Balance"],
            FrontBarSkills=["Healthy Offering"],
        ),
        magicka_flood_owned=True,
    )

    assert result.magicka.skill_percent_contributions == ()
    assert result.stamina.skill_percent_contributions == ()
    assert result.unresolved == ()


def test_foreign_base_class_can_use_explicit_siphoning_route():
    resolver = _resolver({"Healthy Offering": "Siphoning"})
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Siphoning", "Green Balance"],
            FrontBarSkills=["Healthy Offering"],
        ),
        magicka_flood_owned=True,
    )

    assert result.magicka.skill_percent_contributions[-1].value == pytest.approx(0.06)
    assert result.stamina.skill_percent_contributions[-1].value == pytest.approx(0.06)


def test_unknown_active_bar_skill_blocks_trigger_when_siphoning_not_proven():
    resolver = _resolver({})
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Nightblade",
            FrontBarSkills=["Unknown Skill"],
        ),
        magicka_flood_owned=True,
    )

    assert result.magicka.skill_percent_contributions == ()
    assert result.stamina.skill_percent_contributions == ()
    assert result.unresolved
    assert "Magicka Flood trigger is unresolved" in result.unresolved[0]


def test_proven_siphoning_slot_makes_unrelated_unknown_slot_irrelevant():
    resolver = _resolver({"Healthy Offering": "Siphoning"})
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Nightblade",
            FrontBarSkills=["Healthy Offering", "Unknown Skill"],
        ),
        magicka_flood_owned=True,
    )

    assert result.magicka.skill_percent_contributions[-1].value == pytest.approx(0.06)
    assert result.stamina.skill_percent_contributions[-1].value == pytest.approx(0.06)
    assert result.unresolved == ()


def test_magicka_flood_joins_existing_percent_buckets_additively():
    resolver = _resolver({"Healthy Offering": "Siphoning"})
    baseline = GearCalculationInputs(
        magicka=replace(
            GearCalculationInputs().magicka,
            skill_percent_contributions=(PercentContribution("Existing Magicka", 0.05),),
        ),
        stamina=replace(
            GearCalculationInputs().stamina,
            skill_percent_contributions=(PercentContribution("Existing Stamina", 0.02),),
        ),
    )
    result = resolver.apply(
        baseline,
        PlayerBuild(EsoClass="Nightblade", FrontBarSkills=["Healthy Offering"]),
        magicka_flood_owned=True,
    )

    assert tuple(item.value for item in result.magicka.skill_percent_contributions) == pytest.approx(
        (0.05, 0.06)
    )
    assert tuple(item.value for item in result.stamina.skill_percent_contributions) == pytest.approx(
        (0.02, 0.06)
    )
    state = BaseCharacterCalculator().calculate(
        magicka=result.magicka,
        stamina=result.stamina,
    )
    assert state.max_magicka == 13320
    assert state.max_stamina == 12960
