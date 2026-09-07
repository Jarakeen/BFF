from __future__ import annotations

import pytest

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_enchantment_objective_service import (
    ExtremeEnchantmentObjectiveService,
)


class _JewelryRepo:
    def list_names(self):
        return ("Glyph of Magicka Recovery", "Glyph of Increase Magical Harm", "Mystery Glyph")

    def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
        assert use_max_value is True
        if name == "Glyph of Magicka Recovery":
            return [
                Effect(
                    source=name,
                    stat=StatId.MAGICKA_RECOVERY,
                    operation=EffectOperation.ADD,
                    value=169.0,
                    unit=EffectUnit.FLAT,
                )
            ]
        if name == "Glyph of Increase Magical Harm":
            return [
                Effect(
                    source=name,
                    stat=StatId.SPELL_DAMAGE,
                    operation=EffectOperation.ADD,
                    value=174.0,
                    unit=EffectUnit.FLAT,
                )
            ]
        return [
            Effect(
                source=name,
                stat=StatId.SPELL_DAMAGE,
                operation=EffectOperation.ADD_PERCENT,
                value=10.0,
                unit=EffectUnit.PERCENT,
            )
        ]


class _ArmorRepo:
    def list_names(self):
        return ("Glyph of Health", "Glyph of Magicka")

    def get_armor_glyph_effect_by_name(self, name, *, use_max_value=True):
        stat = StatId.MAX_HEALTH if name == "Glyph of Health" else StatId.MAX_MAGICKA
        return [
            Effect(
                source=name,
                stat=stat,
                operation=EffectOperation.ADD,
                value=868.0,
                unit=EffectUnit.FLAT,
            )
        ]


def test_best_jewelry_glyph_projects_static_recovery():
    best = ExtremeEnchantmentObjectiveService.best_jewelry_for_objective(
        _JewelryRepo(),
        "magicka_recovery",
    )

    assert best is not None
    assert best.glyph_name == "Glyph of Magicka Recovery"
    assert best.projected_delta == pytest.approx(169.0)
    assert best.unresolved == ()


def test_jewelry_multiplier_applies_to_static_damage_glyph():
    row = ExtremeEnchantmentObjectiveService.jewelry_candidate(
        _JewelryRepo(),
        "Glyph of Increase Magical Harm",
        "spell_damage",
        multiplier=1.6,
    )

    assert row.projected_delta == pytest.approx(278.4)


def test_three_jewelry_slots_are_jointly_projected_without_assuming_trait_values():
    loadout = ExtremeEnchantmentObjectiveService.best_three_jewelry_loadout(
        _JewelryRepo(),
        "spell_damage",
        slot_multipliers=(1.0, 1.6, 1.6),
    )

    assert loadout is not None
    assert loadout.glyph_name == "Glyph of Increase Magical Harm"
    assert loadout.projected_delta == pytest.approx(174.0 * 4.2)


def test_relevant_unmapped_percent_effect_is_explicit_blocker_not_zero():
    row = ExtremeEnchantmentObjectiveService.jewelry_candidate(
        _JewelryRepo(),
        "Mystery Glyph",
        "spell_damage",
    )

    assert row.projected_delta is None
    assert row.unresolved
    assert "stacking review" in row.unresolved[0]


def test_armor_glyph_irrelevant_to_current_objective_is_zero_not_unresolved():
    row = ExtremeEnchantmentObjectiveService.armor_candidate(
        _ArmorRepo(),
        "Glyph of Health",
        "physical_resistance",
    )

    assert row.projected_delta == 0.0
    assert row.unresolved == ()


def test_invalid_multiplier_and_unknown_objective_fail_closed():
    with pytest.raises(ValueError, match="non-negative"):
        ExtremeEnchantmentObjectiveService.jewelry_candidate(
            _JewelryRepo(),
            "Glyph of Magicka Recovery",
            "magicka_recovery",
            multiplier=-1.0,
        )

    with pytest.raises(KeyError, match="unreviewed Extreme enchantment objective"):
        ExtremeEnchantmentObjectiveService.jewelry_candidate(
            _JewelryRepo(),
            "Glyph of Magicka Recovery",
            "max_health",
        )

    with pytest.raises(ValueError, match="three non-negative"):
        ExtremeEnchantmentObjectiveService.best_three_jewelry_loadout(
            _JewelryRepo(),
            "spell_damage",
            slot_multipliers=(1.0, 1.0),  # type: ignore[arg-type]
        )
