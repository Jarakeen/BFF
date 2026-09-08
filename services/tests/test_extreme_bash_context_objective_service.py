from dataclasses import replace

import pytest

from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.formulas.final_calculations import calculate_bash_damage
from models.build_model import GearSlot, PlayerBuild
from services.extreme_bash_context_objective_service import (
    ExtremeBashContextObjectiveService,
)
from services.extreme_bash_objective_service import ExtremeBashDamageInputs


def _dual_bar_heavy_build() -> PlayerBuild:
    build = PlayerBuild()
    for entry in build.Armor.values():
        entry.update(
            {
                "Weight": "Heavy",
                "Level": "CP160",
                "Quality": "Gold",
            }
        )

    build.FrontBarWeapon = GearSlot(
        WeaponType="Sword",
        Trait="Defending",
        Level="CP160",
        Quality="Gold",
    )
    build.FrontBarOffHand = GearSlot(
        WeaponType="Shield",
        Level="CP160",
        Quality="Gold",
    )
    build.BackBarWeapon = GearSlot(
        WeaponType="Mace",
        Level="CP160",
        Quality="Gold",
    )
    build.BackBarOffHand = GearSlot(
        WeaponType="Shield",
        Level="CP160",
        Quality="Gold",
    )
    return build


def _all_other_damage_channels_zero() -> ExtremeBashDamageInputs:
    return ExtremeBashDamageInputs(
        cp_bash_damage=0.0,
        skill2_bash_damage=0.0,
        physical_damage_done=0.0,
        damage_done=0.0,
        direct_damage_done=0.0,
        single_target_damage_done=0.0,
        skill_bash_damage=0.0,
        set_extra_bash_damage=0.0,
        skill_extra_bash_damage=0.0,
        item_extra_bash_damage=0.0,
    )


def test_full_build_context_supplies_final_resistance_to_bash_formula():
    build = _dual_bar_heavy_build()
    result = ExtremeBashContextObjectiveService.evaluate_build(
        BuildCalculationContextFactory(),
        character_id="character",
        build_id="bash",
        build=build,
        progression=CharacterProgression(
            owned_skill_lines=("One Hand and Shield", "Heavy Armor"),
        ),
        inputs=_all_other_damage_channels_zero(),
    )

    assert result.physical_resistance is not None
    assert result.spell_resistance is not None
    assert result.physical_resistance > 0
    assert result.spell_resistance > 0
    assert result.reviewed_value == pytest.approx(
        calculate_bash_damage(
            spell_resist=result.spell_resistance,
            physical_resist=result.physical_resistance,
        )
    )
    assert result.objective.objective.legality_blockers == ()
    assert result.context_blockers == ()
    assert result.mechanic_complete is True


def test_defending_weapon_resistance_changes_bash_value_through_context_pipeline():
    defending = _dual_bar_heavy_build()
    plain = _dual_bar_heavy_build()
    plain.FrontBarWeapon.Trait = ""

    kwargs = dict(
        factory=BuildCalculationContextFactory(),
        character_id="character",
        build_id="bash",
        progression=CharacterProgression(
            owned_skill_lines=("One Hand and Shield", "Heavy Armor"),
        ),
        inputs=_all_other_damage_channels_zero(),
    )
    defending_result = ExtremeBashContextObjectiveService.evaluate_build(
        build=defending,
        **kwargs,
    )
    plain_result = ExtremeBashContextObjectiveService.evaluate_build(
        build=plain,
        **kwargs,
    )

    assert defending_result.physical_resistance > plain_result.physical_resistance
    assert defending_result.spell_resistance > plain_result.spell_resistance
    assert defending_result.reviewed_value > plain_result.reviewed_value


def test_legacy_one_hand_and_shield_saved_shape_is_still_legal_on_both_bars():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="One Hand and Shield"),
        BackBarWeapon=GearSlot(WeaponType="One Hand and Shield"),
    )

    legality = ExtremeBashContextObjectiveService.legality_for_build(build)

    assert legality.dual_bar_one_hand_and_shield is True
    assert legality.blockers() == ()


def test_context_unresolved_effects_block_complete_bash_claim():
    build = _dual_bar_heavy_build()
    factory = BuildCalculationContextFactory()
    context = factory.build(
        character_id="character",
        build_id="bash",
        build=build,
        progression=CharacterProgression(
            owned_skill_lines=("One Hand and Shield", "Heavy Armor"),
        ),
    )
    context = replace(
        context,
        unresolved_gear_effects=("mystery resistance-capable effect",),
    )

    result = ExtremeBashContextObjectiveService.evaluate_context(
        context,
        _all_other_damage_channels_zero(),
        legality=ExtremeBashContextObjectiveService.legality_for_build(build),
    )

    assert result.context_blockers == (
        "Build context: mystery resistance-capable effect",
    )
    assert result.mechanic_complete is False


def test_context_resistance_cannot_be_double_supplied():
    build = _dual_bar_heavy_build()
    context = BuildCalculationContextFactory().build(
        character_id="character",
        build_id="bash",
        build=build,
        progression=CharacterProgression(),
    )

    with pytest.raises(ValueError, match="supplied directly and through BuildCalculationContext"):
        ExtremeBashContextObjectiveService.evaluate_context(
            context,
            replace(_all_other_damage_channels_zero(), physical_resist=1000.0),
        )
