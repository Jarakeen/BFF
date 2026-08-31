from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.evaluate_action_cost_formula import evaluate_database_ability


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                rank INTEGER,
                morph INTEGER,
                skill_line TEXT,
                base_cost REAL,
                base_mechanic INTEGER
            )
            """
        )
        connection.executemany(
            "INSERT INTO ability VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1001, "Test Spell", 1, 0, "Test Line", 3000.0, 1),
                (1002, "Test Spell", 4, 0, "Test Line", 2700.0, 1),
                (1003, "Hybrid Cost", 4, 1, "Test Line", 1000.0, 5),
            ],
        )
    return path


def test_probe_resolves_exact_ability_id_and_resources(tmp_path: Path) -> None:
    report = evaluate_database_ability(
        _database(tmp_path),
        ability_id=1003,
        flat_reduction=100.0,
        percent_reduction=0.10,
        observed_cost=810,
    )

    assert report["name"] == "Hybrid Cost"
    assert report["resources"] == ("magicka", "stamina")
    assert report["base_cost"] == 1000.0
    assert ("flat_then_percent_then_increase", "floor") in report["matches"]


def test_probe_requires_rank_when_name_is_ambiguous(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        evaluate_database_ability(_database(tmp_path), name="Test Spell")


def test_probe_can_disambiguate_name_by_rank(tmp_path: Path) -> None:
    report = evaluate_database_ability(
        _database(tmp_path),
        name="test spell",
        rank=4,
    )

    assert report["ability_id"] == 1002
    assert report["base_cost"] == 2700.0


def test_probe_rejects_missing_identity(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Provide either"):
        evaluate_database_ability(_database(tmp_path))
