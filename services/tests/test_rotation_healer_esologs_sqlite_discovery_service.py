import sqlite3

from services.rotation_healer_esologs_sqlite_discovery_service import (
    RotationHealerEsoLogsSqliteDiscoveryService,
)


def _database(tmp_path):
    path = tmp_path / "logs.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE log_actor (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                guid INTEGER,
                name TEXT,
                display_name TEXT,
                actor_type TEXT,
                role TEXT,
                anonymous INTEGER,
                raw_json TEXT NOT NULL
            );
            CREATE TABLE log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                event_index INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source_id INTEGER,
                source_is_friendly INTEGER,
                target_id INTEGER,
                target_instance INTEGER,
                target_is_friendly INTEGER,
                ability_game_id INTEGER,
                extra_ability_game_id INTEGER,
                amount REAL,
                hit_type INTEGER,
                tick INTEGER,
                cast_track_id INTEGER,
                resource_change REAL,
                resource_change_type INTEGER,
                other_resource_change REAL,
                max_resource_amount REAL,
                waste REAL,
                overheal REAL,
                absorbed REAL,
                stack INTEGER,
                raw_json TEXT NOT NULL
            );
            """
        )
        db.execute(
            "INSERT INTO log_actor VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("ABC", 4, 7, None, "Magrat", "@Jarakeen", "Player", "healer", 0, "{}"),
        )
        db.execute(
            "INSERT INTO log_actor VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("ABC", 4, 8, None, "Tank", "@Tank", "Player", "tank", 0, "{}"),
        )
        rows = [
            ("ABC", 4, 1, 1000.0, "cast", 7, 1, None, None, None, 93807, None, None, None, 0, None, None, None, None, None, None, None, None, None, "{}"),
            ("ABC", 4, 2, 2000.0, "hot", 7, 1, 3, None, 1, 93807, None, 100.0, None, 1, None, None, None, None, None, None, 0.0, None, None, "{}"),
            ("ABC", 5, 1, 3000.0, "damage", 8, 1, 99, None, 0, 1, None, 50.0, None, 0, None, None, None, None, None, None, None, None, None, "{}"),
        ]
        db.executemany(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
    return path


def test_discovers_fights_healer_and_target_hot(tmp_path):
    report = RotationHealerEsoLogsSqliteDiscoveryService().inspect(_database(tmp_path))

    assert report.has_log_event
    assert report.has_log_actor
    assert [(item.report_code, item.fight_id, item.event_count) for item in report.fights] == [
        ("ABC", 4, 2),
        ("ABC", 5, 1),
    ]
    assert len(report.healers) == 1
    healer = report.healers[0]
    assert healer.actor_id == 7
    assert healer.display_name == "@Jarakeen"
    assert healer.target_ability_names == ("Budding Seeds",)
    assert report.unresolved == ()


def test_missing_log_event_fails_closed_without_querying_it(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE something_else(id INTEGER)")

    report = RotationHealerEsoLogsSqliteDiscoveryService().inspect(path)

    assert not report.has_log_event
    assert report.fights == ()
    assert report.healers == ()
    assert report.unresolved == ("log_event table is unavailable",)


def test_missing_log_actor_keeps_fight_discovery(tmp_path):
    path = tmp_path / "events_only.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE log_event (
                report_code TEXT, fight_id INTEGER, event_index INTEGER,
                timestamp REAL, event_type TEXT, source_id INTEGER,
                ability_game_id INTEGER, tick INTEGER, raw_json TEXT
            );
            INSERT INTO log_event VALUES ('R', 1, 0, 1000, 'heal', 5, 93807, 1, '{}');
            """
        )

    report = RotationHealerEsoLogsSqliteDiscoveryService().inspect(path)

    assert report.has_log_event
    assert not report.has_log_actor
    assert len(report.fights) == 1
    assert report.healers == ()
    assert "log_actor table is unavailable" in report.unresolved
