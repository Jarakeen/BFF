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

# Official Update 35 fully-charged staff-heavy base restores, independently
# corroborated by the current reviewed ESO Logs corpus for these three weapon
# families. Fire Staff remains fail-closed here because the current corpus has
# no reviewed live observation for its restore value yet.
#
# Official source: ESO Update 35 patch notes (2022 Lost Depths update)
# - Restoration Staff: 3267 Magicka
# - Ice Staff: 2425 Magicka
# - Lightning Staff: 2970 Magicka
_VERIFIED_BASE_RESTORE_BY_WEAPON: dict[HeavyAttackWeaponType, float] = {
    HeavyAttackWeaponType.FROST_STAFF: 2425.0,
    HeavyAttackWeaponType.SHOCK_STAFF: 2970.0,
    HeavyAttackWeaponType.RESTORATION_STAFF: 3267.0,
}


@dataclass(frozen=True)
class HeavyAttackRestorationModifiers:
    """Verified multiplicative modifiers to a fully charged heavy restore."""

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


def verified_heavy_attack_base_restore(weapon: HeavyAttackWeaponType) -> float | None:
    """Return a live-verified fully charged base restore when one is known.

    Unknown weapon families remain explicit ``None`` rather than inheriting a
    historical value. Callers may still supply separately reviewed evidence to
    ``calculate_heavy_attack_restoration`` when appropriate.
    """

    return _VERIFIED_BASE_RESTORE_BY_WEAPON.get(weapon)


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
    The base restore must still be explicit at the call boundary; callers may use
    ``verified_heavy_attack_base_restore`` for weapon families promoted from
    reviewed live evidence.
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
