from __future__ import annotations

"""Audit static enchantment-family coverage for Extreme MOST Actual Heal.

Armor and jewelry glyphs are static equipment choices. Weapon enchantments are
intentionally not folded into this proof because their value depends on proc,
cooldown, trigger, and combat-state evidence; those remain in the runtime/weapon
configuration boundary.

This service does not score healing. It proves whether every canonical static
glyph family is either searched by H1, reviewed as irrelevant to one heal-event
magnitude, or left explicitly unresolved.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.armor_glyph_repository import ArmorGlyphEffectRepository
from minmax.build_candidate_armor_enchant import MODELED_ARMOR_ENCHANTS
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from services.build_enchant_catalog_service import BuildEnchantCatalogService


_H1_SEARCHED_JEWELRY_LABELS = frozenset(
    {
        "weapon damage",
        "spell damage",
        "magicka recovery",
        "stamina recovery",
        "health recovery",
    }
)

# Reviewed jewelry-glyph semantic families that cannot change the magnitude of
# one instantaneous H1 heal event. Cost/cooldown/recovery/bash/block mechanics
# matter elsewhere, but not to the selected event's coefficient/output.
_H1_IRRELEVANT_JEWELRY_EFFECT_TYPES = frozenset(
    {
        "health_recovery",
        "magicka_recovery",
        "stamina_recovery",
        "bash_damage",
        "block_cost_reduction",
        "potion_cooldown_reduction",
        "potion_duration",
        "magicka_cost_reduction",
        "stamina_cost_reduction",
        "health_cost_reduction",
        "resource_cost_reduction",
        "physical_resistance",
        "spell_resistance",
        "disease_resistance",
        "flame_resistance",
        "frost_resistance",
        "poison_resistance",
        "shock_resistance",
    }
)

# A few legacy Build labels are presentation aliases rather than canonical glyph
# family names.  These are mechanically reviewed as irrelevant to the magnitude
# of one instantaneous H1 healing event, so they may be dispositioned without
# asking the repository to resolve a display alias as if it were canonical data.
_H1_IRRELEVANT_JEWELRY_LABELS = frozenset(
    {
        "bashing",
        "block cost",
        "glyph of bashing",
        "glyph of bracing",
        "glyph of disease resist",
        "glyph of flame resist",
        "glyph of frost resist",
        "glyph of poison resist",
        "glyph of shock resist",
        "glyph of potion boost",
        "glyph of reduce skill cost",
        "glyph of decrease physical harm",
        "glyph of decrease spell harm",
    }
)

_H1_RELEVANT_JEWELRY_EFFECT_TYPES = frozenset(
    {
        "weapon_damage",
        "spell_damage",
        "weapon_spell_damage",
        "max_magicka",
        "max_stamina",
        "healing_done",
        "critical_healing",
    }
)


@dataclass(frozen=True)
class ExtremeActualHealStaticEnchantDenominator:
    armor_families: tuple[str, ...]
    jewelry_families: tuple[str, ...]
    searched_armor_families: tuple[str, ...]
    searched_jewelry_families: tuple[str, ...]
    irrelevant_jewelry_families: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def static_family_count(self) -> int:
        return len(self.armor_families) + len(self.jewelry_families)

    @property
    def accounted_family_count(self) -> int:
        return (
            len(self.searched_armor_families)
            + len(self.searched_jewelry_families)
            + len(self.irrelevant_jewelry_families)
        )

    @property
    def denominator_proven(self) -> bool:
        return bool(
            self.static_family_count
            and not self.unresolved
            and self.static_family_count == self.accounted_family_count
        )


class ExtremeActualHealStaticEnchantDenominatorService:
    def __init__(
        self,
        database_path: str | Path,
        *,
        armor_repository: ArmorGlyphEffectRepository | None = None,
        jewelry_repository: JewelryGlyphEffectRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.armor = armor_repository or ArmorGlyphEffectRepository(self.database_path)
        self.jewelry = jewelry_repository or JewelryGlyphEffectRepository(self.database_path)

    @staticmethod
    def _normalized(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    " ".join(str(value or "").strip().split()).casefold()
                    for value in values
                    if str(value or "").strip()
                }
            )
        )

    def build(self) -> ExtremeActualHealStaticEnchantDenominator:
        catalog = BuildEnchantCatalogService(
            self.database_path,
            armor_repository=self.armor,
            jewelry_repository=self.jewelry,
        )
        armor = self._normalized(tuple(catalog.armor_choices()))
        jewelry = self._normalized(tuple(catalog.jewelry_choices()))

        searched_armor_domain = {
            str(value or "").strip().casefold() for value in MODELED_ARMOR_ENCHANTS
        }
        searched_armor = tuple(sorted(set(armor) & searched_armor_domain))

        unresolved: list[str] = []
        for family in armor:
            if family not in searched_armor_domain:
                unresolved.append(
                    f"unreviewed armor glyph family for H1 static search: {family}"
                )

        searched_jewelry: list[str] = []
        irrelevant_jewelry: list[str] = []
        for family in jewelry:
            if family in _H1_SEARCHED_JEWELRY_LABELS:
                searched_jewelry.append(family)
                continue
            if family in _H1_IRRELEVANT_JEWELRY_LABELS:
                irrelevant_jewelry.append(family)
                continue

            effect_types = tuple(
                str(value or "").strip().casefold()
                for value in self.jewelry.get_jewelry_glyph_effect_types_by_name(family)
                if str(value or "").strip()
            )
            if not effect_types:
                unresolved.append(
                    f"jewelry glyph family has no semantic effect identity for H1: {family}"
                )
                continue

            semantic_set = set(effect_types)
            relevant = semantic_set & _H1_RELEVANT_JEWELRY_EFFECT_TYPES
            unknown = semantic_set - (
                _H1_RELEVANT_JEWELRY_EFFECT_TYPES
                | _H1_IRRELEVANT_JEWELRY_EFFECT_TYPES
            )
            if relevant:
                unresolved.append(
                    f"H1-relevant jewelry glyph family is not searched: {family} "
                    f"({', '.join(sorted(relevant))})"
                )
            elif unknown:
                unresolved.append(
                    f"unreviewed jewelry glyph semantics for H1: {family} "
                    f"({', '.join(sorted(unknown))})"
                )
            else:
                irrelevant_jewelry.append(family)

        return ExtremeActualHealStaticEnchantDenominator(
            armor_families=armor,
            jewelry_families=jewelry,
            searched_armor_families=searched_armor,
            searched_jewelry_families=tuple(sorted(searched_jewelry)),
            irrelevant_jewelry_families=tuple(sorted(irrelevant_jewelry)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeActualHealStaticEnchantDenominator",
    "ExtremeActualHealStaticEnchantDenominatorService",
]
