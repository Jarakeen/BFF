"""
Generic GearSet -> EffectVariant bridge.

The resolver never parses bonus descriptions or invents effect identities.
It asks the canonical known-effect registry for an already-verified mapping.
"""

from __future__ import annotations

from .character_build.effect_instance import EffectVariant
from .gear_set_known_effects import (
    GearSetKnownEffect,
    known_effect_for_bonus_row,
)
from .gear_set_repository import GearSetRepository


class GearSetEffectVariantResolver:
    """Resolve canonical EffectVariants from verified gear-set mappings."""

    def __init__(self, repository: GearSetRepository) -> None:
        self.repository = repository

    def resolve(
        self,
        set_id: int,
        equipped_piece_count: int,
    ) -> list[EffectVariant]:
        if equipped_piece_count <= 0:
            return []

        gear_set = self.repository.get_set_by_id(set_id)
        source_name = gear_set.name if gear_set is not None else f"Set {set_id}"
        bonuses = self.repository.get_bonuses(set_id)

        variants: list[EffectVariant] = []

        for bonus in bonuses:
            if bonus.piece_count > equipped_piece_count:
                continue

            known = known_effect_for_bonus_row(
                bonus.id,
                bonus.set_id,
                source_name,
                bonus.piece_count,
            )
            if known is None:
                continue

            variants.append(
                self._to_effect_variant(known, source_name, bonus.piece_count)
            )

        return variants

    @staticmethod
    def _to_effect_variant(
        known: GearSetKnownEffect,
        source_name: str,
        piece_count: int,
    ) -> EffectVariant:
        return EffectVariant(
            name=known.name,
            layer=known.layer,
            source=f"{source_name} ({piece_count})",
            magnitude=known.magnitude,
            duration=known.duration,
            target_count=known.target_count,
            range=known.range,
            scaling=known.scaling,
            condition=known.condition,
            trigger=known.trigger,
            target_type=known.target_type,
            category=known.category,
            stacking=known.stacking,
            exclusivity_group=known.exclusivity_group,
        )
