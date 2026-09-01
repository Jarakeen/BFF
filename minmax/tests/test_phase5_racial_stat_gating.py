import sqlite3

from models.build_model import PlayerBuild
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.race_repository import RaceRepository


def _race_db(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE race (id INTEGER PRIMARY KEY, name TEXT, alliance TEXT, association TEXT);
            CREATE TABLE race_stat (id INTEGER PRIMARY KEY, race_id INTEGER, stat TEXT, value REAL);
            INSERT INTO race VALUES (1, 'Breton', 'Daggerfall Covenant', 'Breton');
            INSERT INTO race_stat VALUES (1, 1, 'max_magicka', 2000);
            INSERT INTO race_stat VALUES (2, 1, 'magicka_recovery', 130);
            """
        )


def test_phase5_explicit_progression_does_not_assume_aggregate_racial_stats(tmp_path):
    database = tmp_path / "races.db"
    _race_db(database)
    factory = Phase5BuildCalculationContextFactory(race_repository=RaceRepository(database))
    build = PlayerBuild(Race="Breton")
    progression = CharacterProgression(
        attributes=AttributeAllocation(magicka=64),
        passive_ranks={},
    )

    context = factory.build(
        character_id="breton-1",
        build_id="build-1",
        build=build,
        progression=progression,
    )

    assert context.character_state.max_magicka == 19104
    assert context.character_state.magicka_recovery == 514
    assert context.unresolved_gear_effects == (
        "Racial aggregate stats are not applied because individual racial passive ownership cannot be resolved from canonical data: Breton",
    )


def test_phase5_legacy_progression_keeps_aggregate_racial_stats(tmp_path):
    database = tmp_path / "races.db"
    _race_db(database)
    factory = Phase5BuildCalculationContextFactory(race_repository=RaceRepository(database))
    build = PlayerBuild(Race="Breton")
    progression = CharacterProgression(
        attributes=AttributeAllocation(magicka=64),
        passive_ranks=None,
    )

    context = factory.build(
        character_id="breton-1",
        build_id="build-1",
        build=build,
        progression=progression,
    )

    assert context.character_state.max_magicka == 21104
    assert context.character_state.magicka_recovery == 644
    assert context.unresolved_gear_effects == ()
