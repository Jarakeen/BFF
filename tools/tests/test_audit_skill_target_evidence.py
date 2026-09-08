from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.audit_skill_target_evidence import audit


def _database(path: Path) -> Path:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                target INTEGER
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                rank INTEGER,
                morph INTEGER,
                raw_json TEXT
            );
            """
        )
        db.execute("INSERT INTO skill VALUES (1, 'Combat Prayer', 4)")
        db.execute("INSERT INTO skill VALUES (2, 'Force Pulse', 7)")
        db.execute(
            "INSERT INTO skill_rank VALUES (?, ?, ?, ?, ?)",
            (
                11,
                1,
                4,
                1,
                json.dumps(
                    {
                        "target": 4,
                        "targetDescription": "Area",
                        "nested": {"preferredTarget": "group"},
                    }
                ),
            ),
        )
        db.execute(
            "INSERT INTO skill_rank VALUES (?, ?, ?, ?, ?)",
            (21, 2, 4, 1, json.dumps({"target": 7})),
        )
    return path


def test_audit_reports_opaque_targets_and_retained_raw_target_fields(tmp_path: Path) -> None:
    output = audit(_database(tmp_path / "eso.db"))

    assert "target=4: rows=1; examples=Combat Prayer" in output
    assert "target=7: rows=1; examples=Force Pulse" in output
    assert 'target=4: rows=1; examples=Combat Prayer' in output
    assert 'targetDescription="Area": rows=1; examples=Combat Prayer' in output
    assert 'nested.preferredTarget="group": rows=1; examples=Combat Prayer' in output
    assert "does not map opaque integer target values" in output


def test_audit_reports_when_raw_target_fields_are_absent(tmp_path: Path) -> None:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (id INTEGER PRIMARY KEY, name TEXT, target INTEGER);
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                rank INTEGER,
                morph INTEGER,
                raw_json TEXT
            );
            INSERT INTO skill VALUES (1, 'Skill', NULL);
            INSERT INTO skill_rank VALUES (1, 1, 1, 0, '{"name": "Skill"}');
            """
        )

    output = audit(path)

    assert "target=NULL: rows=1; examples=Skill" in output
    assert "No target-related raw_json fields found." in output
