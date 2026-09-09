import sqlite3

from services.rotation_healer_esologs_sqlite_family_match_service import (
    RotationHealerEsoLogsSqliteFamilyMatchService,
)


def _canonical_db(tmp_path):
    path = tmp_path / "canonical.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (id INTEGER PRIMARY KEY, base_ability_id INTEGER, name TEXT);
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            );
            INSERT INTO skill VALUES (1, 1, 'Budding Seeds');
            INSERT INTO skill_rank VALUES (10, 1, 93807, 'Budding Seeds', 4, 1);
            INSERT INTO skill VALUES (2, 2, 'Radiating Regeneration');
            INSERT INTO skill_rank VALUES (20, 2, 40079, 'Radiating Regeneration', 1, 1);
            INSERT INTO skill_rank VALUES (21, 2, 41288, 'Radiating Regeneration', 4, 1);
            INSERT INTO skill VALUES (3, 3, 'Illustrious Healing');
            INSERT INTO skill_rank VALUES (30, 3, 41255, 'Illustrious Healing', 4, 1);
            INSERT INTO skill VALUES (4, 4, 'Energy Orb');
            INSERT INTO skill_rank VALUES (40, 4, 43447, 'Energy Orb', 4, 1);
            INSERT INTO skill VALUES (5, 5, 'Echoing Vigor');
            INSERT INTO skill_rank VALUES (50, 5, 63247, 'Echoing Vigor', 4, 1);
            """
        )
    return path


def _log_db(tmp_path):
    path = tmp_path / "logs.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE log_actor (
                report_code TEXT, fight_id INTEGER, actor_id INTEGER,
                name TEXT, display_name TEXT, role TEXT
            );
            CREATE TABLE log_event (
                report_code TEXT, fight_id INTEGER, event_index INTEGER,
                timestamp REAL, event_type TEXT, source_id INTEGER,
                ability_game_id INTEGER, tick INTEGER
            );
            INSERT INTO log_actor VALUES ('R', 6, 7, 'Healer', '@Healer', 'healer');
            INSERT INTO log_event VALUES ('R', 6, 1, 1000, 'cast', 7, 40079, 0);
            INSERT INTO log_event VALUES ('R', 6, 2, 3000, 'heal', 7, 40079, 1);
            INSERT INTO log_event VALUES ('R', 6, 3, 5000, 'heal', 7, 40079, 1);
            """
        )
    return path


def test_matches_historical_rank_id_to_current_skill_family(tmp_path):
    report = RotationHealerEsoLogsSqliteFamilyMatchService().inspect(
        _log_db(tmp_path),
        _canonical_db(tmp_path),
    )

    radiating = [item for item in report.matches if item.source_name == 'Radiating Regeneration']
    assert len(radiating) == 1
    assert radiating[0].matched_ability_ids == (40079,)
    assert radiating[0].event_count == 3
    assert radiating[0].periodic_event_count == 2
    assert report.unresolved == ()


def test_missing_target_families_are_reported(tmp_path):
    canonical = tmp_path / 'empty_canonical.db'
    with sqlite3.connect(canonical) as db:
        db.executescript(
            """
            CREATE TABLE skill (id INTEGER PRIMARY KEY, base_ability_id INTEGER, name TEXT);
            CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER, ability_id INTEGER, raw_name TEXT);
            """
        )

    report = RotationHealerEsoLogsSqliteFamilyMatchService().inspect(
        _log_db(tmp_path),
        canonical,
    )

    assert report.matches == ()
    assert len(report.unresolved) == 5
