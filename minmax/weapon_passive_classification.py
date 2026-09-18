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
    WeaponPassiveRule(
        "Bow",
        "Accuracy",
        WeaponPassiveLayer.SHARED_STANDING,
        "Increases Critical Chance rating while a Bow is equipped; H1 Actual Heal does not use critical chance to scale a proven critical event.",
    ),
    WeaponPassiveRule(
        "Bow",
        "Vinedusk Training",
        WeaponPassiveLayer.COMBAT_STATE,
        "Distance-dependent damage-done or Critical Chance bonuses affect enemy damage/crit probability, not one H1 healing-event magnitude.",
    ),
    WeaponPassiveRule(
        "Bow",
        "Hawk Eye",
        WeaponPassiveLayer.COMBAT_STATE,
        "Light/Heavy Attack stacks increase Bow ability damage only; they do not scale healing events.",
    ),
    WeaponPassiveRule(
        "Bow",
        "Hasty Retreat",
        WeaponPassiveLayer.COMBAT_STATE,
        "Roll Dodge grants Major Expedition; movement speed does not scale one healing event.",
    ),
    WeaponPassiveRule(
        "Bow",
        "Ranger",
        WeaponPassiveLayer.ABILITY_FAMILY,
        "Reduces the Stamina cost of Bow abilities; does not modify Max Stamina.",
    ),
    WeaponPassiveRule(
        "Dual Wield",
        "Ambidextrous",
        WeaponPassiveLayer.SHARED_STANDING,
        "Increases Weapon and Spell Damage from the off-hand weapon; does not modify maximum resources.",
    ),
    WeaponPassiveRule(
        "Dual Wield",
        "Twin Blade and Blunt",
        WeaponPassiveLayer.SHARED_STANDING,
        "Weapon-subtype standing bonuses include sword Weapon/Spell Damage and therefore can change H1 heal scaling; subtype search must preserve this passive.",
    ),
    WeaponPassiveRule(
        "Dual Wield",
        "Controlled Fury",
        WeaponPassiveLayer.ABILITY_FAMILY,
        "Reduces the Stamina cost of Dual Wield abilities; does not modify Max Stamina.",
    ),
    WeaponPassiveRule(
        "Dual Wield",
        "Focused Killer",
        WeaponPassiveLayer.COMBAT_STATE,
        "Increases Dual Wield ability damage against low-Health enemies; does not modify maximum resources.",
    ),
    WeaponPassiveRule(
        "Dual Wield",
        "Ruffian",
        WeaponPassiveLayer.COMBAT_STATE,
        "Increases Dual Wield attack damage against controlled enemies; does not modify maximum resources.",
    ),
    WeaponPassiveRule(
        "One Hand and Shield",
        "Deadly Bash",
        WeaponPassiveLayer.ABILITY_FAMILY,
        "Improves Bash damage/cost only; it does not scale a healing event.",
    ),
    WeaponPassiveRule(
        "One Hand and Shield",
        "Deflect Bolts",
        WeaponPassiveLayer.BLOCK_STATE,
        "Changes blocked projectile/ranged damage only; it does not scale a healing event.",
    ),
    WeaponPassiveRule(
        "One Hand and Shield",
        "Fortress",
        WeaponPassiveLayer.BLOCK_STATE,
        "Reduces One Hand and Shield ability cost and block cost; neither changes one H1 heal magnitude.",
    ),
    WeaponPassiveRule(
        "One Hand and Shield",
        "Sword and Board",
        WeaponPassiveLayer.SHARED_STANDING,
        "Increases Weapon and Spell Damage while One Hand and Shield is equipped; this can change H1 heal scaling and must remain in weapon-configuration search.",
    ),
    WeaponPassiveRule(
        "One Hand and Shield",
        "Battlefield Mobility",
        WeaponPassiveLayer.BLOCK_STATE,
        "Reduces the Movement Speed penalty while bracing; does not modify maximum resources.",
    ),
    WeaponPassiveRule(
        "Two Handed",
        "Balanced Blade",
        WeaponPassiveLayer.ABILITY_FAMILY,
        "Reduces the Stamina cost of Two-Handed abilities; does not modify Max Stamina.",
    ),
    WeaponPassiveRule(
        "Two Handed",
        "Heavy Weapons",
        WeaponPassiveLayer.SHARED_STANDING,
        "Weapon-subtype standing bonuses include sword Weapon/Spell Damage and therefore can change H1 heal scaling; subtype search must preserve this passive.",
    ),
    WeaponPassiveRule(
        "Two Handed",
        "Follow Up",
        WeaponPassiveLayer.COMBAT_STATE,
        "After a fully charged Heavy Attack it increases Two Handed attack damage only; it does not scale healing events.",
    ),
    WeaponPassiveRule(
        "Two Handed",
        "Battle Rush",
        WeaponPassiveLayer.COMBAT_STATE,
        "Kill-triggered Stamina Recovery does not change one H1 heal magnitude.",
    ),
    WeaponPassiveRule(
        "Two Handed",
        "Forceful",
        WeaponPassiveLayer.COMBAT_STATE,
        "Causes Light and Heavy Attacks to cleave nearby enemies; does not modify maximum resources.",
    ),
)


def shared_standing_weapon_passives(skill_line: str) -> tuple[WeaponPassiveRule, ...]:
    key = str(skill_line or "").strip().casefold()
    return tuple(
        rule
        for rule in VERIFIED_WEAPON_PASSIVE_RULES
        if rule.skill_line.casefold() == key and rule.layer is WeaponPassiveLayer.SHARED_STANDING
    )
