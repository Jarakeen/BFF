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
    "Increase Weapon Power": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Increase Weapon Power",
            effect_name="Minor Maim",
            target_type=SupportTargetType.ENEMY,
        ),
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Increase Weapon Power",
            effect_name="Minor Brutality",
            target_type=SupportTargetType.SELF,
        ),
    ),
    "Increase Spell Power": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Increase Spell Power",
            effect_name="Minor Cowardice",
            target_type=SupportTargetType.ENEMY,
        ),
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Increase Spell Power",
            effect_name="Minor Sorcery",
            target_type=SupportTargetType.SELF,
        ),
    ),
    "Weapon Critical": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Weapon Critical",
            effect_name="Minor Enervation",
            target_type=SupportTargetType.ENEMY,
        ),
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Weapon Critical",
            effect_name="Minor Savagery",
            target_type=SupportTargetType.SELF,
        ),
    ),
    "Spell Critical": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Spell Critical",
            effect_name="Minor Uncertainty",
            target_type=SupportTargetType.ENEMY,
        ),
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Spell Critical",
            effect_name="Minor Prophecy",
            target_type=SupportTargetType.SELF,
        ),
    ),
    "Defile": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Defile",
            effect_name="Minor Defile",
            target_type=SupportTargetType.ENEMY,
        ),
    ),
    "Vitality": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Vitality",
            effect_name="Minor Defile",
            target_type=SupportTargetType.ENEMY,
        ),
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Vitality",
            effect_name="Minor Vitality",
            target_type=SupportTargetType.SELF,
        ),
    ),
    "Maim": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Maim",
            effect_name="Minor Maim",
            target_type=SupportTargetType.ENEMY,
        ),
    ),
    "Cowardice": (
        AlchemyPoisonNamedEffectRelationship(
            source_trait="Cowardice",
            effect_name="Minor Cowardice",
            target_type=SupportTargetType.ENEMY,
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
