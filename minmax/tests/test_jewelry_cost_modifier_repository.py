from __future__ import annotations

import sqlite3
from pathlib import Path

from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.resource_cost_modifiers import CostModifierOperation
from minmax.resource_costs import ResourceType


def _database(tmp_path: Path) -> Path:
    database = tmp_path / "eso.db"
    with sqlite3.connect(database) as connection:
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
    return database


def _insert_effect(
    database: Path,
    *,
    item_id: int,
    name: str,
    effect_type: str,
    value: float,
    unit: str = "flat",
) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO jewelry_glyph (item_id, name) VALUES (?, ?)",
            (item_id, name),
        )
        connection.execute(
            """
            INSERT INTO jewelry_glyph_effect
                (glyph_item_id, effect_type, value_min, value_max, unit, description)
            VALUES (?, ?, ?, ?, ?, '')
            """,
            (item_id, effect_type, value, value, unit),
        )


def test_magicka_cost_reduction_maps_to_flat_magicka_modifier(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _insert_effect(
        database,
        item_id=1,
        name="Glyph of Reduce Spell Cost",
        effect_type="magicka_cost_reduction",
        value=203,
    )

    modifiers = JewelryCostModifierRepository(database).get_by_name(
        "Glyph of Reduce Spell Cost"
    )

    assert len(modifiers) == 1
    modifier = modifiers[0]
    assert modifier.operation is CostModifierOperation.FLAT_REDUCTION
    assert modifier.value == 203
    assert modifier.resources == (ResourceType.MAGICKA,)


def test_prismatic_cost_reduction_targets_three_primary_resources(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _insert_effect(
        database,
        item_id=2,
        name="Glyph of Reduce Skill Cost",
        effect_type="resource_cost_reduction",
        value=133,
    )

    modifier = JewelryCostModifierRepository(database).get_by_name(
        "Glyph of Reduce Skill Cost"
    )[0]

    assert modifier.resources == (
        ResourceType.HEALTH,
        ResourceType.MAGICKA,
        ResourceType.STAMINA,
    )


def test_repository_uses_strongest_matching_effect_type(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _insert_effect(
        database,
        item_id=10,
        name="Glyph of Reduce Spell Cost",
        effect_type="magicka_cost_reduction",
        value=150,
    )
    _insert_effect(
        database,
        item_id=11,
        name="Glyph of Reduce Spell Cost",
        effect_type="magicka_cost_reduction",
        value=203,
    )

    modifier = JewelryCostModifierRepository(database).get_by_name(
        "Glyph of Reduce Spell Cost"
    )[0]

    assert modifier.value == 203


def test_multiplier_and_source_prefix_support_infused_build_resolution(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _insert_effect(
        database,
        item_id=20,
        name="Glyph of Reduce Spell Cost",
        effect_type="magicka_cost_reduction",
        value=200,
    )

    modifier = JewelryCostModifierRepository(database).get_by_name(
        "Glyph of Reduce Spell Cost",
        multiplier=1.3,
        source_prefix="Necklace",
    )[0]

    assert modifier.value == 260
    assert modifier.source == "Necklace: Glyph of Reduce Spell Cost"


def test_non_cost_jewelry_effects_are_ignored(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _insert_effect(
        database,
        item_id=30,
        name="Glyph of Magicka Recovery",
        effect_type="magicka_recovery",
        value=169,
    )

    assert JewelryCostModifierRepository(database).get_by_name(
        "Glyph of Magicka Recovery"
    ) == ()
