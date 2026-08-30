import sqlite3

from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId


def _database(tmp_path):
    """Create deliberately stale rows to prove current constants win."""
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
                ('Infused', 'enchantment_effect', 'Jewelry', 'Legendary', NULL, 12, 'flat'),
                ('Triune', 'max_health', 'Platinum', 'Legendary', 150, 473, 'flat'),
                ('Triune', 'max_magicka', 'Platinum', 'Legendary', 150, 430, 'flat'),
                ('Triune', 'max_stamina', 'Platinum', 'Legendary', 150, 430, 'flat'),
                ('Protective', 'physical_spell_resistance', 'Platinum', 'Legendary', 150, 1824, 'flat');
            """
        )
    return path


def test_saved_gold_quality_maps_to_current_legendary_infused_value(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_infused_enchantment_percent("Gold") == 60


def test_database_quality_name_can_be_used_directly(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_infused_enchantment_percent("Epic") == 51


def test_missing_quality_returns_none(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_infused_enchantment_percent("") is None


def test_stale_database_rows_do_not_override_current_constants(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_infused_enchantment_percent("Gold") == 60
    protective = repository.get_static_effects("Protective", quality="Gold", level="CP160")
    assert {effect.value for effect in protective} == {1190}


def test_cp160_gold_triune_resolves_current_all_three_resources(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    effects = repository.get_static_effects("Triune", quality="Gold", level="CP160")
    values = {effect.stat: effect.value for effect in effects}

    assert values == {
        StatId.MAX_HEALTH: 482,
        StatId.MAX_MAGICKA: 439,
        StatId.MAX_STAMINA: 439,
    }


def test_cp160_gold_protective_resolves_current_resistance(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    effects = repository.get_static_effects("Protective", quality="Gold", level="CP160")
    values = {effect.stat: effect.value for effect in effects}

    assert values == {
        StatId.PHYSICAL_RESISTANCE: 1190,
        StatId.SPELL_RESISTANCE: 1190,
    }


def test_arcane_healthy_and_robust_are_now_canonical_static_traits(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    arcane = repository.get_static_effects("Arcane", quality="Gold", level="CP160")
    healthy = repository.get_static_effects("Healthy", quality="Gold", level="CP160")
    robust = repository.get_static_effects("Robust", quality="Gold", level="CP160")

    assert [(effect.stat, effect.value) for effect in arcane] == [(StatId.MAX_MAGICKA, 877)]
    assert [(effect.stat, effect.value) for effect in healthy] == [(StatId.MAX_HEALTH, 965)]
    assert [(effect.stat, effect.value) for effect in robust] == [(StatId.MAX_STAMINA, 877)]


def test_non_max_level_is_not_assumed_to_use_cp160_trait_values(tmp_path):
    repository = JewelryTraitRepository(_database(tmp_path))

    assert repository.get_static_effects("Triune", quality="Gold", level="CP150") == []
