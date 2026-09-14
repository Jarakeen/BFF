import pytest

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_recovery_jewelry_projection_service import (
    ExtremeRecoveryJewelryProjectionService,
)


class _GlyphRepository:
    def list_names(self):
        return (
            "Glyph of Health Recovery",
            "Glyph of Magicka Recovery",
            "Glyph of Stamina Recovery",
        )

    def get_jewelry_glyph_effect_types_by_name(self, name):
        return {
            "Glyph of Health Recovery": ("health_recovery",),
            "Glyph of Magicka Recovery": ("magicka_recovery",),
            "Glyph of Stamina Recovery": ("stamina_recovery",),
        }[name]

    def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
        stat = {
            "Glyph of Health Recovery": StatId.HEALTH_RECOVERY,
            "Glyph of Magicka Recovery": StatId.MAGICKA_RECOVERY,
            "Glyph of Stamina Recovery": StatId.STAMINA_RECOVERY,
        }[name]
        return [
            Effect(
                source=name,
                stat=stat,
                operation=EffectOperation.ADD,
                value=169.0,
                unit=EffectUnit.FLAT,
            )
        ]


class _TraitRepository:
    def get_infused_enchantment_percent(self, quality):
        assert quality == "Gold"
        return 60.0


def test_projects_magicka_recovery_with_three_gold_infused_slots():
    result = ExtremeRecoveryJewelryProjectionService(
        _GlyphRepository(),
        _TraitRepository(),
    ).build("magicka_recovery")

    assert result.denominator_proven is True
    assert result.objective_key == "magicka_recovery"
    assert result.relevant_glyphs == ("Glyph of Magicka Recovery",)
    assert result.strongest_glyph_name == "Glyph of Magicka Recovery"
    assert result.base_flat_per_slot == pytest.approx(169.0)
    assert result.infused_percent == pytest.approx(60.0)
    assert result.infused_flat_per_slot == pytest.approx(270.4)
    assert result.three_slot_infused_flat == pytest.approx(811.2)
    assert result.unresolved == ()


def test_unknown_recovery_objective_fails_closed():
    result = ExtremeRecoveryJewelryProjectionService(
        _GlyphRepository(),
        _TraitRepository(),
    ).build("spell_damage")

    assert result.denominator_proven is False
    assert result.unresolved == ("Unsupported Recovery jewelry objective: 'spell_damage'",)
