import sqlite3

import pytest

from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE jewelry_trait_effect (
                id INTEGER PRIMARY KEY,
                trait_name TEXT NOT NULL,
                effect_type TEXT NOT NULL,
                item_type TEXT,
                quality TEXT,
                item_level INTEGER,
                value REAL,
                unit TEXT
            );
            INSERT INTO jewelry_trait_effect
                (trait_name, effect_type, item_type, quality, item_level, value, unit)
            VALUES
                ('Infused', 'enchantment_effect', 'Jewelry', 'Legendary', NULL, 60, 'percent'),
                ('Infused', 'enchantment_effect', 'Jewelry', 'Epic', NULL, 51, 'percent'),
                ('Triune', 'max_health', 'Platinum', 'Legendary', 150, 473, 'flat'),
                ('Triune', 'max_magicka', 'Platinum', 'Legendary', 150, 430, 'flat'),
                ('Triune', 'max_stamina', 'Platinum', 'Legendary', 150, 430, 'flat'),
                ('Protective', 'physical_spell_resistance', 'Platinum', 'Legendary', 150, 1824, 'flat');
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
            "UPDATE jewelry_trait_effect SET unit = 'flat' WHERE quality = 'Legendary' AND trait_name = 'Infused'"
        )

    repository = JewelryTraitRepository(path)

    with pytest.raises(ValueError, match="unsupported unit"):
        repository.get_infused_enchantment_percent("Gold")


def test_cp160_gold_triune_resolves_all_three_resources(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    effects = repository.get_static_effects("Triune", quality="Gold", level="CP160")
    values = {effect.stat: effect.value for effect in effects}

    assert values == {
        StatId.MAX_HEALTH: 473,
        StatId.MAX_MAGICKA: 430,
        StatId.MAX_STAMINA: 430,
    }


def test_cp160_gold_protective_splits_combined_resistance(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    effects = repository.get_static_effects("Protective", quality="Gold", level="CP160")
    values = {effect.stat: effect.value for effect in effects}

    assert values == {
        StatId.PHYSICAL_RESISTANCE: 1824,
        StatId.SPELL_RESISTANCE: 1824,
    }


def test_non_max_level_is_not_assumed_to_use_cp160_trait_values(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_static_effects("Triune", quality="Gold", level="CP150") == []
