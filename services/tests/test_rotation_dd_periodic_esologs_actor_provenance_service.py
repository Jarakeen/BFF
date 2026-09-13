import json
import sqlite3

from services.rotation_dd_periodic_esologs_actor_provenance_service import (
    RotationDDPeriodicEsoLogsActorProvenanceService,
)


def _database(path):
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE log_actor (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                name TEXT,
                display_name TEXT,
                actor_type TEXT,
                role TEXT,
                raw_json TEXT NOT NULL
            );
            CREATE TABLE log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                event_index INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source_id INTEGER,
                ability_game_id INTEGER
            );
            """
        )
        db.execute(
            "INSERT INTO log_actor VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "AAA",
                1,
                7,
                "Skeletal Archer",
                None,
                "Pet",
                None,
                json.dumps({"ownerID": 3, "name": "Skeletal Archer"}),
            ),
        )
        db.execute(
            "INSERT INTO log_actor VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "BBB",
                2,
                7,
                "Other Actor",
                None,
                "NPC",
                None,
                json.dumps({"name": "Other Actor"}),
            ),
        )
        db.executemany(
            "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ("AAA", 1, 1, 1000.0, "damage", 7, 21929),
                ("AAA", 1, 2, 3000.0, "damage", 7, 21929),
                ("BBB", 2, 1, 1000.0, "damage", 7, 21929),
            ),
        )
        db.commit()


def test_actor_provenance_keeps_report_fight_actor_identity_separate(tmp_path) -> None:
    database = tmp_path / "logs.db"
    _database(database)

    report = RotationDDPeriodicEsoLogsActorProvenanceService(database).inspect(21929)

    assert report.event_count == 3
    assert report.source_actor_count == 2
    assert report.matched_actor_count == 2
    assert len(report.rows) == 2

    pet = next(row for row in report.rows if row.report_code == "AAA")
    other = next(row for row in report.rows if row.report_code == "BBB")

    assert pet.fight_id == 1
    assert pet.actor_id == 7
    assert pet.event_count == 2
    assert pet.actor_type == "Pet"
    assert pet.owner_hints == ("ownerID=3",)

    assert other.fight_id == 2
    assert other.actor_id == 7
    assert other.event_count == 1
    assert other.actor_type == "NPC"
    assert other.owner_hints == ()
