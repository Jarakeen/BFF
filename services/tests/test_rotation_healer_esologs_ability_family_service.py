import sqlite3

from services.rotation_healer_esologs_ability_family_service import (
    RotationHealerEsoLogsAbilityFamilyService,
)


def _canonical_db(tmp_path):
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
            INSERT INTO skill VALUES (10, 40076, 'Radiating Regeneration');
            INSERT INTO skill_rank VALUES (100, 10, 40079, 'Radiating Regeneration', 1, 1);
            INSERT INTO skill_rank VALUES (101, 10, 41278, 'Radiating Regeneration', 2, 1);
            INSERT INTO skill_rank VALUES (102, 10, 41283, 'Radiating Regeneration', 3, 1);
            INSERT INTO skill_rank VALUES (103, 10, 41288, 'Radiating Regeneration', 4, 1);
            """
        )
    return path


def test_resolves_all_rank_ability_ids_for_named_skill_family(tmp_path):
    family = RotationHealerEsoLogsAbilityFamilyService(_canonical_db(tmp_path)).resolve(
        "Radiating Regeneration"
    )

    assert family is not None
    assert family.skill_id == 10
    assert family.ability_game_ids == (40079, 41278, 41283, 41288)
    assert family.contains(40079)
    assert family.contains(41288)


def test_unknown_skill_family_fails_closed(tmp_path):
    assert (
        RotationHealerEsoLogsAbilityFamilyService(_canonical_db(tmp_path)).resolve(
            "Not A Real Skill"
        )
        is None
    )
