from pathlib import Path

from minmax.armor_glyph_repository import (
    ArmorGlyphEffectRepository,
)
from minmax.effects import EffectOperation, EffectUnit
from minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")


def test_health_glyph_from_database():
    repository = ArmorGlyphEffectRepository(DB_PATH)

    effects = repository.get_armor_glyph_effect(26580)

    assert len(effects) == 1

    effect = effects[0]

    assert effect.stat == StatId.MAX_HEALTH
    assert effect.operation == EffectOperation.ADD
    assert effect.value == 954
    assert effect.unit == EffectUnit.FLAT
    assert effect.source == "Glyph of Health"


def test_prismatic_glyph_produces_three_effects():
    repository = ArmorGlyphEffectRepository(DB_PATH)

    effects = repository.get_armor_glyph_effect(68343)

    assert len(effects) == 3

    values = {
        effect.stat: effect.value
        for effect in effects
    }

    assert values[StatId.MAX_HEALTH] == 477
    assert values[StatId.MAX_MAGICKA] == 434
    assert values[StatId.MAX_STAMINA] == 434


def test_prismatic_glyph_can_resolve_minimum_values():
    repository = ArmorGlyphEffectRepository(DB_PATH)

    effects = repository.get_armor_glyph_effect(
        68343,
        use_max_value=False,
    )

    values = {
        effect.stat: effect.value
        for effect in effects
    }

    assert values[StatId.MAX_HEALTH] == 38
    assert values[StatId.MAX_MAGICKA] == 35
    assert values[StatId.MAX_STAMINA] == 35