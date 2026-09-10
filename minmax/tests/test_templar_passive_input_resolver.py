from __future__ import annotations

from dataclasses import replace

import pytest

from minmax.derived_stats import StatContribution
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.templar_passive_input_resolver import TemplarPassiveInputResolver
from models.build_model import PlayerBuild


def test_native_templar_balanced_warrior_adds_six_percent_weapon_and_spell_damage():
    result = TemplarPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Templar"),
        balanced_warrior_owned=True,
    )

    assert result.core.weapon_damage.percent == (
        StatContribution("Templar: Balanced Warrior", 0.06),
    )
    assert result.core.spell_damage.percent == (
        StatContribution("Templar: Balanced Warrior", 0.06),
    )
    assert result.applied_effect_count == 2


def test_explicit_class_route_can_remove_native_aedric_spear():
    result = TemplarPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Templar",
            ClassSkillLines=["Dawn's Wrath", "Restoring Light", "Green Balance"],
        ),
        balanced_warrior_owned=True,
    )

    assert result.core.weapon_damage.percent == ()
    assert result.core.spell_damage.percent == ()
    assert result.applied_effect_count == 0


def test_foreign_base_class_can_gain_balanced_warrior_through_aedric_spear_route():
    result = TemplarPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Aedric Spear"],
        ),
        balanced_warrior_owned=True,
    )

    assert result.core.weapon_damage.percent[-1].value == pytest.approx(0.06)
    assert result.core.spell_damage.percent[-1].value == pytest.approx(0.06)


def test_unowned_balanced_warrior_does_not_apply():
    result = TemplarPassiveInputResolver().apply(
        GearCalculationInputs(),
        PlayerBuild(EsoClass="Templar"),
        balanced_warrior_owned=False,
    )

    assert result.core.weapon_damage.percent == ()
    assert result.core.spell_damage.percent == ()


def test_balanced_warrior_joins_existing_weapon_spell_damage_percent_bucket():
    baseline = GearCalculationInputs(
        core=replace(
            GearCalculationInputs().core,
            weapon_damage=replace(
                GearCalculationInputs().core.weapon_damage,
                percent=(StatContribution("Existing Weapon", 0.08),),
            ),
            spell_damage=replace(
                GearCalculationInputs().core.spell_damage,
                percent=(StatContribution("Existing Spell", 0.05),),
            ),
        )
    )

    result = TemplarPassiveInputResolver().apply(
        baseline,
        PlayerBuild(EsoClass="Templar"),
        balanced_warrior_owned=True,
    )

    assert tuple(item.value for item in result.core.weapon_damage.percent) == pytest.approx(
        (0.08, 0.06)
    )
    assert tuple(item.value for item in result.core.spell_damage.percent) == pytest.approx(
        (0.05, 0.06)
    )
