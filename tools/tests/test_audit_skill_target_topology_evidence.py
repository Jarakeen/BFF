from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.audit_skill_target_topology_evidence import audit


def _database(path: Path) -> Path:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                target TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                rank INTEGER,
                morph INTEGER,
                radius REAL,
                angle_distance REAL,
                raw_json TEXT
            );
            """
        )
        db.execute(
            "INSERT INTO skill(id, name, target) VALUES (1, 'Wide Heal', 'Area')"
        )
        db.execute(
            "INSERT INTO skill(id, name, target) VALUES (2, 'Cone Heal', 'Cone')"
        )
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, rank, morph, radius, angle_distance, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                1,
                4,
                0,
                8.0,
                0.0,
                json.dumps({"maxTargets": 6, "name": "Wide Heal"}),
            ),
        )
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, rank, morph, radius, angle_distance, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                2,
                4,
                0,
                0.0,
                28.0,
                json.dumps({"nested": {"target_count": 3}}),
            ),
        )
        db.commit()
    return path


def test_audit_reports_geometry_and_raw_capacity_fields(tmp_path: Path) -> None:
    output = audit(_database(tmp_path / "eso.db"))

    assert "radius=8" in output
    assert "examples=Wide Heal" in output
    assert "angle_distance=28" in output
    assert "examples=Cone Heal" in output
    assert "maxTargets=6" in output
    assert "nested.target_count=3" in output
    assert "does not infer target capacity" in output


def test_audit_reports_absence_without_inference(tmp_path: Path) -> None:
    path = tmp_path / "empty.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                target TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                rank INTEGER,
                morph INTEGER,
                radius REAL,
                angle_distance REAL,
                raw_json TEXT
            );
            """
        )
        db.execute("INSERT INTO skill(id, name, target) VALUES (1, 'Plain Skill', '')")
        db.execute(
            "INSERT INTO skill_rank(id, skill_id, rank, morph, radius, angle_distance, raw_json) "
            "VALUES (1, 1, 1, 0, 0, 0, '{}')"
        )
        db.commit()

    output = audit(path)

    assert "No positive radius or angle_distance values found." in output
    assert "No target-count/max-target-like raw_json fields found." in output
