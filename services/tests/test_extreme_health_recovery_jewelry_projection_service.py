import pytest

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_health_recovery_jewelry_projection_service import (
    ExtremeHealthRecoveryJewelryProjectionService,
)


class _GlyphRepository:
    def list_names(self):
        return ("Glyph of Health Recovery", "Glyph of Magicka Recovery")

    def get_jewelry_glyph_effect_types_by_name(self, name):
        if name == "Glyph of Health Recovery":
            return ("health_recovery",)
        return ("magicka_recovery",)

    def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
        if name == "Glyph of Health Recovery":
            return [
                Effect(
                    source=name,
                    stat=StatId.HEALTH_RECOVERY,
                    operation=EffectOperation.ADD,
                    value=169.0,
                    unit=EffectUnit.FLAT,
                )
            ]
        return [
            Effect(
                source=name,
                stat=StatId.MAGICKA_RECOVERY,
                operation=EffectOperation.ADD,
                value=169.0,
                unit=EffectUnit.FLAT,
            )
        ]


class _TraitRepository:
    def get_infused_enchantment_percent(self, quality):
        assert quality == "Gold"
        return 60.0


def test_projects_strongest_health_recovery_glyph_with_three_gold_infused_slots():
    result = ExtremeHealthRecoveryJewelryProjectionService(
        _GlyphRepository(),
        _TraitRepository(),
    ).build()

    assert result.denominator_proven is True
    assert result.glyphs_reviewed == 2
    assert result.relevant_glyphs == ("Glyph of Health Recovery",)
    assert result.strongest_glyph_name == "Glyph of Health Recovery"
    assert result.base_flat_per_slot == pytest.approx(169.0)
    assert result.infused_percent == pytest.approx(60.0)
    assert result.infused_flat_per_slot == pytest.approx(270.4)
    assert result.three_slot_infused_flat == pytest.approx(811.2)
    assert result.unresolved == ()
