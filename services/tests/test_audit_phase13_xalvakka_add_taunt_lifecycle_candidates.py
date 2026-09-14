from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.audit_phase13_xalvakka_add_taunt_lifecycle_candidates import audit


@pytest.fixture
def research_db(tmp_path: Path) -> Path:
    path = tmp_path / "research.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE log_fight (
            report_code TEXT,
            fight_id INTEGER,
            name TEXT,
            start_time REAL
        );
        CREATE TABLE log_report_actor (
            report_code TEXT,
            actor_id INTEGER,
            name TEXT
        );
        CREATE TABLE log_event (
            report_code TEXT,
            fight_id INTEGER,
            event_index INTEGER,
            timestamp REAL,
            event_type TEXT,
            source_id INTEGER,
            target_id INTEGER,
            target_instance INTEGER,
            ability_game_id INTEGER,
            source_is_friendly INTEGER,
            target_is_friendly INTEGER,
            raw_json TEXT
        );
        INSERT INTO log_fight VALUES ('R', 1, 'Xalvakka', 1000);
        INSERT INTO log_report_actor VALUES ('R', 104, 'Iron Atronach');
        INSERT INTO log_report_actor VALUES ('R', 112, 'Daedroth');
        """
    )
    # Hostile source activity creates the add instance consumed by observe_add_signals.
    db.execute(
        "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ('R', 1, 1, 2000, 'cast', 104, 1, 0, 900, 0, 1, '{"sourceInstance":1}'),
    )
    db.execute(
        "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ('R', 1, 2, 3000, 'damage', 1, 104, 1, 999, 1, 0, '{"targetInstance":1}'),
    )
    db.commit()
    db.close()
    return path


@pytest.fixture
def game_db(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "game.db"
    sqlite3.connect(path).close()

    from tools import audit_phase13_xalvakka_add_taunt_lifecycle_candidates as module

    monkeypatch.setattr(
        module,
        "canonical_taunt_abilities",
        lambda _path: (
            type("Taunt", (), {"ability_id": 100, "skill_name": "Puncture"})(),
        ),
    )
    return path


def test_audit_finds_target_matched_status_event_near_taunt_cast(
    research_db: Path,
    game_db: Path,
):
    db = sqlite3.connect(research_db)
    db.execute(
        "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ('R', 1, 3, 4000, 'cast', 1, 104, 1, 100, 1, 0, '{"targetInstance":1,"ability":{"name":"Puncture"}}'),
    )
    db.execute(
        "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ('R', 1, 4, 4050, 'applydebuff', 1, 104, 1, 555, 1, 0, '{"targetInstance":1,"ability":{"name":"Taunt State"}}'),
    )
    db.commit()
    db.close()

    lines = audit(research_db, game_db)

    assert any(
        "CANDIDATE_EFFECT: ability=Taunt State ability_id=555 event=applydebuff count=1" in line
        for line in lines
    )
    assert any(
        "cast=Puncture:100 effect=Taunt State:555 event=applydebuff offset=0.050s" in line
        for line in lines
    )


def test_audit_does_not_match_status_from_different_target_instance(
    research_db: Path,
    game_db: Path,
):
    db = sqlite3.connect(research_db)
    db.execute(
        "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ('R', 1, 3, 4000, 'cast', 1, 104, 1, 100, 1, 0, '{"targetInstance":1}'),
    )
    db.execute(
        "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ('R', 1, 4, 4050, 'applydebuff', 1, 104, 2, 555, 1, 0, '{"targetInstance":2,"ability":{"name":"Other Instance"}}'),
    )
    db.commit()
    db.close()

    lines = audit(research_db, game_db)

    assert "LIFECYCLE_CANDIDATE_EVENTS=0" in lines
