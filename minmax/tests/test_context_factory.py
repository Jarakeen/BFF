from models.build_model import PlayerBuild

from minmax.base_character_state import BaseCharacterCalculator
from minmax.build_calculation_context import CombatEnvironment
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory


def test_factory_builds_context_from_character_and_build():
    build = PlayerBuild(FrontBarSkills=["Healing Seed", "Illustrious Healing", "", "", "", ""], BackBarSkills=["Budding Seeds", "", "", "", "", ""])
    progression = CharacterProgression(attributes=AttributeAllocation(magicka=64))

    context = BuildCalculationContextFactory().build(
        character_id="character-1",
        build_id="build-1",
        build=build,
        progression=progression,
    )

    assert context.character_id == "character-1"
    assert context.build_id == "build-1"
    assert context.progression is progression
    assert context.character_state.max_magicka == 19104
    assert context.selected_skills == ("Healing Seed", "Illustrious Healing", "Budding Seeds")


def test_factory_preserves_explicit_combat_context():
    build = PlayerBuild()
    progression = CharacterProgression()

    context = BuildCalculationContextFactory().build(
        character_id="character-1",
        build_id="build-1",
        build=build,
        progression=progression,
        environment=CombatEnvironment.PVP,
        target_type="player",
        target_count=2,
        target_resistance=33000,
        fight_duration=60,
    )

    assert context.environment is CombatEnvironment.PVP
    assert context.target_type == "player"
    assert context.target_count == 2
    assert context.target_resistance == 33000
    assert context.fight_duration == 60
