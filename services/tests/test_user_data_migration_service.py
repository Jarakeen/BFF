from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.achievement_progress_service import AchievementProgressService
from services.user_data_migration_service import migrate_legacy_user_data


def _legacy_database(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE roster_member (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                character_name TEXT,
                eso_class TEXT,
                primary_role TEXT,
                secondary_role TEXT,
                status TEXT NOT NULL DEFAULT 'Active'
            );
            CREATE TABLE team (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE team_member (
                roster_member_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                PRIMARY KEY (roster_member_id, team_id)
            );
            CREATE TABLE collectible_progress (
                collectible_id INTEGER PRIMARY KEY,
                owned INTEGER NOT NULL DEFAULT 0,
                acquired_on TEXT,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        db.execute(
            "INSERT INTO roster_member(id, player_name, status) VALUES (1, 'Rikbacon', 'Active')"
        )
        db.execute("INSERT INTO team(id, name) VALUES (1, 'Performance Mode')")
        db.execute("INSERT INTO team_member(roster_member_id, team_id) VALUES (1, 1)")
        db.execute(
            "INSERT INTO collectible_progress(collectible_id, owned, notes) VALUES (42, 1, 'owned')"
        )
        db.commit()
    finally:
        db.close()


def test_legacy_user_state_is_copied_without_mutating_source(tmp_path: Path) -> None:
    legacy = tmp_path / "eso.db"
    target = tmp_path / "foundrydock.db"
    achievements = tmp_path / "achievement_progress.json"
    _legacy_database(legacy)
    achievements.write_text(
        json.dumps(
            {
                "Version": 2,
                "ActiveProfile": "Jarakeen",
                "Profiles": {"Jarakeen": {"Completed": ["100", "200"]}},
            }
        ),
        encoding="utf-8",
    )

    before = legacy.read_bytes()
    counts = migrate_legacy_user_data(
        legacy_database=legacy,
        user_database=target,
        achievement_progress=achievements,
    )

    assert legacy.read_bytes() == before
    assert counts["roster_member"] == 1
    assert counts["team"] == 1
    assert counts["team_member"] == 1
    assert counts["collectible_progress"] == 1
    assert counts["achievement_progress"] == 2

    db = sqlite3.connect(target)
    try:
        assert db.execute("SELECT player_name FROM roster_member").fetchone()[0] == "Rikbacon"
        assert db.execute("SELECT name FROM team").fetchone()[0] == "Performance Mode"
        assert db.execute(
            "SELECT owned FROM collectible_progress WHERE profile_name='Default' AND collectible_id=42"
        ).fetchone()[0] == 1
    finally:
        db.close()

    progress = AchievementProgressService(target)
    assert progress.active_profile == "Jarakeen"
    assert progress.completed_ids() == {"100", "200"}


def test_migration_is_idempotent_and_existing_user_rows_win(tmp_path: Path) -> None:
    legacy = tmp_path / "eso.db"
    target = tmp_path / "foundrydock.db"
    achievements = tmp_path / "achievement_progress.json"
    _legacy_database(legacy)
    achievements.write_text('{"Completed": ["100"]}', encoding="utf-8")

    migrate_legacy_user_data(
        legacy_database=legacy,
        user_database=target,
        achievement_progress=achievements,
    )

    db = sqlite3.connect(target)
    try:
        db.execute("UPDATE roster_member SET player_name='User Edited' WHERE id=1")
        db.commit()
    finally:
        db.close()

    migrate_legacy_user_data(
        legacy_database=legacy,
        user_database=target,
        achievement_progress=achievements,
    )

    db = sqlite3.connect(target)
    try:
        assert db.execute("SELECT player_name FROM roster_member WHERE id=1").fetchone()[0] == "User Edited"
    finally:
        db.close()
