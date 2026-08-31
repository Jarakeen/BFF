from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .resource_costs import ResourceType
from .restoration_events import ResourceRestorationEvent


class HeavyAttackWeaponType(str, Enum):
    BOW = "bow"
    DUAL_WIELD = "dual_wield"
    TWO_HANDED = "two_handed"
    ONE_HAND_AND_SHIELD = "one_hand_and_shield"
    FIRE_STAFF = "fire_staff"
    FROST_STAFF = "frost_staff"
    SHOCK_STAFF = "shock_staff"
    RESTORATION_STAFF = "restoration_staff"
    UNARMED = "unarmed"
    WEREWOLF = "werewolf"


_STAMINA_WEAPONS = {
    HeavyAttackWeaponType.BOW,
    HeavyAttackWeaponType.DUAL_WIELD,
    HeavyAttackWeaponType.TWO_HANDED,
    HeavyAttackWeaponType.ONE_HAND_AND_SHIELD,
    HeavyAttackWeaponType.UNARMED,
    HeavyAttackWeaponType.WEREWOLF,
}

_MAGICKA_WEAPONS = {
    HeavyAttackWeaponType.FIRE_STAFF,
    HeavyAttackWeaponType.FROST_STAFF,
    HeavyAttackWeaponType.SHOCK_STAFF,
    HeavyAttackWeaponType.RESTORATION_STAFF,
}


@dataclass(frozen=True)
class HeavyAttackRestorationModifiers:
    """Verified multiplicative modifiers to a fully charged heavy restore.

    The underlying weapon-specific base restore is deliberately supplied by the
    caller until current live values are verified. This prevents historical
    UESP-translated constants from silently becoming Phase 4 canonical inputs.
    """

    champion_point_percent: float = 0.0
    skill_set_buff_percent: float = 0.0
    restoration_staff_cycle_of_life_percent: float = 0.0
    heavy_armor_revitalize_percent: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("champion_point_percent", self.champion_point_percent),
            ("skill_set_buff_percent", self.skill_set_buff_percent),
            ("restoration_staff_cycle_of_life_percent", self.restoration_staff_cycle_of_life_percent),
            ("heavy_armor_revitalize_percent", self.heavy_armor_revitalize_percent),
        ):
            if value < 0:
                raise ValueError(f"Heavy attack restoration modifier cannot be negative: {name}={value}")


def resource_for_heavy_attack_weapon(weapon: HeavyAttackWeaponType) -> ResourceType:
    if weapon in _STAMINA_WEAPONS:
        return ResourceType.STAMINA
    if weapon in _MAGICKA_WEAPONS:
        return ResourceType.MAGICKA
    raise ValueError(f"Unsupported heavy attack weapon type: {weapon}")


def calculate_heavy_attack_restoration(
    *,
    weapon: HeavyAttackWeaponType,
    verified_base_restore: float | None,
    modifiers: HeavyAttackRestorationModifiers = HeavyAttackRestorationModifiers(),
) -> float:
    """Calculate a fully charged heavy-attack restore from verified inputs.

    Current Phase 4 ordering preserves the existing UESP-translated structure:

        base * (1 + CP) * (1 + skill/set/buff + Revitalize) * weapon-specific

    Restoration Staff Cycle of Life is a weapon-specific multiplicative term.
    The base restore itself remains required and explicit until live-verified.
    """

    if verified_base_restore is None:
        raise ValueError(
            f"Heavy attack base restore is not live-verified for {weapon.value}"
        )
    if verified_base_restore < 0:
        raise ValueError(f"Heavy attack base restore cannot be negative: {verified_base_restore}")

    value = float(verified_base_restore)
    value *= 1.0 + modifiers.champion_point_percent
    value *= 1.0 + modifiers.skill_set_buff_percent + modifiers.heavy_armor_revitalize_percent

    if modifiers.restoration_staff_cycle_of_life_percent:
        if weapon is not HeavyAttackWeaponType.RESTORATION_STAFF:
            raise ValueError("Cycle of Life modifier requires a Restoration Staff heavy attack")
        value *= 1.0 + modifiers.restoration_staff_cycle_of_life_percent

    return value


def create_heavy_attack_restoration_event(
    *,
    time_seconds: float,
    weapon: HeavyAttackWeaponType,
    verified_base_restore: float | None,
    modifiers: HeavyAttackRestorationModifiers = HeavyAttackRestorationModifiers(),
    source: str | None = None,
) -> ResourceRestorationEvent:
    amount = calculate_heavy_attack_restoration(
        weapon=weapon,
        verified_base_restore=verified_base_restore,
        modifiers=modifiers,
    )
    return ResourceRestorationEvent(
        time_seconds=time_seconds,
        resource=resource_for_heavy_attack_weapon(weapon),
        amount=amount,
        source=source or f"Fully charged heavy attack: {weapon.value}",
    )
