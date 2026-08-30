from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PassiveLayer(str, Enum):
    ABILITY_FAMILY = "ability_family"
    COMBAT_STATE = "combat_state"
    BLOCK_STATE = "block_state"
    EVENT_STATE = "event_state"
    LOCATION_STATE = "location_state"
    NON_COMBAT = "non_combat"


@dataclass(frozen=True)
class PassiveClassification:
    skill_line: str
    name: str
    layer: PassiveLayer
    reason: str


PSIJIC_ORDER_PASSIVES = (
    PassiveClassification("Psijic Order", "See the Unseen", PassiveLayer.NON_COMBAT, "world-interaction utility"),
    PassiveClassification("Psijic Order", "Clairvoyance", PassiveLayer.ABILITY_FAMILY, "reduces Psijic Order ability costs only"),
    PassiveClassification("Psijic Order", "Spell Orb", PassiveLayer.COMBAT_STATE, "requires casting Psijic abilities while in combat and charge accumulation"),
    PassiveClassification("Psijic Order", "Concentrated Barrier", PassiveLayer.BLOCK_STATE, "requires a Psijic ability slotted and Bracing"),
    PassiveClassification("Psijic Order", "Deliberation", PassiveLayer.COMBAT_STATE, "requires casting or channeling a Psijic Order ability"),
)


ASSAULT_PASSIVES = (
    PassiveClassification("Assault", "Continuous Attack", PassiveLayer.EVENT_STATE, "temporary combat bonuses require a recent Alliance War objective capture; Gallop is mount-only"),
    PassiveClassification("Assault", "Reach", PassiveLayer.LOCATION_STATE, "requires keep or outpost proximity and modifies long-range abilities only"),
    PassiveClassification("Assault", "Combat Frenzy", PassiveLayer.EVENT_STATE, "requires killing an enemy player"),
)


def generic_shared_standing_passives() -> tuple[PassiveClassification, ...]:
    """Psijic Order and Assault currently contribute no generic standing sheet passives."""
    return ()
