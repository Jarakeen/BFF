from __future__ import annotations

"""Audit armor/jewelry trait coverage for Extreme max-resource objectives.

The max-resource search already executes the only armor trait interaction that can
change these objectives directly (Divines versus Infused with resource armor
glyphs), the static resource jewelry traits, and weapon-trait irrelevance.  This
audit owns no stat arithmetic; it proves that every remaining trait in the build
model's canonical trait domains is either searched/accounted for or reviewed as
irrelevant to Max Health, Max Magicka, and Max Stamina.

Unknown future traits fail closed automatically.
"""

from dataclasses import dataclass

from models.build_model import ARMOR_TRAITS, JEWELRY_TRAITS


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")

# Executed by ExtremeArmorResourceTraitGlyphStateService.
_SEARCHED_ARMOR = frozenset({"divines", "infused"})

# These alter mitigation, movement/costs, XP, recovery, or armor rather than a
# maximum resource pool.  They are deliberately reviewed here rather than
# inferred from names at runtime.
_IRRELEVANT_ARMOR = frozenset(
    {
        "reinforced",
        "well-fitted",
        "impenetrable",
        "training",
        "nirnhoned",
        "sturdy",
        "invigorating",
    }
)

# Executed by ExtremeJewelryResourceStaticTraitStateService.
_SEARCHED_JEWELRY = frozenset({"arcane", "healthy", "robust", "protective", "triune"})

# Bloodthirsty changes offensive damage, Harmony changes synergy potency, and
# Swift changes movement speed.  None modifies a maximum resource pool.
_IRRELEVANT_JEWELRY = frozenset({"bloodthirsty", "harmony", "swift"})

# Infused is relevant only through the jewelry enchantment it amplifies.  The
# record layer may close it only together with a proven jewelry-glyph
# irrelevance audit for the requested max-resource objective.
_GLYPH_DEPENDENT_JEWELRY = frozenset({"infused"})


@dataclass(frozen=True)
class ExtremeResourceEquipmentTraitCoverageAudit:
    objective_key: str
    armor_traits_reviewed: tuple[str, ...]
    jewelry_traits_reviewed: tuple[str, ...]
    searched_armor_traits: tuple[str, ...]
    searched_jewelry_traits: tuple[str, ...]
    proven_irrelevant_armor_traits: tuple[str, ...]
    proven_irrelevant_jewelry_traits: tuple[str, ...]
    glyph_dependent_jewelry_traits: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return bool(self.armor_traits_reviewed and self.jewelry_traits_reviewed and not self.unresolved)

    def projection_complete(self, *, jewelry_glyph_irrelevance_proven: bool) -> bool:
        return bool(
            self.denominator_proven
            and (not self.glyph_dependent_jewelry_traits or jewelry_glyph_irrelevance_proven)
        )


class ExtremeResourceEquipmentTraitCoverageAuditService:
    """Classify every canonical armor and jewelry trait for max-resource search."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

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

    def build(self, objective_key: str) -> ExtremeResourceEquipmentTraitCoverageAudit:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource equipment-trait objective: {objective_key!r}")

        armor = self._domain(ARMOR_TRAITS)
        jewelry = self._domain(JEWELRY_TRAITS)
        unresolved: list[str] = []

        classified_armor = _SEARCHED_ARMOR | _IRRELEVANT_ARMOR
        classified_jewelry = _SEARCHED_JEWELRY | _IRRELEVANT_JEWELRY | _GLYPH_DEPENDENT_JEWELRY

        for trait in armor:
            if trait not in classified_armor:
                unresolved.append(f"unreviewed armor trait for max-resource search: {trait}")
        for trait in jewelry:
            if trait not in classified_jewelry:
                unresolved.append(f"unreviewed jewelry trait for max-resource search: {trait}")

        return ExtremeResourceEquipmentTraitCoverageAudit(
            objective_key=key,
            armor_traits_reviewed=armor,
            jewelry_traits_reviewed=jewelry,
            searched_armor_traits=tuple(sorted(_SEARCHED_ARMOR & set(armor))),
            searched_jewelry_traits=tuple(sorted(_SEARCHED_JEWELRY & set(jewelry))),
            proven_irrelevant_armor_traits=tuple(sorted(_IRRELEVANT_ARMOR & set(armor))),
            proven_irrelevant_jewelry_traits=tuple(sorted(_IRRELEVANT_JEWELRY & set(jewelry))),
            glyph_dependent_jewelry_traits=tuple(sorted(_GLYPH_DEPENDENT_JEWELRY & set(jewelry))),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "ExtremeResourceEquipmentTraitCoverageAudit",
    "ExtremeResourceEquipmentTraitCoverageAuditService",
]
