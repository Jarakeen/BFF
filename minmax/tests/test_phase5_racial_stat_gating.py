import sqlite3

from models.build_model import PlayerBuild
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId


def _race_db(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE race (id INTEGER PRIMARY KEY, name TEXT, alliance TEXT, association TEXT);
            CREATE TABLE race_stat (id INTEGER PRIMARY KEY, race_id INTEGER, stat TEXT, value REAL);
            INSERT INTO race VALUES (1, 'Breton', 'Daggerfall Covenant', 'Breton');
            INSERT INTO race_stat VALUES (1, 1, 'max_magicka', 2000);
            INSERT INTO race_stat VALUES (2, 1, 'magicka_recovery', 130);

            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                skill_line TEXT,
                is_passive INTEGER,
                is_player INTEGER
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                rank INTEGER
            );
            CREATE TABLE ability (
                id INTEGER PRIMARY KEY,
                ability_id INTEGER,
                description TEXT
            );

            INSERT INTO skill VALUES (1, 'Gift of Magnus', 'Breton Skills', 1, 1);
            INSERT INTO skill VALUES (2, 'Spell Attunement', 'Breton Skills', 1, 1);
            INSERT INTO skill VALUES (3, 'Magicka Mastery', 'Breton Skills', 1, 1);
            INSERT INTO skill VALUES (4, 'Opportunist', 'Breton Skills', 1, 1);

            INSERT INTO skill_rank VALUES (1, 1, 101, 1);
            INSERT INTO skill_rank VALUES (2, 1, 102, 2);
            INSERT INTO skill_rank VALUES (3, 1, 103, 3);
            INSERT INTO skill_rank VALUES (4, 2, 201, 1);
            INSERT INTO skill_rank VALUES (5, 2, 202, 2);
            INSERT INTO skill_rank VALUES (6, 2, 203, 3);
            INSERT INTO skill_rank VALUES (7, 3, 301, 1);
            INSERT INTO skill_rank VALUES (8, 3, 302, 2);
            INSERT INTO skill_rank VALUES (9, 3, 303, 3);
            INSERT INTO skill_rank VALUES (10, 4, 401, 1);

            INSERT INTO ability VALUES (1, 101, 'Increases your Max Magicka by |cffffff600|r.');
            INSERT INTO ability VALUES (2, 102, 'Increases your Max Magicka by |cffffff1200|r.');
            INSERT INTO ability VALUES (3, 103, 'Increases your Max Magicka by |cffffff2000|r.');
            INSERT INTO ability VALUES (4, 201, 'Increases your Spell Resistance by |cffffff660|r. This effect is doubled if you are afflicted with Burning, Chilled, or Concussed. Increases your Magicka Recovery by |cffffff40|r.');
            INSERT INTO ability VALUES (5, 202, 'Increases your Spell Resistance by |cffffff1320|r. This effect is doubled if you are afflicted with Burning, Chilled, or Concussed. Increases your Magicka Recovery by |cffffff80|r.');
            INSERT INTO ability VALUES (6, 203, 'Increases your Spell Resistance by |cffffff2310|r. This effect is doubled if you are afflicted with Burning, Chilled, or Concussed. Increases your Magicka Recovery by |cffffff130|r.');
            INSERT INTO ability VALUES (7, 301, 'Reduces the Magicka cost of your abilities by |cffffff2|r%.');
            INSERT INTO ability VALUES (8, 302, 'Reduces the Magicka cost of your abilities by |cffffff4|r%.');
            INSERT INTO ability VALUES (9, 303, 'Reduces the Magicka cost of your abilities by |cffffff7|r%.');
            INSERT INTO ability VALUES (10, 401, 'Increases your experience gain with the Light Armor skill line by |cffffff15|r%. Increases your Alliance Points gained by |cffffff1|r%.');
            """
        )


def test_phase5_explicit_progression_uses_exact_purchased_racial_ranks(tmp_path):
    database = tmp_path / "races.db"
    _race_db(database)
    factory = Phase5BuildCalculationContextFactory(race_repository=RaceRepository(database))
    build = PlayerBuild(Race="Breton")
    progression = CharacterProgression(
        attributes=AttributeAllocation(magicka=64),
        passive_ranks={
            "Gift of Magnus": 2,
            "Spell Attunement": 2,
            "Magicka Mastery": 2,
            "Opportunist": 1,
        },
    )

    context = factory.build(
        character_id="breton-1",
        build_id="build-1",
        build=build,
        progression=progression,
    )

    assert context.character_state.max_magicka == 20304
    assert context.character_state.magicka_recovery == 594
    assert context.core_state.derived[StatId.SPELL_RESISTANCE].final_value == 1320
    assert "Conditional racial passive bonus requires combat-state model: Spell Attunement" in context.unresolved_gear_effects
    assert "Racial ability-cost reduction requires cost-stat model: Magicka Mastery" in context.unresolved_gear_effects
    assert "Non-combat racial passive outside combat capability audit: Opportunist" in context.unresolved_gear_effects


def test_phase5_explicit_zero_racial_ranks_grant_nothing(tmp_path):
    database = tmp_path / "races.db"
    _race_db(database)
    factory = Phase5BuildCalculationContextFactory(race_repository=RaceRepository(database))
    build = PlayerBuild(Race="Breton")
    progression = CharacterProgression(
        attributes=AttributeAllocation(magicka=64),
        passive_ranks={
            "Gift of Magnus": 0,
            "Spell Attunement": 0,
            "Magicka Mastery": 0,
            "Opportunist": 0,
        },
    )

    context = factory.build(
        character_id="breton-1",
        build_id="build-1",
        build=build,
        progression=progression,
    )

    assert context.character_state.max_magicka == 19104
    assert context.character_state.magicka_recovery == 514
    assert context.core_state.derived[StatId.SPELL_RESISTANCE].final_value == 0
    assert context.unresolved_gear_effects == ()


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
