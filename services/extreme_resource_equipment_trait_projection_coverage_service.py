from __future__ import annotations

"""Compose proof that every max-resource equipment-trait family is covered.

This service owns no ESO stat arithmetic. It combines the authoritative armor and
jewelry trait-domain audit with the existing canonical static-jewelry, jewelry-glyph,
and weapon trait/enchantment evidence. Armor Divines/Infused execution remains
owned by the resource armor catalog and is checked by the scorer that owns that
catalog.
"""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_jewelry_resource_glyph_relevance_service import (
    ExtremeJewelryResourceGlyphRelevanceService,
)
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)
from services.extreme_resource_equipment_trait_coverage_audit_service import (
    ExtremeResourceEquipmentTraitCoverageAuditService,
)
from services.extreme_weapon_resource_relevance_service import (
    ExtremeWeaponResourceRelevanceService,
)


@dataclass(frozen=True)
class ExtremeResourceEquipmentTraitProjectionCoverage:
    objective_key: str
    trait_domain_denominator_proven: bool
    jewelry_static_trait_denominator_proven: bool
    jewelry_glyph_irrelevance_proven: bool
    weapon_irrelevance_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.trait_domain_denominator_proven
            and self.jewelry_static_trait_denominator_proven
            and self.jewelry_glyph_irrelevance_proven
            and self.weapon_irrelevance_proven
            and not self.unresolved
        )


class ExtremeResourceEquipmentTraitProjectionCoverageService:
    """Compose the non-armor-catalog half of equipment-trait proof."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def build(self, objective_key: str) -> ExtremeResourceEquipmentTraitProjectionCoverage:
        key = str(objective_key or "").strip().casefold()
        trait_audit = ExtremeResourceEquipmentTraitCoverageAuditService().build(key)
        jewelry_catalog = ExtremeJewelryResourceStaticTraitStateService(
            self.database_path
        ).build(key)
        jewelry_glyph = ExtremeJewelryResourceGlyphRelevanceService(
            self.database_path
        ).build(key)
        weapon = ExtremeWeaponResourceRelevanceService(self.database_path).build(key)

        unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (
                    *trait_audit.unresolved,
                    *jewelry_catalog.unresolved,
                    *jewelry_glyph.unresolved,
                    *weapon.unresolved,
                )
                if str(item)
            )
        )
        trait_projection_complete = trait_audit.projection_complete(
            jewelry_glyph_irrelevance_proven=bool(
                jewelry_glyph.objective_irrelevance_proven
            )
        )

        return ExtremeResourceEquipmentTraitProjectionCoverage(
            objective_key=key,
            trait_domain_denominator_proven=bool(trait_projection_complete),
            jewelry_static_trait_denominator_proven=bool(
                jewelry_catalog.denominator_proven and len(jewelry_catalog.states) == 1
            ),
            jewelry_glyph_irrelevance_proven=bool(
                jewelry_glyph.denominator_proven
                and jewelry_glyph.objective_irrelevance_proven
            ),
            weapon_irrelevance_proven=bool(
                weapon.denominator_proven and weapon.objective_irrelevance_proven
            ),
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeResourceEquipmentTraitProjectionCoverage",
    "ExtremeResourceEquipmentTraitProjectionCoverageService",
]
