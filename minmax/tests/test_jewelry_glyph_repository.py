import sqlite3

import pytest

import minmax.jewelry_glyph_repository as jewelry_glyph_module
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
                (500, "Lesser Glyph of Bashing"),
                (501, "Truly Superb Glyph of Bashing"),
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
                (8, 500, "bash_damage", 10, 90, "flat", "Bash attacks deal more damage"),
                (9, 501, "bash_damage", 20, 180, "flat", "Bash attacks deal more damage"),
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


def test_effect_type_lookup_returns_strongest_canonical_bash_glyph(tmp_path):
    repository = JewelryGlyphEffectRepository(_database(tmp_path))

    effects = repository.get_strongest_jewelry_glyph_effect_by_type("  BASH_DAMAGE  ")

    assert len(effects) == 1
    assert effects[0].stat == StatId.BASH_DAMAGE
    assert effects[0].value == 180
    assert effects[0].source == "Truly Superb Glyph of Bashing"


def test_effect_type_lookup_can_use_minimum_recorded_value(tmp_path):
    repository = JewelryGlyphEffectRepository(_database(tmp_path))

    effects = repository.get_strongest_jewelry_glyph_effect_by_type(
        "bash_damage",
        use_max_value=False,
    )

    assert effects[0].value == 20


def test_jewelry_glyph_catalog_and_semantic_lookups_are_cached(tmp_path, monkeypatch):
    database_path = _database(tmp_path)
    original_connect = jewelry_glyph_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(jewelry_glyph_module.sqlite3, "connect", counting_connect)
    repository = JewelryGlyphEffectRepository(database_path)

    names = repository.list_names()
    assert repository.list_names() == names
    assert connect_count == 1

    effect_types = repository.get_jewelry_glyph_effect_types_by_name(" Glyph of Test Harm ")
    assert repository.get_jewelry_glyph_effect_types_by_name("glyph of test harm") == effect_types
    assert connect_count == 2

    fresh_repository = JewelryGlyphEffectRepository(database_path)
    assert fresh_repository.list_names() == names
    assert connect_count == 3


def test_jewelry_mapped_effect_lookups_are_cached_and_return_list_copies(tmp_path, monkeypatch):
    database_path = _database(tmp_path)
    original_connect = jewelry_glyph_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(jewelry_glyph_module.sqlite3, "connect", counting_connect)
    repository = JewelryGlyphEffectRepository(database_path)

    by_item = repository.get_jewelry_glyph_effect(100)
    by_item_again = repository.get_jewelry_glyph_effect(100)
    assert by_item == by_item_again
    assert by_item is not by_item_again
    assert connect_count == 1

    by_name = repository.get_jewelry_glyph_effect_by_name(" Glyph of Test Harm ")
    by_name_again = repository.get_jewelry_glyph_effect_by_name("glyph of test harm")
    assert by_name == by_name_again
    assert by_name is not by_name_again
    assert connect_count == 2

    strongest = repository.get_strongest_jewelry_glyph_effect_by_type(" BASH_DAMAGE ")
    strongest_again = repository.get_strongest_jewelry_glyph_effect_by_type("bash_damage")
    assert strongest == strongest_again
    assert strongest is not strongest_again
    assert connect_count == 3

    by_item.clear()
    by_name.clear()
    strongest.clear()
    assert repository.get_jewelry_glyph_effect(100) == by_item_again
    assert repository.get_jewelry_glyph_effect_by_name("Glyph of Test Harm") == by_name_again
    assert repository.get_strongest_jewelry_glyph_effect_by_type("bash_damage") == strongest_again
    assert connect_count == 3
