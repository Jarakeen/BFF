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


class _SemanticJewelryRepo:
    def list_names(self):
        return ("Glyph of Bracing", "Glyph of Magicka Recovery")

    def get_jewelry_glyph_effect_types_by_name(self, name):
        if name == "Glyph of Bracing":
            return ("block_cost_reduction",)
        return ("magicka_recovery",)

    def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
        assert use_max_value is True
        if name == "Glyph of Bracing":
            raise ValueError("Unsupported engine stat effect type: 'block_cost_reduction'")
        return [
            Effect(
                source=name,
                stat=StatId.MAGICKA_RECOVERY,
                operation=EffectOperation.ADD,
                value=169.0,
                unit=EffectUnit.FLAT,
            )
        ]


class _RelevantUnmappedJewelryRepo:
    def get_jewelry_glyph_effect_types_by_name(self, name):
        return ("magicka_recovery", "future_unmapped_semantic")

    def get_jewelry_glyph_effect_by_name(self, name, *, use_max_value=True):
        raise ValueError("Unsupported engine stat effect type: 'future_unmapped_semantic'")


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


def test_irrelevant_unmapped_jewelry_semantics_do_not_poison_recovery_search():
    rows = ExtremeEnchantmentObjectiveService.jewelry_candidates_for_objective(
        _SemanticJewelryRepo(),
        "magicka_recovery",
    )
    by_name = {row.glyph_name: row for row in rows}

    assert by_name["Glyph of Bracing"].projected_delta == 0.0
    assert by_name["Glyph of Bracing"].unresolved == ()
    assert by_name["Glyph of Magicka Recovery"].projected_delta == pytest.approx(169.0)


def test_relevant_unmapped_jewelry_semantic_remains_explicit_blocker():
    row = ExtremeEnchantmentObjectiveService.jewelry_candidate(
        _RelevantUnmappedJewelryRepo(),
        "Future Mixed Glyph",
        "magicka_recovery",
    )

    assert row.projected_delta is None
    assert row.unresolved
    assert "future_unmapped_semantic" in row.unresolved[0]


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
