from __future__ import annotations

import sqlite3
from pathlib import Path

from minmax.character_build.gear_piece import GearPieceCategory
from minmax.gear_set_category_resolver import GearSetCategoryResolver


def _make_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            );
            CREATE TABLE gear_set_item (
                set_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                PRIMARY KEY(set_id, item_id)
            );

            INSERT INTO gear_set VALUES
                (609, 'Magma Incarnate', 'standard', 2),
                (627, 'Spaulder of Ruin', 'standard', 1),
                (641, 'Serpent''s Disdain', 'standard', 5),
                (900, 'One-piece Weapon Test', 'standard', 1);

            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES
                (609, 1, 1, 0),
                (609, 1, 2, 0),
                (609, 1, 3, 0),
                (609, 4, 1, 0),
                (609, 4, 2, 0),
                (609, 4, 3, 0),
                (627, 4, 1, 0),
                (641, 1, 1, 0),
                (641, 4, 1, 0),
                (641, 8, 1, 0),
                (900, 5, 0, 12);

            INSERT INTO gear_set_item VALUES
                (609, 178627),
                (609, 178628),
                (627, 181695),
                (641, 185164),
                (641, 185165),
                (900, 999001);
            """
        )


def test_classifies_magma_structure_as_monster_set(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _make_db(database)

    result = GearSetCategoryResolver(database).resolve(609, raw_category="standard")

    assert result == GearPieceCategory.MONSTER_SET


def test_classifies_spaulder_structure_as_mythic(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _make_db(database)

    result = GearSetCategoryResolver(database).resolve(627, raw_category="standard")

    assert result == GearPieceCategory.MYTHIC


def test_standard_multislot_set_remains_set_piece(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _make_db(database)

    result = GearSetCategoryResolver(database).resolve(641, raw_category="standard")

    assert result == GearPieceCategory.SET_PIECE


def test_one_piece_weapon_structure_is_not_misclassified_as_mythic(tmp_path: Path) -> None:
    database = tmp_path / "eso.db"
    _make_db(database)

    result = GearSetCategoryResolver(database).resolve(900, raw_category="standard")

    assert result == GearPieceCategory.SET_PIECE


def test_explicit_imported_special_category_wins_without_structure(tmp_path: Path) -> None:
    database = tmp_path / "empty.db"

    resolver = GearSetCategoryResolver(database)

    assert resolver.resolve(1, raw_category="mythic") == GearPieceCategory.MYTHIC
    assert resolver.resolve(2, raw_category="monster") == GearPieceCategory.MONSTER_SET
