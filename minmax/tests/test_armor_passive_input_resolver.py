import pytest

from minmax.armor_passive_input_resolver import ArmorPassiveInputResolver
from minmax.gear_stat_inputs import GearCalculationInputs
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
    assert any("Critical Healing" in message for message in result.unresolved)


def test_equipped_weight_does_not_apply_passives_without_ownership():
    original = GearCalculationInputs()
    result = ArmorPassiveInputResolver().apply(original, _six_light_one_medium())
    assert result == original


def test_light_and_medium_ownership_are_independent():
    build = _six_light_one_medium()

    light_only = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        light_armor_passives_owned=True,
    )
    assert light_only.magicka_recovery.skill_percent_contributions
    assert not light_only.stamina_recovery.skill_percent_contributions
    assert not light_only.core.weapon_damage.percent

    medium_only = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        medium_armor_passives_owned=True,
    )
    assert not medium_only.magicka_recovery.skill_percent_contributions
    assert medium_only.stamina_recovery.skill_percent_contributions
    assert medium_only.core.weapon_damage.percent
