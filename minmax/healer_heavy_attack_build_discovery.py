from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from models.build_model import PlayerBuild
from .heavy_attack_restoration import HeavyAttackWeaponType
from .weapon_passive_classification import (
    VERIFIED_WEAPON_PASSIVE_RULES,
    WeaponPassiveLayer,
)


class HeavyAttackBuildIncentiveKind(str, Enum):
    REQUIRED_EFFECT = "required_effect"
    HEALING_VALUE = "healing_value"
    RECOVERY_VALUE = "recovery_value"


@dataclass(frozen=True)
class HealerHeavyAttackBuildIncentive:
    """Static saved-build evidence explaining why a heavy attack may matter.

    This is deliberately not a runtime scheduling decision. Encounter safety,
    resource state, effect uptime, exact channel duration, and refresh collisions
    must still be proven at the decision point before a HEAVY_ATTACK is scheduled.
    """

    bar: str
    weapon: HeavyAttackWeaponType
    kind: HeavyAttackBuildIncentiveKind
    name: str
    source: str
    recurrence_seconds: float | None = None
    maximum_effect_duration_seconds: float | None = None
    requires_active_effect: str | None = None


_WEAPON_TYPES = {
    "restoration staff": HeavyAttackWeaponType.RESTORATION_STAFF,
    "ice staff": HeavyAttackWeaponType.FROST_STAFF,
    "frost staff": HeavyAttackWeaponType.FROST_STAFF,
    "inferno staff": HeavyAttackWeaponType.FIRE_STAFF,
    "fire staff": HeavyAttackWeaponType.FIRE_STAFF,
    "lightning staff": HeavyAttackWeaponType.SHOCK_STAFF,
    "shock staff": HeavyAttackWeaponType.SHOCK_STAFF,
}

_ROARING_OPPORTUNIST_NAMES = {
    "roaring opportunist",
    "perfected roaring opportunist",
}

_LOTUS_SKILLS = {
    "lotus flower",
    "green lotus",
    "lotus blossom",
}

_RO_SOURCE = (
    "ESO-Hub Roaring Opportunist set tooltip, verified 2026-09-06: fully-charged "
    "Heavy Attack grants Major Slayer; target lockout 22s; maximum duration 12s"
)

_LOTUS_SOURCE = (
    "ESO-Hub Warden Lotus tooltip, verified 2026-09-06: while active, fully-charged "
    "Heavy Attacks heal the caster or nearby allies"
)


def discover_healer_heavy_attack_build_incentives(
    build: PlayerBuild,
) -> tuple[HealerHeavyAttackBuildIncentive, ...]:
    """Return static heavy-attack incentives proven by one saved build.

    The function intentionally does not manufacture heavy timing. It only derives
    weapon/passive, equipped-set, and slotted Lotus evidence that a later runtime
    layer can combine with cooldown, sustain, encounter, and refresh state.
    """

    incentives: list[HealerHeavyAttackBuildIncentive] = []
    active_sets = {
        "front": _active_set_counts(build, "front"),
        "back": _active_set_counts(build, "back"),
    }
    lotus = _slotted_lotus_skill(build)

    for bar in ("front", "back"):
        weapon = _weapon_for_bar(build, bar)
        if weapon is None:
            continue

        if weapon is HeavyAttackWeaponType.RESTORATION_STAFF:
            passive_names = {
                rule.passive
                for rule in VERIFIED_WEAPON_PASSIVE_RULES
                if rule.skill_line == "Restoration Staff"
                and rule.layer is WeaponPassiveLayer.COMBAT_STATE
            }
            if "Essence Drain" in passive_names:
                incentives.append(
                    HealerHeavyAttackBuildIncentive(
                        bar=bar,
                        weapon=weapon,
                        kind=HeavyAttackBuildIncentiveKind.HEALING_VALUE,
                        name="Essence Drain",
                        source="VERIFIED_WEAPON_PASSIVE_RULES: Essence Drain",
                        maximum_effect_duration_seconds=4.0,
                    )
                )
            if "Cycle of Life" in passive_names:
                incentives.append(
                    HealerHeavyAttackBuildIncentive(
                        bar=bar,
                        weapon=weapon,
                        kind=HeavyAttackBuildIncentiveKind.RECOVERY_VALUE,
                        name="Cycle of Life",
                        source="VERIFIED_WEAPON_PASSIVE_RULES: Cycle of Life",
                    )
                )

        for set_name, pieces in active_sets[bar].items():
            if pieces < 5 or set_name.casefold() not in _ROARING_OPPORTUNIST_NAMES:
                continue
            incentives.append(
                HealerHeavyAttackBuildIncentive(
                    bar=bar,
                    weapon=weapon,
                    kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
                    name=set_name,
                    source=_RO_SOURCE,
                    recurrence_seconds=22.0,
                    maximum_effect_duration_seconds=12.0,
                )
            )

        if lotus is not None:
            incentives.append(
                HealerHeavyAttackBuildIncentive(
                    bar=bar,
                    weapon=weapon,
                    kind=HeavyAttackBuildIncentiveKind.HEALING_VALUE,
                    name=lotus,
                    source=_LOTUS_SOURCE,
                    requires_active_effect=lotus,
                )
            )

    return tuple(incentives)


def _weapon_for_bar(build: PlayerBuild, bar: str) -> HeavyAttackWeaponType | None:
    slot = build.FrontBarWeapon if bar == "front" else build.BackBarWeapon
    name = " ".join(str(slot.WeaponType or "").strip().split()).casefold()
    return _WEAPON_TYPES.get(name)


def _slotted_lotus_skill(build: PlayerBuild) -> str | None:
    if str(build.EsoClass or "").strip().casefold() != "warden":
        return None
    for raw in tuple(build.FrontBarSkills or ()) + tuple(build.BackBarSkills or ()):
        name = " ".join(str(raw or "").strip().split())
        if name.casefold() in _LOTUS_SKILLS:
            return name
    return None


def _active_set_counts(build: PlayerBuild, bar: str) -> dict[str, int]:
    counts: dict[str, int] = {}

    def add(raw_name: str, pieces: int = 1) -> None:
        name = " ".join(str(raw_name or "").strip().split())
        if name:
            counts[name] = counts.get(name, 0) + pieces

    for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
        entry = build.Armor.get(slot, {})
        add(entry.get("Set", ""))
        add(entry.get("Set2", ""))
    for jewelry in (build.Necklace, build.Ring1, build.Ring2):
        add(jewelry.Set)
        add(getattr(jewelry, "Set2", ""))

    weapon = build.FrontBarWeapon if bar == "front" else build.BackBarWeapon
    weapon_type = " ".join(str(weapon.WeaponType or "").strip().split()).casefold()
    weapon_pieces = 2 if "staff" in weapon_type else 1
    add(weapon.Set, weapon_pieces)
    add(getattr(weapon, "Set2", ""), weapon_pieces)
    return counts
