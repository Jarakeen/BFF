import pytest

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.undaunted_passive_input_resolver import UndauntedPassiveInputResolver
from models.build_model import PlayerBuild


def _two_type_build() -> PlayerBuild:
    build = PlayerBuild(AttributeMagicka=64)
    build.Armor["Head"]["Weight"] = "Medium"
    for slot in ("Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
        build.Armor[slot]["Weight"] = "Light"
    return build


def test_undaunted_mettle_is_four_percent_for_two_equipped_armor_types():
    result = UndauntedPassiveInputResolver().apply(
        GearCalculationInputs(),
        _two_type_build(),
        undaunted_passives_owned=True,
    )

    for resource in (result.health, result.magicka, result.stamina):
        contribution = resource.skill_percent_contributions[-1]
        assert contribution.label == "Undaunted: Undaunted Mettle"
        assert contribution.value == pytest.approx(0.04)


def test_undaunted_mettle_does_not_apply_without_ownership():
    original = GearCalculationInputs()
    assert UndauntedPassiveInputResolver().apply(original, _two_type_build()) == original


def test_undaunted_mettle_counts_distinct_armor_types_not_pieces():
    build = PlayerBuild()
    for slot in build.Armor:
        build.Armor[slot]["Weight"] = "Light"

    result = UndauntedPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        undaunted_passives_owned=True,
    )
    assert result.health.skill_percent_contributions[-1].value == pytest.approx(0.02)

    build.Armor["Head"]["Weight"] = "Medium"
    build.Armor["Chest"]["Weight"] = "Heavy"
    result = UndauntedPassiveInputResolver().apply(
        GearCalculationInputs(),
        build,
        undaunted_passives_owned=True,
    )
    assert result.health.skill_percent_contributions[-1].value == pytest.approx(0.06)


def test_context_factory_uses_character_owned_undaunted_for_final_resources():
    build = _two_type_build()
    progression = CharacterProgression(
        attributes=AttributeAllocation(magicka=64),
        owned_skill_lines=("Undaunted",),
    )

    context = BuildCalculationContextFactory().build(
        character_id="test-character",
        build_id="test-build",
        build=build,
        progression=progression,
    )

    assert context.character_state.max_health == 16640
    assert context.character_state.max_magicka == 19869
    assert context.character_state.max_stamina == 12480
    assert "Undaunted: Undaunted Mettle" in [
        step.label for step in context.character_state.traces[next(
            stat for stat in context.character_state.traces if stat.value == "max_magicka"
        )].steps
    ]
