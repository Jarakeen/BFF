from pathlib import Path

import minmax.armor_glyph_repository as armor_glyph_module
from minmax.armor_glyph_repository import ArmorGlyphEffectRepository


DB_PATH = Path("data/eso.db")


def test_named_glyph_resolution_is_cached_case_insensitively(monkeypatch) -> None:
    original_connect = armor_glyph_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(armor_glyph_module.sqlite3, "connect", counting_connect)
    repository = ArmorGlyphEffectRepository(DB_PATH)

    first = repository.get_armor_glyph_effect_by_name(" Glyph of Health ")
    second = repository.get_armor_glyph_effect_by_name("glyph of health")

    assert first == second
    assert first is not second
    assert connect_count == 1

    first.clear()
    assert repository.get_armor_glyph_effect_by_name("Glyph of Health") == second
    assert connect_count == 1


def test_named_glyph_cache_keeps_min_and_max_value_paths_distinct(monkeypatch) -> None:
    original_connect = armor_glyph_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(armor_glyph_module.sqlite3, "connect", counting_connect)
    repository = ArmorGlyphEffectRepository(DB_PATH)

    maximum = repository.get_armor_glyph_effect_by_name("Glyph of Health", use_max_value=True)
    minimum = repository.get_armor_glyph_effect_by_name("Glyph of Health", use_max_value=False)
    maximum_again = repository.get_armor_glyph_effect_by_name("glyph of health", use_max_value=True)

    assert maximum_again == maximum
    assert minimum != maximum
    assert connect_count == 2


def test_unresolved_named_glyph_is_cached(monkeypatch) -> None:
    original_connect = armor_glyph_module.sqlite3.connect
    connect_count = 0

    def counting_connect(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(armor_glyph_module.sqlite3, "connect", counting_connect)
    repository = ArmorGlyphEffectRepository(DB_PATH)

    assert repository.get_armor_glyph_effect_by_name("Definitely Missing Glyph") == []
    assert repository.get_armor_glyph_effect_by_name(" definitely missing glyph ") == []
    assert connect_count == 1
