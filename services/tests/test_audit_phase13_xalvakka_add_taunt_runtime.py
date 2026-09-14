from pathlib import Path
import sqlite3

import tools.audit_phase13_xalvakka_add_taunt_runtime as audit_module
from tools.audit_phase13_xalvakka_add_taunt_runtime import CanonicalTauntAbility, audit


def _research_db(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE log_report_actor (
                report_code TEXT,
                actor_id INTEGER,
                name TEXT
            );
            CREATE TABLE log_fight (
                report_code TEXT,
                fight_id INTEGER,
                name TEXT,
                start_time REAL
            );
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
                event_index INTEGER,
                timestamp REAL,
                event_type TEXT,
                source_id INTEGER,
                source_is_friendly INTEGER,
                target_id INTEGER,
                target_instance INTEGER,
                target_is_friendly INTEGER,
                ability_game_id INTEGER
            );
            """
        )
        db.execute(
            "INSERT INTO log_report_actor VALUES ('R', 104, 'Iron Atronach')"
        )
        db.execute(
            "INSERT INTO log_report_actor VALUES ('R', 112, 'Daedroth')"
        )
        db.execute(
            "INSERT INTO log_fight VALUES ('R', 34, 'Xalvakka', 100000.0)"
        )
        db.execute(
            "INSERT INTO log_event VALUES ('R', 34, 1, 118000.0, 'cast', 7, 1, 104, 1, 0, 999)"
        )
        db.execute(
            "INSERT INTO log_event VALUES ('R', 34, 2, 119000.0, 'damage', 7, 1, 104, 1, 0, 123)"
        )
        db.commit()
    finally:
        db.close()


def test_audit_matches_only_canonical_taunt_ids_against_named_add_instances(tmp_path, monkeypatch):
    research = tmp_path / "research.db"
    game = tmp_path / "game.db"
    _research_db(research)
    game.touch()
    monkeypatch.setattr(
        audit_module,
        "canonical_taunt_abilities",
        lambda _path: (CanonicalTauntAbility(ability_id=999, skill_name="Pierce Armor"),),
    )

    lines = audit(research, game)

    assert any(
        "TAUNT_EVENT:" in line
        and "actor=Iron Atronach" in line
        and "instance=1" in line
        and "ability=Pierce Armor" in line
        for line in lines
    )
    assert "OBSERVED_TAUNT_EVENTS=1" in lines
    assert "TAUNTED_ADD_INSTANCES=1" in lines


def test_audit_fails_closed_when_canonical_taunt_catalog_is_empty(tmp_path, monkeypatch):
    research = tmp_path / "research.db"
    game = tmp_path / "game.db"
    _research_db(research)
    game.touch()
    monkeypatch.setattr(audit_module, "canonical_taunt_abilities", lambda _path: ())

    assert audit(research, game) == (
        "UNRESOLVED: canonical game database exposes no TAUNT skill-rank ability IDs",
    )
