import sqlite3

import pytest

from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.stat_ids import StatId


def _database(tmp_path):
    database_path = tmp_path / "jewelry_glyphs.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE jewelry_glyph (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );

            CREATE TABLE jewelry_glyph_effect (
                id INTEGER PRIMARY KEY,
                glyph_item_id INTEGER NOT NULL,
                effect_type TEXT NOT NULL,
                value_min REAL,
                value_max REAL,
                unit TEXT NOT NULL,
                description TEXT
            );
            """
        )
        connection.executemany(
            "INSERT INTO jewelry_glyph(item_id, name) VALUES (?, ?)",
            [
                (100, "Glyph of Stamina Recovery"),
                (200, "Glyph of Test Harm"),
                (201, "Glyph of Test Harm"),
                (300, "Glyph of Strange Things"),
                (400, "Glyph of Increase Magical Harm"),
            ],
        )
        connection.executemany(
            """
            INSERT INTO jewelry_glyph_effect(
                id, glyph_item_id, effect_type, value_min, value_max, unit, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 100, "stamina_recovery", 10, 169, "flat", "Adds Stamina Recovery"),
                (2, 200, "max_magicka", 20, 300, "flat", "Lower tier Magicka"),
                (3, 200, "stamina_recovery", 5, 80, "flat", "Lower tier Recovery"),
                (4, 201, "max_magicka", 30, 600, "flat", "Max tier Magicka"),
                (5, 201, "stamina_recovery", 10, 160, "flat", "Max tier Recovery"),
                (6, 300, "not_a_real_engine_stat", 1, 2, "flat", "Unsupported"),
                (7, 400, "weapon_spell_damage", 10, 174, "flat", "Adds damage"),
            ],
        )
    return database_path


def test_item_lookup_uses_max_value_by_default(tmp_path):
    repository = JewelryGlyphEffectRepository(_database(tmp_path))

    effects = repository.get_jewelry_glyph_effect(100)

    assert len(effects) == 1
    assert effects[0].stat == StatId.STAMINA_RECOVERY
    assert effects[0].value == 169
    assert effects[0].source == "Glyph of Stamina Recovery"


def test_item_lookup_can_use_min_value(tmp_path):
    repository = JewelryGlyphEffectRepository(_database(tmp_path))

    effects = repository.get_jewelry_glyph_effect(100, use_max_value=False)

    assert effects[0].value == 10


def test_name_lookup_preserves_each_effect_type_from_strongest_named_glyph(tmp_path):
    repository = JewelryGlyphEffectRepository(_database(tmp_path))

    effects = repository.get_jewelry_glyph_effect_by_name("  glyph of test harm  ")
    values = {effect.stat: effect.value for effect in effects}

    assert values == {
        StatId.MAX_MAGICKA: 600,
        StatId.STAMINA_RECOVERY: 160,
    }


def test_unsupported_effect_type_is_explicit(tmp_path):
    repository = JewelryGlyphEffectRepository(_database(tmp_path))

    with pytest.raises(ValueError, match="Unsupported engine stat effect type"):
        repository.get_jewelry_glyph_effect(300)



def test_combined_weapon_spell_damage_glyph_maps_to_both_stats(tmp_path):
    repository = JewelryGlyphEffectRepository(_database(tmp_path))

    effects = repository.get_jewelry_glyph_effect_by_name(
        "Glyph of Increase Magical Harm"
    )
    values = {effect.stat: effect.value for effect in effects}

    assert values == {
        StatId.WEAPON_DAMAGE: 174,
        StatId.SPELL_DAMAGE: 174,
    }
