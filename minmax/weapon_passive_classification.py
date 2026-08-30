from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WeaponPassiveLayer(str, Enum):
    SHARED_STANDING = "shared_standing"
    ABILITY_FAMILY = "ability_family"
    COMBAT_STATE = "combat_state"
    BLOCK_STATE = "block_state"
    STATUS_STATE = "status_state"


@dataclass(frozen=True)
class WeaponPassiveRule:
    skill_line: str
    passive: str
    layer: WeaponPassiveLayer
    reason: str


VERIFIED_WEAPON_PASSIVE_RULES: tuple[WeaponPassiveRule, ...] = (
    WeaponPassiveRule(
        "Restoration Staff",
        "Restoration Master",
        WeaponPassiveLayer.ABILITY_FAMILY,
        "Increases healing with Restoration Staff spells by 5%; not generic Healing Done.",
    ),
    WeaponPassiveRule(
        "Restoration Staff",
        "Restoration Expert",
        WeaponPassiveLayer.ABILITY_FAMILY,
        "Increases healing only on allies under 30% Health.",
    ),
    WeaponPassiveRule(
        "Restoration Staff",
        "Essence Drain",
        WeaponPassiveLayer.COMBAT_STATE,
        "Major Mending and ally/self heal occur after a fully-charged Heavy Attack.",
    ),
    WeaponPassiveRule(
        "Restoration Staff",
        "Cycle of Life",
        WeaponPassiveLayer.COMBAT_STATE,
        "Changes Magicka restored by fully-charged Heavy Attacks.",
    ),
    WeaponPassiveRule(
        "Restoration Staff",
        "Absorb",
        WeaponPassiveLayer.BLOCK_STATE,
        "Restores Magicka when blocking an attack.",
    ),
    WeaponPassiveRule(
        "Destruction Staff",
        "Penetrating Magic",
        WeaponPassiveLayer.ABILITY_FAMILY,
        "Spell Resistance ignore applies to Destruction Staff abilities, not generic character penetration.",
    ),
    WeaponPassiveRule(
        "Destruction Staff",
        "Elemental Force",
        WeaponPassiveLayer.STATUS_STATE,
        "Modifies status-effect application chance rather than a shared character-sheet stat.",
    ),
    WeaponPassiveRule(
        "Destruction Staff",
        "Ancient Knowledge",
        WeaponPassiveLayer.ABILITY_FAMILY,
        "Effect depends on staff element and damage/effect family; Ice Staff portion modifies blocking.",
    ),
    WeaponPassiveRule(
        "Destruction Staff",
        "Tri Focus",
        WeaponPassiveLayer.BLOCK_STATE,
        "Ice Staff changes blocking resource and Heavy Attack effects; other staff effects are Heavy-Attack specific.",
    ),
    WeaponPassiveRule(
        "Destruction Staff",
        "Destruction Expert",
        WeaponPassiveLayer.COMBAT_STATE,
        "Resource restoration requires a kill or Destruction Staff damage-shield absorption event.",
    ),
)


def shared_standing_weapon_passives(skill_line: str) -> tuple[WeaponPassiveRule, ...]:
    key = str(skill_line or "").strip().casefold()
    return tuple(
        rule
        for rule in VERIFIED_WEAPON_PASSIVE_RULES
        if rule.skill_line.casefold() == key and rule.layer is WeaponPassiveLayer.SHARED_STANDING
    )
