from __future__ import annotations

import sqlite3
from pathlib import Path

from services.roster_gear_set_alias_service import resolve_roster_gear_set_name


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE gear_set (id INTEGER PRIMARY KEY, name TEXT, category TEXT, max_equip_count INTEGER)"
        )
        rows = [
            (1, "Roaring Opportunist", "Trial", 5),
            (2, "Perfected Roaring Opportunist", "Trial", 5),
            (3, "Pillager's Profit", "Dungeon", 5),
            (4, "Symphony of Blades", "Monster", 2),
            (5, "Ozezan the Inferno", "Monster", 2),
            (6, "Lucent Echoes", "Trial", 5),
            (7, "Pillar of Nirn", "Dungeon", 5),
            (8, "Perfected Coral Riptide", "Trial", 5),
            (9, "Coral Riptide", "Trial", 5),
        ]
        connection.executemany(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (?, ?, ?, ?)",
            rows,
        )
    return path


def test_alias_prefers_perfected_when_available(tmp_path: Path) -> None:
    db = _database(tmp_path)
    result = resolve_roster_gear_set_name("RO", database_path=db)
    assert result.canonical_name == "Perfected Roaring Opportunist"
    assert result.matched_alias is True
    assert result.perfected is True


def test_user_requested_roster_aliases_resolve(tmp_path: Path) -> None:
    db = _database(tmp_path)
    expected = {
        "Pill": "Pillager's Profit",
        "Pilly": "Pillager's Profit",
        "SoB": "Symphony of Blades",
        "Oz": "Ozezan the Inferno",
        "LE": "Lucent Echoes",
    }
    for raw, canonical in expected.items():
        assert resolve_roster_gear_set_name(raw, database_path=db).canonical_name == canonical


def test_pill_and_pillar_are_not_fuzzy_collisions(tmp_path: Path) -> None:
    db = _database(tmp_path)
    assert resolve_roster_gear_set_name("Pill", database_path=db).canonical_name == "Pillager's Profit"
    assert resolve_roster_gear_set_name("Pillar", database_path=db).canonical_name == "Pillar of Nirn"


def test_explicit_normal_opt_out_preserves_non_perfected(tmp_path: Path) -> None:
    db = _database(tmp_path)
    result = resolve_roster_gear_set_name("normal RO", database_path=db)
    assert result.canonical_name == "Roaring Opportunist"
    assert result.explicit_non_perfected is True
    assert result.perfected is False


def test_alias_only_backfill_leaves_full_canonical_non_perfected_name_alone(tmp_path: Path) -> None:
    db = _database(tmp_path)
    result = resolve_roster_gear_set_name(
        "Roaring Opportunist",
        database_path=db,
        aliases_only=True,
    )
    assert result.canonical_name == "Roaring Opportunist"
    assert result.matched_alias is False


def test_full_name_import_still_prefers_perfected_when_available(tmp_path: Path) -> None:
    db = _database(tmp_path)
    result = resolve_roster_gear_set_name("Coral Riptide", database_path=db)
    assert result.canonical_name == "Perfected Coral Riptide"
