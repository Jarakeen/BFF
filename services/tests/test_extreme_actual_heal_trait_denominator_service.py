from __future__ import annotations

from minmax.build_candidate_armor_trait import MODELED_ARMOR_TRAITS
from models.build_model import ARMOR_TRAITS, JEWELRY_TRAITS, WEAPON_TRAITS
from services.extreme_actual_heal_trait_denominator_service import (
    ExtremeActualHealTraitDenominatorService,
)


def _domain(values: list[str]) -> set[str]:
    return {
        str(value or "").strip().casefold()
        for value in values
        if str(value or "").strip()
    }


def test_actual_heal_trait_denominator_accounts_for_every_canonical_trait_value() -> None:
    result = ExtremeActualHealTraitDenominatorService().build()

    assert result.denominator_proven is True
    assert result.unresolved == ()
    assert set(result.armor_traits) == _domain(ARMOR_TRAITS)
    assert set(result.jewelry_traits) == _domain(JEWELRY_TRAITS)
    assert set(result.weapon_traits) == _domain(WEAPON_TRAITS)
    assert result.legal_trait_value_count == 27
    assert result.searched_trait_value_count == 24
    assert result.safely_pruned_trait_value_count == 3


def test_actual_heal_trait_denominator_matches_optimizer_trait_ownership() -> None:
    result = ExtremeActualHealTraitDenominatorService().build()

    assert set(result.searched_armor_traits) == {
        value.casefold() for value in MODELED_ARMOR_TRAITS
    }
    assert set(result.proven_irrelevant_armor_traits) == {
        "sturdy",
        "well-fitted",
        "training",
    }
    assert set(result.searched_jewelry_traits) == _domain(JEWELRY_TRAITS)
    assert set(result.searched_weapon_traits) == _domain(WEAPON_TRAITS)


def test_actual_heal_trait_denominator_has_no_double_counted_armor_disposition() -> None:
    result = ExtremeActualHealTraitDenominatorService().build()

    assert not (
        set(result.searched_armor_traits)
        & set(result.proven_irrelevant_armor_traits)
    )
    assert (
        set(result.searched_armor_traits)
        | set(result.proven_irrelevant_armor_traits)
    ) == set(result.armor_traits)
