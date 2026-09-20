from __future__ import annotations

from pathlib import Path
import sqlite3

from tools.build_release_database_seed import create_release_database_seed


def _seed_source(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE ability (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            INSERT INTO ability(id, name) VALUES (1, 'Combat Prayer');

            CREATE TABLE roster_member (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL
            );
            INSERT INTO roster_member(player_name) VALUES ('Jarakeen');

            CREATE TABLE team (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );
            INSERT INTO team(name) VALUES ('Performance Mode');

            CREATE TABLE roster_player_alias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roster_member_id INTEGER NOT NULL,
                alias TEXT NOT NULL
            );
            INSERT INTO roster_player_alias(roster_member_id, alias)
            VALUES (1, 'Jara');

            CREATE TABLE generated_roster_draft (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );
            INSERT INTO generated_roster_draft(name) VALUES ('GS');

            CREATE TABLE collectible_profile (
                profile_name TEXT PRIMARY KEY
            );
            INSERT INTO collectible_profile(profile_name) VALUES ('Jarakeen');

            CREATE TABLE collectible_progress (
                profile_name TEXT NOT NULL,
                collectible_id INTEGER NOT NULL,
                owned INTEGER NOT NULL
            );
            INSERT INTO collectible_progress VALUES ('Jarakeen', 42, 1);

            CREATE TABLE stickerbook_progress (
                profile_id TEXT NOT NULL,
                set_id INTEGER NOT NULL,
                piece_key TEXT NOT NULL,
                collected INTEGER NOT NULL
            );
            INSERT INTO stickerbook_progress VALUES ('Jarakeen', 7, '7:1:1:0', 1);

            CREATE TABLE log_report (
                report_code TEXT PRIMARY KEY,
                title TEXT
            );
            INSERT INTO log_report(report_code, title) VALUES ('ABC', 'Private raid');

            CREATE TABLE collectible (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            INSERT INTO collectible(id, name) VALUES (42, 'Reference Collectible');
            """
        )
        db.commit()


def test_release_database_seed_removes_user_state_and_preserves_reference_data(tmp_path: Path) -> None:
    source = tmp_path / "live.db"
    destination = tmp_path / "release.db"
    _seed_source(source)

    cleared = create_release_database_seed(source, destination)

    assert "roster_member" in cleared
    assert "team" in cleared
    assert "roster_player_alias" in cleared
    assert "generated_roster_draft" in cleared
    assert "collectible_profile" in cleared
    assert "collectible_progress" in cleared
    assert "stickerbook_progress" in cleared
    assert "log_report" in cleared

    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT COUNT(*) FROM roster_member").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM team").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM roster_player_alias").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM generated_roster_draft").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collectible_profile").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM collectible_progress").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM stickerbook_progress").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM log_report").fetchone()[0] == 0

        assert db.execute("SELECT name FROM ability WHERE id=1").fetchone()[0] == "Combat Prayer"
        assert db.execute("SELECT name FROM collectible WHERE id=42").fetchone()[0] == "Reference Collectible"

        roster_schema = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='roster_member'"
        ).fetchone()
        assert roster_schema is not None


def test_release_database_seed_does_not_modify_live_source(tmp_path: Path) -> None:
    source = tmp_path / "live.db"
    destination = tmp_path / "release.db"
    _seed_source(source)

    create_release_database_seed(source, destination)

    with sqlite3.connect(source) as db:
        assert db.execute("SELECT player_name FROM roster_member").fetchone()[0] == "Jarakeen"
        assert db.execute("SELECT name FROM team").fetchone()[0] == "Performance Mode"
        assert db.execute("SELECT report_code FROM log_report").fetchone()[0] == "ABC"
