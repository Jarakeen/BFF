from __future__ import annotations

import pytest

from minmax.build_candidate_armor_enchant import MODELED_ARMOR_ENCHANTS
from minmax.build_candidate_armor_trait import MODELED_ARMOR_TRAITS
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_armor_trait_enchant_frontier_service import (
    ExtremeSustainedDPSArmorTraitEnchantFrontierService,
)


def _build():
    build = PlayerBuild()
    for slot in ("Head", "Chest"):
        build.Armor[slot]["Set"] = "Test Set"
        build.Armor[slot]["Weight"] = "Medium"
        build.Armor[slot]["Quality"] = "Gold"
        build.Armor[slot]["Level"] = "CP160"
        build.Armor[slot]["EnchantTier"] = "Truly Superb"
        build.Armor[slot]["Trait"] = "Divines"
        build.Armor[slot]["Enchant"] = "Max Magicka"
    return build


def test_frontier_counts_full_modeled_product_for_equipped_slots() -> None:
    result = ExtremeSustainedDPSArmorTraitEnchantFrontierService.frontier(_build())

    per_slot = len(MODELED_ARMOR_TRAITS) * len(MODELED_ARMOR_ENCHANTS)
    assert result.denominator_proven is True
    assert len(result.slots) == 2
    assert result.candidate_count == per_slot**2
    assert result.unresolved == ()


def test_candidate_indexing_is_deterministic_mixed_radix() -> None:
    build = _build()
    first = ExtremeSustainedDPSArmorTraitEnchantFrontierService.candidate_at(build, 0)
    last = ExtremeSustainedDPSArmorTraitEnchantFrontierService.candidate_at(
        build,
        ExtremeSustainedDPSArmorTraitEnchantFrontierService.frontier(build).candidate_count - 1,
    )

    assert first.slot_choices[0] == (
        "Head",
        MODELED_ARMOR_TRAITS[0],
        MODELED_ARMOR_ENCHANTS[0],
    )
    assert first.slot_choices[1] == (
        "Chest",
        MODELED_ARMOR_TRAITS[0],
        MODELED_ARMOR_ENCHANTS[0],
    )
    assert last.slot_choices[0] == (
        "Head",
        MODELED_ARMOR_TRAITS[-1],
        MODELED_ARMOR_ENCHANTS[-1],
    )
    assert last.slot_choices[1] == (
        "Chest",
        MODELED_ARMOR_TRAITS[-1],
        MODELED_ARMOR_ENCHANTS[-1],
    )


def test_page_does_not_materialize_entire_frontier() -> None:
    rows = ExtremeSustainedDPSArmorTraitEnchantFrontierService.page(
        _build(),
        offset=3,
        limit=4,
    )

    assert tuple(row.structural_index for row in rows) == (3, 4, 5, 6)


def test_noneligible_enchant_slot_retains_existing_enchant_only() -> None:
    build = _build()
    build.Armor["Chest"]["EnchantTier"] = ""
    build.Armor["Chest"]["Enchant"] = "Legacy Enchant"

    result = ExtremeSustainedDPSArmorTraitEnchantFrontierService.frontier(build)
    chest = next(row for row in result.slots if row.slot == "Chest")

    assert chest.enchant_axis_active is False
    assert chest.enchant_choices == ("Legacy Enchant",)
    assert result.candidate_count == (
        len(MODELED_ARMOR_TRAITS)
        * len(MODELED_ARMOR_ENCHANTS)
        * len(MODELED_ARMOR_TRAITS)
    )


def test_unequipped_slots_do_not_expand_denominator() -> None:
    build = _build()
    result = ExtremeSustainedDPSArmorTraitEnchantFrontierService.frontier(build)

    assert tuple(row.slot for row in result.slots) == ("Head", "Chest")


def test_invalid_candidate_index_fails_closed() -> None:
    build = _build()
    count = ExtremeSustainedDPSArmorTraitEnchantFrontierService.frontier(build).candidate_count

    with pytest.raises(IndexError):
        ExtremeSustainedDPSArmorTraitEnchantFrontierService.candidate_at(build, -1)
    with pytest.raises(IndexError):
        ExtremeSustainedDPSArmorTraitEnchantFrontierService.candidate_at(build, count)


def test_empty_armor_frontier_is_unproven() -> None:
    build = PlayerBuild()
    result = ExtremeSustainedDPSArmorTraitEnchantFrontierService.frontier(build)

    assert result.denominator_proven is False
    assert result.candidate_count == 1
    assert result.unresolved


def test_armor_trait_enchant_frontier_rejects_boolean_candidate_index() -> None:
    with pytest.raises(TypeError, match="candidate index must be an integer"):
        ExtremeSustainedDPSArmorTraitEnchantFrontierService.candidate_at(
            _build(),
            True,
        )


@pytest.mark.parametrize("field,value", (("offset", False), ("limit", "4"), ("offset", 2.5)))
def test_armor_trait_enchant_page_requires_strict_integer_bounds(field, value) -> None:
    kwargs = {"offset": 0, "limit": 4}
    kwargs[field] = value

    with pytest.raises(TypeError, match=f"armor trait/enchant page {field} must be an integer"):
        ExtremeSustainedDPSArmorTraitEnchantFrontierService.page(
            _build(),
            **kwargs,
        )
