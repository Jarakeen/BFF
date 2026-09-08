from __future__ import annotations

from dataclasses import replace

import pytest

from minmax.base_character_state import BaseCharacterCalculator, PercentContribution
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.sorcerer_passive_input_resolver import SorcererPassiveInputResolver
from models.build_model import PlayerBuild


def test_native_sorcerer_expert_summoner_adds_five_percent_magicka_and_stamina():
    resolver = SorcererPassiveInputResolver()
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Sorcerer"),
        expert_summoner_owned=True,
    )

    assert result.magicka.skill_percent_contributions == (
        PercentContribution("Sorcerer: Expert Summoner", 0.05),
    )
    assert result.stamina.skill_percent_contributions == (
        PercentContribution("Sorcerer: Expert Summoner", 0.05),
    )
    state = BaseCharacterCalculator().calculate(
        magicka=result.magicka,
        stamina=result.stamina,
    )
    assert state.max_magicka == 12600
    assert state.max_stamina == 12600
    assert result.applied_effect_count == 2


def test_explicit_class_route_can_remove_native_daedric_summoning():
    resolver = SorcererPassiveInputResolver()
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Sorcerer",
            ClassSkillLines=["Dark Magic", "Storm Calling", "Green Balance"],
        ),
        expert_summoner_owned=True,
    )

    assert result.magicka.skill_percent_contributions == ()
    assert result.stamina.skill_percent_contributions == ()


def test_foreign_base_class_can_use_explicit_daedric_summoning_route():
    resolver = SorcererPassiveInputResolver()
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Restoring Light", "Daedric Summoning", "Green Balance"],
        ),
        expert_summoner_owned=True,
    )

    assert result.magicka.skill_percent_contributions[-1].value == pytest.approx(0.05)
    assert result.stamina.skill_percent_contributions[-1].value == pytest.approx(0.05)


def test_unowned_expert_summoner_does_not_apply():
    resolver = SorcererPassiveInputResolver()
    result = resolver.apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Sorcerer"),
        expert_summoner_owned=False,
    )

    assert result.magicka.skill_percent_contributions == ()
    assert result.stamina.skill_percent_contributions == ()


def test_expert_summoner_joins_existing_resource_percent_buckets_additively():
    resolver = SorcererPassiveInputResolver()
    baseline = GearCalculationInputs(
        magicka=replace(
            GearCalculationInputs().magicka,
            skill_percent_contributions=(PercentContribution("Existing Magicka", 0.08),),
        ),
        stamina=replace(
            GearCalculationInputs().stamina,
            skill_percent_contributions=(PercentContribution("Existing Stamina", 0.06),),
        ),
    )
    result = resolver.apply(
        baseline,
        PlayerBuild(EsoClass="Sorcerer"),
        expert_summoner_owned=True,
    )

    assert tuple(item.value for item in result.magicka.skill_percent_contributions) == pytest.approx(
        (0.08, 0.05)
    )
    assert tuple(item.value for item in result.stamina.skill_percent_contributions) == pytest.approx(
        (0.06, 0.05)
    )
    state = BaseCharacterCalculator().calculate(
        magicka=result.magicka,
        stamina=result.stamina,
    )
    assert state.max_magicka == 13560
    assert state.max_stamina == 13321
