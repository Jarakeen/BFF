import sqlite3

import pytest

from minmax.jewelry_trait_repository import JewelryTraitRepository


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE jewelry_trait_effect (
                id INTEGER PRIMARY KEY,
                trait_name TEXT NOT NULL,
                effect_type TEXT NOT NULL,
                item_type TEXT NOT NULL,
                quality TEXT NOT NULL,
                value REAL,
                unit TEXT
            );
            INSERT INTO jewelry_trait_effect
                (trait_name, effect_type, item_type, quality, value, unit)
            VALUES
                ('Infused', 'enchantment_effect', 'Jewelry', 'Legendary', 60, 'percent'),
                ('Infused', 'enchantment_effect', 'Jewelry', 'Epic', 51, 'percent');
            """
        )
    return path


def test_saved_gold_quality_maps_to_legendary_infused_value(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_infused_enchantment_percent("Gold") == 60


def test_database_quality_name_can_be_used_directly(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_infused_enchantment_percent("Epic") == 51


def test_missing_quality_returns_none(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_infused_enchantment_percent("") is None


def test_non_percent_infused_rule_is_rejected(tmp_path):
    path = _database(tmp_path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE jewelry_trait_effect SET unit = 'flat' WHERE quality = 'Legendary'"
        )

    repository = JewelryTraitRepository(path)

    with pytest.raises(ValueError, match="unsupported unit"):
        repository.get_infused_enchantment_percent("Gold")
