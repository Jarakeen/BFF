import sqlite3
from pathlib import Path

from minmax.weapon_enchantment_repository import WeaponEnchantmentRepository


def _create_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE weapon_enchantment (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                enchant_name TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE weapon_enchantment_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enchantment_item_id INTEGER NOT NULL,
                effect_type TEXT NOT NULL
            )
            """
        )
        db.executemany(
            "INSERT INTO weapon_enchantment(item_id, name, enchant_name) VALUES (?, ?, ?)",
            [
                (101, "Glyph of Weapon Damage", "Weapon Damage"),
                (202, "Glyph of Crushing", "Crushing"),
                (303, "Duplicate A", "Ambiguous"),
                (304, "Duplicate B", "Ambiguous"),
            ],
        )
        db.executemany(
            "INSERT INTO weapon_enchantment_effect(enchantment_item_id, effect_type) VALUES (?, ?)",
            [
                (101, "weapon_spell_damage"),
                (202, "physical_spell_resistance_reduction"),
            ],
        )


def _create_semantic_alias_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE weapon_enchantment (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                enchant_name TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE weapon_enchantment_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enchantment_item_id INTEGER NOT NULL,
                effect_type TEXT NOT NULL
            )
            """
        )
        db.executemany(
            "INSERT INTO weapon_enchantment(item_id, name, enchant_name) VALUES (?, ?, ?)",
            [
                (54484, "Glyph of Weapon Damage", "Weapon Damage Enchantment"),
                (26845, "Glyph of Crushing", "Crusher Enchantment"),
            ],
        )
        db.executemany(
            "INSERT INTO weapon_enchantment_effect(enchantment_item_id, effect_type) VALUES (?, ?)",
            [
                (54484, "weapon_spell_damage"),
                (26845, "physical_spell_resistance_reduction"),
            ],
        )


def test_find_item_ids_by_label_matches_enchant_name_exactly(tmp_path: Path):
    database = tmp_path / "eso.db"
    _create_database(database)
    repository = WeaponEnchantmentRepository(database)

    assert repository.find_item_ids_by_label(" weapon   damage ") == (101,)
    assert repository.find_item_ids_by_label("Crushing") == (202,)


def test_find_item_ids_by_label_can_match_imported_item_name(tmp_path: Path):
    database = tmp_path / "eso.db"
    _create_database(database)
    repository = WeaponEnchantmentRepository(database)

    assert repository.find_item_ids_by_label("Glyph of Crushing") == (202,)


def test_find_item_ids_by_label_preserves_missing_and_ambiguous_results(tmp_path: Path):
    database = tmp_path / "eso.db"
    _create_database(database)
    repository = WeaponEnchantmentRepository(database)

    assert repository.find_item_ids_by_label("Not In Database") == ()
    assert repository.find_item_ids_by_label("Ambiguous") == (303, 304)


def test_saved_ui_aliases_resolve_by_verified_effect_signature(tmp_path: Path):
    database = tmp_path / "eso.db"
    _create_semantic_alias_database(database)
    repository = WeaponEnchantmentRepository(database)

    assert repository.find_item_ids_by_label("Weapon Damage") == (54484,)
    assert repository.find_item_ids_by_label("Crushing") == (26845,)
