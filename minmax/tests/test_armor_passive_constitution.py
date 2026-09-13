import pytest

from minmax.armor_passive_input_resolver import ArmorPassiveInputResolver
from minmax.gear_stat_inputs import GearCalculationInputs
from models.build_model import PlayerBuild


def _seven_heavy() -> PlayerBuild:
    build = PlayerBuild()
    for entry in build.Armor.values():
        entry["Weight"] = "Heavy"
    return build


def test_constitution_adds_four_percent_health_recovery_per_heavy_piece():
    result = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        _seven_heavy(),
        constitution_owned=True,
    )

    contribution = result.health_recovery.skill_percent_contributions[-1]
    assert contribution.label == "Heavy Armor: Constitution"
    assert contribution.value == pytest.approx(0.28)
    assert result.applied_effect_count == 1


def test_constitution_requires_purchased_passive():
    result = ArmorPassiveInputResolver().apply(
        GearCalculationInputs(),
        _seven_heavy(),
        constitution_owned=False,
    )

    assert result.health_recovery.skill_percent_contributions == ()
