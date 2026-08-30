from models.build_model import PlayerBuild

from minmax.build_calculation_context import CombatEnvironment
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId


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
    assert context.core_state is not None
    assert context.core_state.derived[StatId.CRITICAL_CHANCE].final_value == 0.10
    assert context.core_state.derived[StatId.CRITICAL_DAMAGE].final_value == 0.50
    assert context.core_state.derived[StatId.CRITICAL_RESISTANCE].final_value == 1320
    assert context.selected_skills == ("Healing Seed", "Illustrious Healing", "Budding Seeds")


def test_factory_resolves_racial_stats_when_repository_is_supplied(tmp_path):
    database = tmp_path / "races.db"
    import sqlite3

    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE race (id INTEGER PRIMARY KEY, name TEXT, alliance TEXT, association TEXT);
            CREATE TABLE race_stat (id INTEGER PRIMARY KEY, race_id INTEGER, stat TEXT, value REAL);
            INSERT INTO race VALUES (1, 'Breton', 'Daggerfall Covenant', 'Breton');
            INSERT INTO race_stat VALUES (1, 1, 'max_magicka', 2000);
            INSERT INTO race_stat VALUES (2, 1, 'magicka_recovery', 130);
            INSERT INTO race_stat VALUES (3, 1, 'spell_resistance', 2310);
            """
        )

    build = PlayerBuild(Race="Breton")
    progression = CharacterProgression(attributes=AttributeAllocation(magicka=64))
    factory = BuildCalculationContextFactory(race_repository=RaceRepository(database))

    context = factory.build(
        character_id="breton-1",
        build_id="build-1",
        build=build,
        progression=progression,
    )

    assert context.character_state.max_magicka == 21104
    assert context.character_state.magicka_recovery == 644
    assert context.core_state is not None
    assert context.core_state.derived[StatId.SPELL_RESISTANCE].final_value == 2310


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
