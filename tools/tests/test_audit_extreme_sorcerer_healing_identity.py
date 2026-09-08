from __future__ import annotations

import sqlite3
from pathlib import Path

from tools.audit_extreme_sorcerer_healing_identity import audit


def _database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                coef_description TEXT
            );
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            );
            CREATE TABLE skill_coefficient (
                skill_rank_id INTEGER,
                coefficient_number INTEGER,
                type TEXT,
                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL
            );
            CREATE TABLE skill_component_classification (
                skill_rank_id INTEGER,
                coefficient_number INTEGER,
                effect_kind TEXT,
                damage_type TEXT,
                is_dot INTEGER,
                is_aoe INTEGER,
                can_crit INTEGER,
                source TEXT,
                confidence REAL
            );
            """
        )
        db.execute(
            "INSERT INTO skill(id, base_ability_id, name) VALUES (1, 100, 'Summon Twilight Matriarch')"
        )
        db.execute(
            "INSERT INTO ability(ability_id, name, coef_description) VALUES (?, ?, ?)",
            (
                101,
                "Summon Twilight Matriarch",
                "Command the twilight to heal itself for $1 Health and up to 2 friendly targets for $2 Health.",
            ),
        )
        db.execute(
            "INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph) VALUES (10, 1, 101, ?, 4, 2)",
            ("Summon Twilight Matriarch",),
        )
        db.executemany(
            "INSERT INTO skill_coefficient VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (10, 1, "8", 0.10, 1.0, 0.0, 1.0, None),
                (10, 2, "8", 0.12, 1.1, 0.0, 1.0, None),
            ),
        )
        db.executemany(
            "INSERT INTO skill_component_classification VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (10, 1, "heal", None, 0, 0, 1, "test", 1.0),
                (10, 2, "heal", None, 0, 1, 1, "test", 1.0),
            ),
        )
        db.commit()


def test_audit_prints_sorcerer_healing_component_evidence(tmp_path, capsys):
    database = tmp_path / "eso.db"
    _database(database)

    assert audit(database_path=database) == 0
    output = capsys.readouterr().out

    assert "Summon Twilight Matriarch" in output
    assert "skill_rank_id=10" in output
    assert "coef #1" in output
    assert "coef #2" in output
    assert "kind=heal" in output
    assert "Command the twilight to heal itself for $1 Health" in output
    assert "up to 2 friendly targets for $2 Health" in output
    assert "Pet activation heals require recipient identity" in output
    assert "Blood Magic is a passive-triggered self heal" in output


def test_audit_fails_cleanly_for_missing_database(tmp_path, capsys):
    database = tmp_path / "missing.db"

    assert audit(database_path=database) == 1
    assert "Database not found" in capsys.readouterr().out
