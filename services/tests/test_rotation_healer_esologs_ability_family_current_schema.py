import sqlite3

from services.rotation_healer_esologs_ability_family_service import (
    RotationHealerEsoLogsAbilityFamilyService,
)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT
            );

            INSERT INTO skill VALUES (10, 40076, 'Regeneration');

            INSERT INTO skill_rank VALUES (100, 10, 40079, '', 1, 1);
            INSERT INTO skill_rank VALUES (101, 10, 41278, '', 2, 1);
            INSERT INTO skill_rank VALUES (102, 10, 41283, '', 3, 1);
            INSERT INTO skill_rank VALUES (103, 10, 41288, '', 4, 1);

            INSERT INTO skill_rank VALUES (110, 10, 40080, '', 1, 2);
            INSERT INTO skill_rank VALUES (111, 10, 41279, '', 2, 2);

            INSERT INTO ability VALUES (40079, 'Radiating Regeneration');
            INSERT INTO ability VALUES (41278, 'Radiating Regeneration');
            INSERT INTO ability VALUES (41283, 'Radiating Regeneration');
            INSERT INTO ability VALUES (41288, 'Radiating Regeneration');
            INSERT INTO ability VALUES (40080, 'Rapid Regeneration');
            INSERT INTO ability VALUES (41279, 'Rapid Regeneration');
            """
        )
    return path


def test_resolves_name_from_ability_table_when_skill_and_raw_name_do_not_match(tmp_path):
    family = RotationHealerEsoLogsAbilityFamilyService(_database(tmp_path)).resolve(
        "Radiating Regeneration"
    )

    assert family is not None
    assert family.skill_id == 10
    assert family.morph == 1
    assert family.ability_game_ids == (40079, 41278, 41283, 41288)


def test_family_does_not_cross_into_sibling_morph(tmp_path):
    family = RotationHealerEsoLogsAbilityFamilyService(_database(tmp_path)).resolve(
        "Radiating Regeneration"
    )

    assert family is not None
    assert not family.contains(40080)
    assert not family.contains(41279)
