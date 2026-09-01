import pytest

from minmax.armor_passive_input_resolver import ArmorPassiveInputResolver
from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


def _six_light_one_medium() -> PlayerBuild:
    build = PlayerBuild()
    weights = {
        "Head": "Medium",
        "Shoulders": "Light",
        "Chest": "Light",
        "Hands": "Light",
        "Waist": "Light",
        "Legs": "Light",
        "Feet": "Light",
    }
    for slot, weight in weights.items():
        build.Armor[slot]["Weight"] = weight
    return build


def _five_heavy_two_light() -> PlayerBuild:
    build = PlayerBuild()
    weights = {
        "Head": "Heavy",
        "Shoulders": "Light",
        "Chest": "Heavy",
        "Hands": "Heavy",
        "Waist": "Light",
        "Legs": "Heavy",
        "Feet": "Heavy",
    }
    for slot, weight in weights.items():
        build.Armor[slot]["Weight"] = weight
    return build


def test_six_light_one_medium_applies_verified_owned_armor_passives():
    result = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        _six_light_one_medium(),
        light_armor_passives_owned=True,
        medium_armor_passives_owned=True,
    )

    assert result.magicka_recovery.skill_percent_contributions[-1].label == "Light Armor: Evocation"
    assert result.magicka_recovery.skill_percent_contributions[-1].value == pytest.approx(0.24)
    assert result.stamina_recovery.skill_percent_contributions[-1].label == "Medium Armor: Wind Walker"
    assert result.stamina_recovery.skill_percent_contributions[-1].value == pytest.approx(0.04)
    assert result.core.physical_penetration.flat[-1].label == "Light Armor: Concentration"
    assert result.core.physical_penetration.flat[-1].value == 5634.0
    assert result.core.spell_penetration.flat[-1].value == 5634.0
    assert result.core.spell_resistance.flat[-1].label == "Light Armor: Spell Warding"
    assert result.core.spell_resistance.flat[-1].value == 4356.0
    assert result.core.physical_resistance.flat == ()
    assert result.core.weapon_critical.flat[-1].label == "Light Armor: Prodigy"
    assert result.core.weapon_critical.flat[-1].value == pytest.approx(1314.0 / 21912.0)
    assert result.core.spell_critical.flat[-1].value == pytest.approx(1314.0 / 21912.0)
    assert result.core.weapon_damage.percent[-1].label == "Medium Armor: Agility"
    assert result.core.weapon_damage.percent[-1].value == pytest.approx(0.02)
    assert result.core.spell_damage.percent[-1].value == pytest.approx(0.02)
    assert result.core.critical_damage.additive_after_percent[-1].label == "Medium Armor: Dexterity (Critical Damage)"
    assert result.core.critical_damage.additive_after_percent[-1].value == pytest.approx(0.02)
    assert result.core.critical_healing.additive_after_percent[-1].label == "Medium Armor: Dexterity (Critical Healing)"
    assert result.core.critical_healing.additive_after_percent[-1].value == pytest.approx(0.02)
    assert [m.percent for m in result.core.block_cost.sequential_modifiers] == pytest.approx([0.18, -0.03])


def test_equipped_weight_applies_only_inherent_armor_rules_without_purchased_passives():
    result = ArmorPassiveInputResolver().apply(GearCalculationInputs(), _six_light_one_medium())

    assert [m.percent for m in result.core.block_cost.sequential_modifiers] == pytest.approx([0.18, -0.03])
    assert not result.magicka_recovery.skill_percent_contributions
    assert not result.stamina_recovery.skill_percent_contributions
    assert not result.core.physical_penetration.flat
    assert not result.core.weapon_damage.percent
    assert not result.core.critical_healing.additive_after_percent


def test_light_and_medium_purchased_passives_are_independent():
    build = _six_light_one_medium()

    light_only = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        light_armor_passives_owned=True,
    )
    assert light_only.magicka_recovery.skill_percent_contributions
    assert not light_only.stamina_recovery.skill_percent_contributions
    assert not light_only.core.weapon_damage.percent
    assert not light_only.core.critical_healing.additive_after_percent
    assert [m.percent for m in light_only.core.block_cost.sequential_modifiers] == pytest.approx([0.18, -0.03])

    medium_only = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        medium_armor_passives_owned=True,
    )
    assert not medium_only.magicka_recovery.skill_percent_contributions
    assert medium_only.stamina_recovery.skill_percent_contributions
    assert medium_only.core.weapon_damage.percent
    assert medium_only.core.critical_healing.additive_after_percent
    assert [m.percent for m in medium_only.core.block_cost.sequential_modifiers] == pytest.approx([0.18, -0.03])


def test_heavy_armor_inherent_block_mitigation_does_not_require_purchased_passive():
    result = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        _five_heavy_two_light(),
    )

    assert result.core.block_mitigation.direct_points == (
        ("Heavy Armor: Block Mitigation Bonus", 0.05),
    )


def test_context_factory_legacy_skill_line_ownership_still_drives_legacy_passive_path():
    build = _six_light_one_medium()
    progression = CharacterProgression(owned_skill_lines=("Light Armor", "Medium Armor"))

    context = BuildCalculationContextFactory().build(
        character_id="character",
        build_id="build",
        build=build,
        progression=progression,
    )

    assert context.character_state.magicka_recovery == 638
    assert context.character_state.stamina_recovery == 535
    assert context.core_state.derived[StatId.PHYSICAL_PENETRATION].final_value == 5634
    assert context.core_state.derived[StatId.SPELL_PENETRATION].final_value == 5634
    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1020
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1020
    assert context.core_state.derived[StatId.CRITICAL_DAMAGE].final_value == pytest.approx(0.52)
    assert context.core_state.derived[StatId.CRITICAL_HEALING].final_value == pytest.approx(0.02)
    assert context.core_state.derived[StatId.BLOCK_COST].final_value == 2004


def test_context_factory_inherent_heavy_armor_block_mitigation_needs_no_skill_line_flag():
    build = _five_heavy_two_light()
    context = BuildCalculationContextFactory().build(
        character_id="character",
        build_id="build",
        build=build,
        progression=CharacterProgression(),
    )

    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.55)


def test_context_factory_does_not_infer_purchased_armor_passives_from_equipment():
    build = _six_light_one_medium()

    context = BuildCalculationContextFactory().build(
        character_id="character",
        build_id="build",
        build=build,
        progression=CharacterProgression(),
    )

    assert context.character_state.magicka_recovery == 514
    assert context.character_state.stamina_recovery == 514
    assert context.core_state.derived[StatId.PHYSICAL_PENETRATION].final_value == 0
    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1000
    assert context.core_state.derived[StatId.CRITICAL_HEALING].final_value == 0
    assert context.core_state.derived[StatId.BLOCK_COST].final_value == 2004
