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
            "INSERT INTO raid_plan(plan_id, payload_json) VALUES ('pm-rg', '{"plan_id":"pm-rg"}')"
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
        assert "achievement_progress" not in tables
        assert "collectible_progress" not in tables
    finally:
        db.close()
