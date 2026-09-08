from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from minmax.jewelry_potion_cooldown_repository import JewelryPotionCooldownRepository


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE jewelry_glyph (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE jewelry_glyph_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                glyph_item_id INTEGER NOT NULL,
                effect_type TEXT,
                value_min REAL,
                value_max REAL,
                unit TEXT,
                description TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO jewelry_glyph(item_id, name) VALUES(1, 'Glyph of Potion Speed')"
        )
        connection.execute(
            """
            INSERT INTO jewelry_glyph_effect(
                glyph_item_id, effect_type, value_min, value_max, unit, description
            ) VALUES(1, 'potion_cooldown_reduction', 3, 5, 'seconds', '')
            """
        )
        connection.execute(
            """
            INSERT INTO jewelry_glyph_effect(
                glyph_item_id, effect_type, value_min, value_max, unit, description
            ) VALUES(1, 'potion_duration', 2, 4, 'seconds', '')
            """
        )
        connection.commit()
    return path


def test_resolves_only_potion_cooldown_reduction_and_supports_infused_multiplier(tmp_path: Path) -> None:
    repository = JewelryPotionCooldownRepository(_database(tmp_path))

    result = repository.get_by_name(
        "  glyph of potion speed  ",
        multiplier=1.6,
        source_prefix="Ring 1",
    )

    assert len(result) == 1
    assert result[0].source == "Ring 1: Glyph of Potion Speed"
    assert result[0].seconds == 8.0


def test_missing_cooldown_effect_returns_no_reduction(tmp_path: Path) -> None:
    repository = JewelryPotionCooldownRepository(_database(tmp_path))

    assert repository.get_by_name("Unknown Glyph") == ()


def test_rejects_non_seconds_cooldown_units(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE jewelry_glyph_effect SET unit='percent' WHERE effect_type='potion_cooldown_reduction'"
        )
        connection.commit()

    with pytest.raises(ValueError, match="Unsupported jewelry potion cooldown unit"):
        JewelryPotionCooldownRepository(database).get_by_name("Glyph of Potion Speed")
