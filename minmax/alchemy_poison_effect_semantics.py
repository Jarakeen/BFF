from __future__ import annotations

"""Versioned weapon-poison Alchemy trait -> canonical combat-effect relationships.

This module owns relationship identity only. Imported poison tier evidence owns the
effect duration. Existing named-effect authorities own numeric combat semantics.
Poison damage/resource magnitudes, dilution, and non-named effects remain separate.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.combat_effect_semantics import GameUpdate, normalize_game_update
from minmax.support_target_type import SupportTargetType


class PoisonRelationshipKind(str, Enum):
    NAMED_EFFECT = "named_effect"


@dataclass(frozen=True)
class AlchemyPoisonNamedEffectRelationship:
    source_trait: str
    effect_name: str
    target_type: SupportTargetType
    kind: PoisonRelationshipKind = PoisonRelationshipKind.NAMED_EFFECT


# Deliberately narrow Objective #32 relationship set.
#
# These relationships are corroborated for live Update 50. Numeric values are
# intentionally absent: canonical named-effect services own those values.
U50_POISON_NAMED_EFFECT_RELATIONSHIPS: dict[
    str, tuple[AlchemyPoisonNamedEffectRelationship, ...]
] = {
    "Breach": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Breach",
            effect_name="Minor Breach",
            target_type=SupportTargetType.ENEMY,
        ),
    ),
    "Protection": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Protection",
            effect_name="Minor Vulnerability",
            target_type=SupportTargetType.ENEMY,
        ),
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Protection",
            effect_name="Minor Protection",
            target_type=SupportTargetType.SELF,
        ),
    ),
}


def poison_named_effects_for_trait(
    trait: str,
    *,
    game_update: GameUpdate | str = GameUpdate.U50,
) -> tuple[AlchemyPoisonNamedEffectRelationship, ...]:
    update = normalize_game_update(game_update)
    key = " ".join(str(trait or "").strip().casefold().split())
    if not key:
        return ()

    # U51 alchemy relationships are intentionally not inherited from U50.
    if update is not GameUpdate.U50:
        return ()

    for source_trait, relationships in U50_POISON_NAMED_EFFECT_RELATIONSHIPS.items():
        if source_trait.casefold() == key:
            return relationships
    return ()


__all__ = [
    "AlchemyPoisonNamedEffectRelationship",
    "PoisonRelationshipKind",
    "U50_POISON_NAMED_EFFECT_RELATIONSHIPS",
    "poison_named_effects_for_trait",
]
