from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BlockModifierLayer(str, Enum):
    STANDING_EQUIPMENT = "standing_equipment"
    ACTIVE_BAR_SLOT = "active_bar_slot"
    COMBAT_STATE = "combat_state"
    DAMAGE_FAMILY = "damage_family"


@dataclass(frozen=True)
class BlockModifierClassification:
    source: str
    stat: str
    value: float
    layer: BlockModifierLayer
    activation: str
    stacking_status: str


VERIFIED_BLOCK_MODIFIERS = (
    BlockModifierClassification(
        "Light Armor Penalties",
        "block_cost",
        0.03,
        BlockModifierLayer.STANDING_EQUIPMENT,
        "per Light Armor piece equipped",
        "value and activation verified; global block-cost stacking order unresolved",
    ),
    BlockModifierClassification(
        "Medium Armor Bonuses",
        "block_cost",
        -0.03,
        BlockModifierLayer.STANDING_EQUIPMENT,
        "per Medium Armor piece equipped",
        "value and activation verified; global block-cost stacking order unresolved",
    ),
    BlockModifierClassification(
        "Heavy Armor Bonuses",
        "block_mitigation",
        0.01,
        BlockModifierLayer.STANDING_EQUIPMENT,
        "per Heavy Armor piece equipped",
        "value and activation verified; global block-mitigation stacking order unresolved",
    ),
    BlockModifierClassification(
        "Fortress",
        "block_cost",
        -0.36,
        BlockModifierLayer.STANDING_EQUIPMENT,
        "One Hand and Shield passive owned and one-hand weapon + shield equipped on active bar",
        "value and activation verified; global block-cost stacking order unresolved",
    ),
    BlockModifierClassification(
        "Sword and Board",
        "block_mitigation",
        0.20,
        BlockModifierLayer.STANDING_EQUIPMENT,
        "One Hand and Shield passive owned and one-hand weapon + shield equipped on active bar",
        "value and activation verified; global block-mitigation stacking order unresolved",
    ),
    BlockModifierClassification(
        "Defensive Stance",
        "block_cost",
        -0.10,
        BlockModifierLayer.ACTIVE_BAR_SLOT,
        "Defensive Stance slotted on active bar and shield equipped",
        "value and activation verified; global block-cost stacking order unresolved",
    ),
    BlockModifierClassification(
        "Defensive Stance",
        "block_mitigation",
        0.10,
        BlockModifierLayer.ACTIVE_BAR_SLOT,
        "Defensive Stance slotted on active bar and shield equipped",
        "value and activation verified; global block-mitigation stacking order unresolved",
    ),
    BlockModifierClassification(
        "Bracing Anchor",
        "block_mitigation",
        0.20,
        BlockModifierLayer.COMBAT_STATE,
        "slotted Champion Point active while in combat",
        "combat-state source; must not enter standing sheet automatically",
    ),
    BlockModifierClassification(
        "Deflect Bolts",
        "block_mitigation",
        0.14,
        BlockModifierLayer.DAMAGE_FAMILY,
        "One Hand and Shield equipped; applies only to projectiles and ranged attacks",
        "damage-family-specific; must not enter generic block mitigation",
    ),
)


def modifiers_for(stat: str) -> tuple[BlockModifierClassification, ...]:
    key = str(stat or "").strip().casefold()
    return tuple(entry for entry in VERIFIED_BLOCK_MODIFIERS if entry.stat.casefold() == key)
