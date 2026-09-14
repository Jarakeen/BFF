from __future__ import annotations

import sqlite3
from pathlib import Path

from tools.audit_phase13_xalvakka_taunt_source_identity import audit


def _fixture(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript(
            """
            CREATE TABLE log_report_actor (
                report_code TEXT NOT NULL,
                actor_id INTEGER NOT NULL,
                name TEXT,
                type TEXT,
                sub_type TEXT,
                game_id INTEGER
            );
            CREATE TABLE log_fight (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                event_index INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                ability_game_id INTEGER,
                source_id INTEGER,
                target_id INTEGER,
                source_is_friendly INTEGER,
                target_instance INTEGER,
                raw_json TEXT
            );
            """
        )
        db.executemany(
            "INSERT INTO log_report_actor VALUES (?, ?, ?, ?, ?, ?)",
            (
                ("r", 1, "Tank One", "Player", "DragonKnight", 101),
                ("r", 5, "Tank Two", "Player", "Necromancer", 105),
                ("r", 104, "Iron Atronach", "NPC", "NPC", 201),
                ("r", 112, "Daedroth", "NPC", "NPC", 202),
            ),
        )
        db.execute("INSERT INTO log_fight VALUES ('r', 30, 'Xalvakka')")
        db.executemany(
            "INSERT INTO log_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ("r", 30, 1000, 1, "applydebuff", 38254, 1, 104, 1, 1, "{}"),
                ("r", 30, 2000, 2, "removedebuff", 38254, 1, 104, 1, 1, "{}"),
                ("r", 30, 3000, 3, "applydebuff", 38254, 5, 112, 1, 2, "{}"),
                ("r", 30, 4000, 4, "removedebuff", 38254, 5, 112, 1, 2, "{}"),
            ),
        )
        db.commit()
    finally:
        db.close()


def test_audit_resolves_distinct_taunt_sources_without_assigning_tank_roles(tmp_path: Path) -> None:
    path = tmp_path / "runtime.db"
    _fixture(path)

    lines = audit(path)
    text = "\n".join(lines)

    assert "OBSERVED_SOURCES=2" in text
    assert "source_id=1 name=Tank One" in text
    assert "source_id=5 name=Tank Two" in text
    assert "actor=Iron Atronach instance=1" in text
    assert "actor=Daedroth instance=2" in text
    assert "Main/Off Tank role assignment requires independent reviewed roster/prescription evidence" in text
