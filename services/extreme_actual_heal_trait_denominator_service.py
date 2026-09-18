from __future__ import annotations

"""Prove the per-slot legal trait-value denominator for Extreme MOST Actual Heal.

This service owns no healing math.  It reconciles the canonical build-model trait
domains against the trait families that the H1 optimizer actually searches, plus
three armor traits whose reviewed effects cannot change the magnitude of one
healing event.

The proof is deliberately per-slot/value.  It does not claim that the current
coordinate search has exhaustively enumerated the Cartesian product of every
trait assignment across every equipped slot; that broader search-space proof
remains an E4 concern.
"""

from dataclasses import dataclass

from minmax.build_candidate_armor_trait import MODELED_ARMOR_TRAITS
from models.build_model import ARMOR_TRAITS, JEWELRY_TRAITS, WEAPON_TRAITS


# These canonical armor traits alter block cost, movement/dodge/sprint cost, or
# experience gain.  None changes Max Resource, Weapon/Spell Damage, Healing Done,
# Critical Healing, or the coefficient of a single reviewed H1 heal event.
_H1_PROVEN_IRRELEVANT_ARMOR = frozenset(
    {
        "sturdy",
        "well-fitted",
        "training",
    }
)


@dataclass(frozen=True)
class ExtremeActualHealTraitDenominator:
    armor_traits: tuple[str, ...]
    jewelry_traits: tuple[str, ...]
    weapon_traits: tuple[str, ...]
    searched_armor_traits: tuple[str, ...]
    searched_jewelry_traits: tuple[str, ...]
    searched_weapon_traits: tuple[str, ...]
    proven_irrelevant_armor_traits: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def legal_trait_value_count(self) -> int:
        return len(self.armor_traits) + len(self.jewelry_traits) + len(self.weapon_traits)

    @property
    def searched_trait_value_count(self) -> int:
        return (
            len(self.searched_armor_traits)
            + len(self.searched_jewelry_traits)
            + len(self.searched_weapon_traits)
        )

    @property
    def safely_pruned_trait_value_count(self) -> int:
        return len(self.proven_irrelevant_armor_traits)

    @property
    def denominator_proven(self) -> bool:
        return bool(
            self.legal_trait_value_count
            and not self.unresolved
            and self.legal_trait_value_count
            == self.searched_trait_value_count + self.safely_pruned_trait_value_count
        )


class ExtremeActualHealTraitDenominatorService:
    """Reconcile every canonical armor/jewelry/weapon trait for H1."""

    @staticmethod
    def _domain(values: list[str]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(value or "").strip().casefold()
                    for value in values
                    if str(value or "").strip()
                }
            )
        )

    def build(self) -> ExtremeActualHealTraitDenominator:
        armor = self._domain(ARMOR_TRAITS)
        jewelry = self._domain(JEWELRY_TRAITS)
        weapon = self._domain(WEAPON_TRAITS)

        searched_armor = frozenset(
            str(value or "").strip().casefold()
            for value in MODELED_ARMOR_TRAITS
            if str(value or "").strip()
        )
        searched_jewelry = frozenset(jewelry)
        searched_weapon = frozenset(weapon)

        unresolved: list[str] = []

        overlap = searched_armor & _H1_PROVEN_IRRELEVANT_ARMOR
        if overlap:
            unresolved.append(
                "H1 armor trait disposition overlap: " + ", ".join(sorted(overlap))
            )

        classified_armor = searched_armor | _H1_PROVEN_IRRELEVANT_ARMOR
        for trait in armor:
            if trait not in classified_armor:
                unresolved.append(f"unreviewed armor trait for H1: {trait}")
        for trait in searched_armor | _H1_PROVEN_IRRELEVANT_ARMOR:
            if trait not in armor:
                unresolved.append(f"stale H1 armor trait disposition: {trait}")

        # Jewelry and weapon candidate generation iterate the canonical nonblank
        # model domains directly.  If those model domains grow, they enter the H1
        # search automatically rather than silently falling outside this ledger.
        return ExtremeActualHealTraitDenominator(
            armor_traits=armor,
            jewelry_traits=jewelry,
            weapon_traits=weapon,
            searched_armor_traits=tuple(sorted(searched_armor & set(armor))),
            searched_jewelry_traits=tuple(sorted(searched_jewelry)),
            searched_weapon_traits=tuple(sorted(searched_weapon)),
            proven_irrelevant_armor_traits=tuple(
                sorted(_H1_PROVEN_IRRELEVANT_ARMOR & set(armor))
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeActualHealTraitDenominator",
    "ExtremeActualHealTraitDenominatorService",
]
