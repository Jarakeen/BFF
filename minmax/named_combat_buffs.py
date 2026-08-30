from __future__ import annotations

"""Verified named combat buffs that modify first-class shared stats.

Source: ``math/buff.txt`` in this repository. This registry intentionally
contains only effects that can be routed into the existing shared stat model
without inventing Damage Done, Damage Taken, shield-strength, movement, or
other future combat-component semantics.
"""

from dataclasses import dataclass

from .stat_ids import StatId


@dataclass(frozen=True)
class NamedBuffEffect:
    stat: StatId
    value: float
    bucket: str


NAMED_BUFF_EFFECTS: dict[str, tuple[NamedBuffEffect, ...]] = {
    "Minor Brutality": (NamedBuffEffect(StatId.WEAPON_DAMAGE, 0.10, "percent"),),
    "Major Brutality": (NamedBuffEffect(StatId.WEAPON_DAMAGE, 0.20, "percent"),),
    "Minor Sorcery": (NamedBuffEffect(StatId.SPELL_DAMAGE, 0.10, "percent"),),
    "Major Sorcery": (NamedBuffEffect(StatId.SPELL_DAMAGE, 0.20, "percent"),),
    "Minor Courage": (
        NamedBuffEffect(StatId.WEAPON_DAMAGE, 215.0, "flat"),
        NamedBuffEffect(StatId.SPELL_DAMAGE, 215.0, "flat"),
    ),
    "Major Courage": (
        NamedBuffEffect(StatId.WEAPON_DAMAGE, 430.0, "flat"),
        NamedBuffEffect(StatId.SPELL_DAMAGE, 430.0, "flat"),
    ),
    "Minor Savagery": (NamedBuffEffect(StatId.WEAPON_CRITICAL, 1314.0, "critical_rating"),),
    "Major Savagery": (NamedBuffEffect(StatId.WEAPON_CRITICAL, 2629.0, "critical_rating"),),
    "Minor Prophecy": (NamedBuffEffect(StatId.SPELL_CRITICAL, 1314.0, "critical_rating"),),
    "Major Prophecy": (NamedBuffEffect(StatId.SPELL_CRITICAL, 2629.0, "critical_rating"),),
    "Minor Force": (NamedBuffEffect(StatId.CRITICAL_DAMAGE, 0.10, "ratio_points"),),
    "Major Force": (NamedBuffEffect(StatId.CRITICAL_DAMAGE, 0.20, "ratio_points"),),
    "Minor Mending": (NamedBuffEffect(StatId.HEALING_DONE, 0.08, "ratio_points"),),
    "Major Mending": (NamedBuffEffect(StatId.HEALING_DONE, 0.16, "ratio_points"),),
    "Minor Resolve": (
        NamedBuffEffect(StatId.PHYSICAL_RESISTANCE, 2974.0, "flat"),
        NamedBuffEffect(StatId.SPELL_RESISTANCE, 2974.0, "flat"),
    ),
    "Major Resolve": (
        NamedBuffEffect(StatId.PHYSICAL_RESISTANCE, 5948.0, "flat"),
        NamedBuffEffect(StatId.SPELL_RESISTANCE, 5948.0, "flat"),
    ),
    "Minor Fortitude": (NamedBuffEffect(StatId.HEALTH_RECOVERY, 0.15, "resource_percent"),),
    "Major Fortitude": (NamedBuffEffect(StatId.HEALTH_RECOVERY, 0.30, "resource_percent"),),
    "Minor Intellect": (NamedBuffEffect(StatId.MAGICKA_RECOVERY, 0.15, "resource_percent"),),
    "Major Intellect": (NamedBuffEffect(StatId.MAGICKA_RECOVERY, 0.30, "resource_percent"),),
    "Minor Endurance": (NamedBuffEffect(StatId.STAMINA_RECOVERY, 0.15, "resource_percent"),),
    "Major Endurance": (NamedBuffEffect(StatId.STAMINA_RECOVERY, 0.30, "resource_percent"),),
    "Minor Toughness": (NamedBuffEffect(StatId.MAX_HEALTH, 0.10, "resource_percent"),),
}


def canonical_buff_name(value: str) -> str | None:
    key = " ".join(str(value or "").strip().casefold().split())
    if not key:
        return None
    for name in NAMED_BUFF_EFFECTS:
        if name.casefold() == key:
            return name
    return None


def effects_for_buff(value: str) -> tuple[NamedBuffEffect, ...]:
    canonical = canonical_buff_name(value)
    return NAMED_BUFF_EFFECTS.get(canonical or "", ())
