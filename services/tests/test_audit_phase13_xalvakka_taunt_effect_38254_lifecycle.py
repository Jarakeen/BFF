from pathlib import Path
import sqlite3

from tools.audit_phase13_xalvakka_taunt_effect_38254_lifecycle import audit


def _research_db(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE log_report_actor (
                report_code TEXT NOT NULL,
                actor_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE log_fight (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                name TEXT,
                start_time REAL
            );
            CREATE TABLE log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                event_index INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source_id INTEGER,
                target_id INTEGER,
                target_instance INTEGER,
                ability_game_id INTEGER,
                raw_json TEXT
            );
            """
        )
        db.execute("INSERT INTO log_report_actor VALUES ('r', 104, 'Iron Atronach')")
        db.execute("INSERT INTO log_fight VALUES ('r', 1, 'Xalvakka', 0)")
        rows = [
            ('r', 1, 1, 1000, 'applydebuff', 1, 104, 1, 38254, '{}'),
            ('r', 1, 2, 7000, 'applydebuff', 1, 104, 1, 38254, '{}'),
            ('r', 1, 3, 22000, 'removedebuff', 1, 104, 1, 38254, '{}'),
        ]
        db.executemany("INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
        db.commit()
    finally:
        db.close()


def _game_db(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.execute(
            "CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, name TEXT, raw_description TEXT)"
        )
        db.execute(
            "INSERT INTO ability VALUES (38254, 'Taunt Candidate', 'fixture description')"
        )
        db.commit()
    finally:
        db.close()


def test_audit_pairs_reapplication_and_removal_without_promoting_identity(tmp_path: Path):
    research = tmp_path / 'research.db'
    game = tmp_path / 'game.db'
    _research_db(research)
    _game_db(game)

    lines = audit(research, game)
    text = '\n'.join(lines)

    assert 'GAME_IDENTITY=Taunt Candidate' in text
    assert 'ACTOR_SUMMARY: actor=Iron Atronach instances=1 intervals=2 remove_closed=1 reapply_closed=1 still_open=0' in text
    assert 'DURATION: actor=Iron Atronach samples=2 median=10.500s min=6.000s max=15.000s' in text
    assert 'remains a taunt-state candidate' in text
