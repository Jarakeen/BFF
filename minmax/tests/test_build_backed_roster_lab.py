import sqlite3

from minmax.build_backed_roster_lab import BuildBackedRosterLab
from minmax.character_build.character_class import CharacterClass
from minmax.role import Role


def make_db(path):
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                target TEXT,
                is_player INTEGER DEFAULT 1
            );
            CREATE TABLE effect (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL
            );
            CREATE TABLE effect_variant (
                id INTEGER PRIMARY KEY,
                effect_id INTEGER NOT NULL,
                type TEXT,
                description TEXT
            );
            CREATE TABLE effect_source (
                id INTEGER PRIMARY KEY,
                effect_variant_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                condition TEXT
            );
            CREATE TABLE ability_effect_link (
                id INTEGER PRIMARY KEY,
                effect_source_id INTEGER NOT NULL,
                effect_variant_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                condition TEXT,
                match_method TEXT NOT NULL,
                confidence REAL NOT NULL
            );
            INSERT INTO gear_set VALUES (332, 'Master Architect', 'standard', 5);
            INSERT INTO gear_set_bonus VALUES
                (1490, 332, 2, '(2 items) Adds Maximum Magicka'),
                (1491, 332, 3, '(3 items) Gain Minor Slayer'),
                (1492, 332, 4, '(4 items) Adds Weapon and Spell Damage'),
                (1493, 332, 5, '(5 items) Major Slayer');
            INSERT INTO ability VALUES (101, 'Test Courage', 'Group', 1);
            INSERT INTO effect VALUES (201, 'major_courage', 'buff');
            INSERT INTO effect_variant VALUES (301, 201, 'Major', 'test');
            INSERT INTO effect_source VALUES (401, 301, 'Abilities', 'Test Courage', NULL);
            INSERT INTO ability_effect_link VALUES (501, 401, 301, 101, NULL, 'exact_name', 1.0);
            """
        )


def test_four_pieces_do_not_resolve_five_piece_support_effect(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)
    lab = BuildBackedRosterLab(db)

    player = lab.add_player(
        'Healer 01', Role.HEALER, CharacterClass.WARDEN, 332, 4
    )

    assert player.gear_set_name == 'Master Architect'
    assert player.resolved_effects == ()
    assert player.unsupported_sources


def test_five_pieces_resolve_known_support_effect(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)
    lab = BuildBackedRosterLab(db)

    player = lab.add_player(
        'Healer 01', Role.HEALER, CharacterClass.WARDEN, 332, 5
    )

    assert player.validation_errors == ()
    assert 'major_slayer' in player.resolved_effects
    assert player.unsupported_sources == ()


def test_unknown_set_is_reported_without_guessing(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)
    lab = BuildBackedRosterLab(db)

    player = lab.add_player(
        'DD 01', Role.DD, CharacterClass.NIGHTBLADE, 9999, 5
    )

    assert player.resolved_effects == ()
    assert player.validation_errors


def test_build_backed_capabilities_reach_roster_layer(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)
    lab = BuildBackedRosterLab(db)

    lab.add_player(
        'Healer 01', Role.HEALER, CharacterClass.WARDEN, 332, 5
    )

    capabilities = lab.capabilities()

    assert 'major_slayer' in capabilities
    assert len(capabilities['major_slayer']) == 1
    assert capabilities['major_slayer'][0].character_name == 'Healer 01'


def test_build_backed_roster_can_be_evaluated_even_when_requirements_are_missing(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)
    lab = BuildBackedRosterLab(db)

    lab.add_player(
        'Healer 01', Role.HEALER, CharacterClass.WARDEN, 332, 5
    )

    evaluation = lab.evaluate()

    assert len(evaluation.classifications) == 6
    assert any(result.effect_name == 'major_force' for result in evaluation.problems)


def test_build_backed_player_can_resolve_linked_skill_effect(tmp_path):
    db = tmp_path / 'test.db'
    make_db(db)
    lab = BuildBackedRosterLab(db)

    player = lab.add_player(
        'Healer 01',
        Role.HEALER,
        CharacterClass.WARDEN,
        skill_ids=(101,),
    )

    assert player.validation_errors == ()
    assert player.skills == ((101, 'Test Courage'),)
    assert 'major_courage' in player.resolved_effects
