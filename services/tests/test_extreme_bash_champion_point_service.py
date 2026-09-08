from __future__ import annotations

import sqlite3

from minmax.champion_point_static_repository import ChampionPointStaticRepository
from services.extreme_bash_champion_point_service import (
    ExtremeBashChampionPointService,
)


def _db(tmp_path):
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE champion_point (
            name TEXT PRIMARY KEY,
            skill_type INTEGER,
            max_points INTEGER,
            jump_points TEXT,
            description TEXT,
            min_description TEXT,
            max_description TEXT
        )
        """
    )
    return path, connection


def _insert(connection, name, max_points, jumps, description):
    connection.execute(
        "INSERT INTO champion_point VALUES (?, 0, ?, ?, '', ?, ?)",
        (name, max_points, jumps, description, description),
    )


def test_bashing_brutality_projects_flat_cp_bash_damage(tmp_path):
    path, db = _db(tmp_path)
    _insert(
        db,
        "Bashing Brutality",
        20,
        "0,10,20",
        "Increases your Bash damage by 60 per stage.",
    )
    db.commit()
    db.close()

    result = ExtremeBashChampionPointService.resolve_damage(
        ChampionPointStaticRepository(path),
    )

    assert result.stages == 2
    assert result.reviewed_formula_value == 120.0
    assert result.canonical_flat_value == 120.0
    assert result.unresolved == ()
    assert result.mechanic_complete is True


def test_bashing_brutality_respects_partial_point_allocation(tmp_path):
    path, db = _db(tmp_path)
    _insert(
        db,
        "Bashing Brutality",
        20,
        "0,10,20",
        "Increases your Bash damage by 60 per stage.",
    )
    db.commit()
    db.close()

    repository = ChampionPointStaticRepository(path)
    assert ExtremeBashChampionPointService.resolve_damage(
        repository,
        points=9,
    ).reviewed_formula_value == 0.0
    assert ExtremeBashChampionPointService.resolve_damage(
        repository,
        points=10,
    ).reviewed_formula_value == 60.0


def test_savage_defense_preserves_flat_reduction_but_blocks_formula_conversion(tmp_path):
    path, db = _db(tmp_path)
    _insert(
        db,
        "Savage Defense",
        30,
        "0,15,30",
        "Reduces the cost of Bash by 45 Stamina per stage.",
    )
    db.commit()
    db.close()

    result = ExtremeBashChampionPointService.resolve_cost(
        ChampionPointStaticRepository(path),
    )

    assert result.stages == 2
    assert result.canonical_flat_value == -90.0
    assert result.reviewed_formula_value is None
    assert result.mechanic_complete is False
    assert result.unresolved == (
        "Savage Defense is a flat Stamina Bash-cost reduction, but the canonical "
        "Bash formula currently exposes CP.BashCost as a multiplier; conversion "
        "requires reviewed formula semantics",
    )


def test_unrecognized_bash_cp_tooltip_fails_closed(tmp_path):
    path, db = _db(tmp_path)
    _insert(
        db,
        "Bashing Brutality",
        20,
        "0,10,20",
        "Makes bashing better somehow.",
    )
    db.commit()
    db.close()

    result = ExtremeBashChampionPointService.resolve_damage(
        ChampionPointStaticRepository(path),
    )

    assert result.reviewed_formula_value is None
    assert result.mechanic_complete is False
    assert result.unresolved == (
        "unrecognized Bashing Brutality tooltip: Makes bashing better somehow.",
    )
