from __future__ import annotations

import sqlite3
from pathlib import Path

from tools.build_custom_user_database_seed import build_seed


def _source_database(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE roster_member (
                id INTEGER PRIMARY KEY,
                player_name TEXT NOT NULL
            );
            CREATE TABLE team (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE team_member (
                roster_member_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                PRIMARY KEY (roster_member_id, team_id)
            );
            CREATE TABLE roster_member_assignment (
                roster_member_id INTEGER PRIMARY KEY,
                primary_assignment TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE raid_plan (
                plan_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE build_catalog (
                singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE achievement_progress (
                profile_name TEXT NOT NULL,
                achievement_id TEXT NOT NULL
            );
            CREATE TABLE collectible_progress (
                profile_name TEXT NOT NULL,
                collectible_id INTEGER NOT NULL,
                owned INTEGER NOT NULL
            );
            """
        )
        db.execute("INSERT INTO roster_member VALUES (1, 'Rikbacon')")
        db.execute("INSERT INTO team VALUES (1, 'Performance Mode')")
        db.execute("INSERT INTO team_member VALUES (1, 1)")
        db.execute("INSERT INTO roster_member_assignment VALUES (1, 'Main Tank')")
        db.execute(
            "INSERT INTO build_catalog(singleton_id, payload_json) VALUES (1, ?)",
            (
                '{"schema_version":4,"players":[{"player_id":"p1","gamertag":"Rikbacon"},{"player_id":"p2","gamertag":"Other"}],'
                '"characters":[{"character_id":"c1","player_id":"p1","name":"Tanky","gamertag":"Rikbacon"},'
                '{"character_id":"c2","player_id":"p2","name":"Other","gamertag":"Other"}],'
                '"builds":[{"build_id":"b1","character_id":"c1","name":"MT"},'
                '{"build_id":"b2","character_id":"c2","name":"Other"}],"team_assignments":[]}'
            ),
        )
        db.execute(
            "INSERT INTO raid_plan(plan_id, payload_json) VALUES (?, ?)",
            (
                "pm-rg",
                '{"plan_id":"pm-rg","members":[{"seat_id":"tank-1","gamertag":"Rikbacon",'
                '"player_id":"p1","character_id":"c1","selected_build_id":"b1","selected_build_name":"MT"}]}',
            ),
        )
        db.execute("INSERT INTO achievement_progress VALUES ('Default', '100')")
        db.execute("INSERT INTO collectible_progress VALUES ('Default', 42, 1)")
        db.commit()
    finally:
        db.close()


def test_custom_exe_seed_keeps_raid_setup_and_drops_collection_progress(tmp_path: Path) -> None:
    source = tmp_path / "foundrydock.db"
    target = tmp_path / "seed.db"
    _source_database(source)

    counts = build_seed(source, target)

    assert counts["roster_member"] == 1
    assert counts["team"] == 1
    assert counts["team_member"] == 1
    assert counts["roster_member_assignment"] == 1
    assert counts["raid_plan"] == 1
    assert counts["build_catalog"] == 1

    db = sqlite3.connect(target)
    try:
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "roster_member" in tables
        assert "team" in tables
        assert "team_member" in tables
        assert "roster_member_assignment" in tables
        assert "raid_plan" in tables
        assert "build_catalog" in tables
        import json
        catalog = json.loads(
            db.execute(
                "SELECT payload_json FROM build_catalog WHERE singleton_id=1"
            ).fetchone()[0]
        )
        assert [row["build_id"] for row in catalog["builds"]] == ["b1"]
        assert [row["character_id"] for row in catalog["characters"]] == ["c1"]
        assert "achievement_progress" not in tables
        assert "collectible_progress" not in tables
    finally:
        db.close()


def test_custom_exe_seed_requires_plan_selection_when_multiple_plans_exist(tmp_path: Path) -> None:
    import pytest

    source = tmp_path / "foundrydock.db"
    target = tmp_path / "seed.db"
    _source_database(source)
    db = sqlite3.connect(source)
    try:
        db.execute(
            "INSERT INTO raid_plan(plan_id, payload_json) VALUES (?, ?)",
            ("other-plan", '{"plan_id":"other-plan"}'),
        )
        db.commit()
    finally:
        db.close()

    with pytest.raises(ValueError, match="multiple saved Raid Plans"):
        build_seed(source, target)

    counts = build_seed(source, target, plan_id="pm-rg")
    assert counts["raid_plan"] == 1
    db = sqlite3.connect(target)
    try:
        rows = db.execute("SELECT plan_id FROM raid_plan").fetchall()
        assert rows == [("pm-rg",)]
    finally:
        db.close()
