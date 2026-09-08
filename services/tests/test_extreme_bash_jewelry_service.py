from __future__ import annotations

import pytest

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild
from services.extreme_bash_jewelry_service import ExtremeBashJewelryService


class FakeGlyphRepository:
    def __init__(self, value: float = 180.0, *, missing: bool = False) -> None:
        self.value = value
        self.missing = missing

    def get_strongest_jewelry_glyph_effect_by_type(self, effect_type, *, use_max_value=True):
        assert effect_type == "bash_damage"
        assert use_max_value is True
        if self.missing:
            return []
        return [
            Effect(
                source="Truly Superb Glyph of Bashing",
                stat=StatId.BASH_DAMAGE,
                operation=EffectOperation.ADD,
                value=self.value,
                unit=EffectUnit.FLAT,
            )
        ]


class FakeTraitRepository:
    def get_infused_enchantment_percent(self, quality):
        return 60.0 if str(quality).casefold() in {"gold", "legendary"} else None


def _bashing_slot(**overrides) -> GearSlot:
    values = {
        "Enchant": "Bashing",
        "EnchantTier": "Truly Superb",
        "Level": "CP160",
        "Quality": "Gold",
    }
    values.update(overrides)
    return GearSlot(**values)


def test_plain_bashing_jewelry_feeds_item_extra_bash_damage():
    build = PlayerBuild(Necklace=_bashing_slot())
    result = ExtremeBashJewelryService(FakeGlyphRepository()).evaluate_build(build)

    assert result.reviewed_item_extra_bash_damage == pytest.approx(180.0)
    assert result.unresolved == ()
    assert result.mechanic_complete is True
    assert result.slots[0].source_effects[0].source == "Truly Superb Glyph of Bashing"


def test_three_bashing_enchants_stack_as_separate_item_sources():
    build = PlayerBuild(
        Necklace=_bashing_slot(),
        Ring1=_bashing_slot(),
        Ring2=_bashing_slot(),
    )
    result = ExtremeBashJewelryService(FakeGlyphRepository()).evaluate_build(build)

    assert result.reviewed_item_extra_bash_damage == pytest.approx(540.0)
    assert result.mechanic_complete is True


def test_infused_scales_only_the_selected_bashing_enchant():
    build = PlayerBuild(
        Necklace=_bashing_slot(Trait="Infused", Quality="Gold"),
        Ring1=GearSlot(
            Enchant="Weapon Damage",
            Trait="Infused",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        ),
    )
    result = ExtremeBashJewelryService(
        FakeGlyphRepository(),
        trait_repository=FakeTraitRepository(),
    ).evaluate_build(build)

    assert result.reviewed_item_extra_bash_damage == pytest.approx(288.0)
    assert result.slots[1].reviewed_item_extra_bash_damage == 0.0
    assert result.mechanic_complete is True


def test_bashing_with_unverified_level_or_tier_keeps_partial_value_but_blocks_completeness():
    build = PlayerBuild(Necklace=_bashing_slot(Level="", EnchantTier=""))
    result = ExtremeBashJewelryService(FakeGlyphRepository()).evaluate_build(build)

    assert result.reviewed_item_extra_bash_damage == pytest.approx(180.0)
    assert any("needs verified level/tier scaling" in problem for problem in result.unresolved)
    assert result.mechanic_complete is False


def test_infused_bashing_requires_reviewed_trait_scaling():
    build = PlayerBuild(Necklace=_bashing_slot(Trait="Infused"))
    result = ExtremeBashJewelryService(FakeGlyphRepository()).evaluate_build(build)

    assert result.reviewed_item_extra_bash_damage == 0.0
    assert result.unresolved == (
        "Necklace: Infused jewelry trait repository unavailable",
    )
    assert result.mechanic_complete is False


def test_selected_bashing_enchant_without_canonical_glyph_data_is_explicit_blocker():
    build = PlayerBuild(Necklace=_bashing_slot())
    result = ExtremeBashJewelryService(FakeGlyphRepository(missing=True)).evaluate_build(build)

    assert result.reviewed_item_extra_bash_damage == 0.0
    assert result.unresolved == (
        "Necklace Bashing: canonical bash_damage jewelry glyph not found",
    )
    assert result.mechanic_complete is False
