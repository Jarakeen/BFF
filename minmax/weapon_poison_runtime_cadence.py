from __future__ import annotations

"""Canonical weapon-poison runtime cadence evidence for Objective #32.

Poison ownership/effect resolution stays separate from activation cadence.  The
fields here are intentionally evidence-granular so later research can replace one
mechanic without silently changing the rest of the runtime denominator.
"""

from dataclasses import dataclass
from enum import Enum


class WeaponPoisonCadenceAuthority(str, Enum):
    AUTHORITATIVE = "authoritative"
    PROVISIONAL = "provisional"


@dataclass(frozen=True)
class WeaponPoisonCadenceEvidence:
    proc_chance: float | None
    proc_chance_authority: WeaponPoisonCadenceAuthority
    proc_chance_evidence_note: str

    cooldown_seconds: float | None
    cooldown_authority: WeaponPoisonCadenceAuthority
    cooldown_evidence_note: str

    cooldown_scope: str | None
    cooldown_scope_authority: WeaponPoisonCadenceAuthority
    cooldown_scope_evidence_note: str

    activation_causes: tuple[str, ...]
    activation_authority: WeaponPoisonCadenceAuthority
    activation_evidence_note: str

    single_target_dot_ticks_eligible: bool | None
    single_target_dot_authority: WeaponPoisonCadenceAuthority
    single_target_dot_evidence_note: str

    poison_suppresses_weapon_enchantment: bool | None
    suppression_authority: WeaponPoisonCadenceAuthority
    suppression_evidence_note: str

    @property
    def runtime_blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if self.proc_chance is None:
            blockers.append("poison proc chance is unavailable")
        if self.proc_chance_authority is not WeaponPoisonCadenceAuthority.AUTHORITATIVE:
            blockers.append("poison proc chance is not authoritative")
        if self.cooldown_seconds is None:
            blockers.append("poison cooldown is unavailable")
        if self.cooldown_authority is not WeaponPoisonCadenceAuthority.AUTHORITATIVE:
            blockers.append("poison cooldown is not authoritative")
        if not str(self.cooldown_scope or "").strip():
            blockers.append("poison cooldown scope is unavailable")
        if self.cooldown_scope_authority is not WeaponPoisonCadenceAuthority.AUTHORITATIVE:
            blockers.append("poison cooldown scope is not authoritative")
        if not self.activation_causes:
            blockers.append("poison activation causes are unavailable")
        if self.activation_authority is not WeaponPoisonCadenceAuthority.AUTHORITATIVE:
            blockers.append("poison activation causes are not authoritative")
        if self.single_target_dot_ticks_eligible is None:
            blockers.append("single-target DoT poison eligibility is unavailable")
        if self.single_target_dot_authority is not WeaponPoisonCadenceAuthority.AUTHORITATIVE:
            blockers.append("single-target DoT poison eligibility is not authoritative")
        if self.poison_suppresses_weapon_enchantment is None:
            blockers.append("poison/enchantment suppression is unavailable")
        if self.suppression_authority is not WeaponPoisonCadenceAuthority.AUTHORITATIVE:
            blockers.append("poison/enchantment suppression is not authoritative")
        return tuple(dict.fromkeys(blockers))

    @property
    def runtime_ready(self) -> bool:
        return not self.runtime_blockers


AUTHORITATIVE_WEAPON_POISON_CADENCE = WeaponPoisonCadenceEvidence(
    proc_chance=0.20,
    proc_chance_authority=WeaponPoisonCadenceAuthority.AUTHORITATIVE,
    proc_chance_evidence_note=(
        "ZOS Update 20 live patch notes state that all poisons proc 20% of the "
        "time when a Light Attack, Heavy Attack, or weapon ability deals damage."
    ),
    cooldown_seconds=10.0,
    cooldown_authority=WeaponPoisonCadenceAuthority.AUTHORITATIVE,
    cooldown_evidence_note=(
        "ZOS Update 13 developer notes state that poisons cannot proc more than "
        "once every 10 seconds."
    ),
    cooldown_scope="global_player_poison",
    cooldown_scope_authority=WeaponPoisonCadenceAuthority.AUTHORITATIVE,
    cooldown_scope_evidence_note=(
        "ZOS Update 13 developer notes state that all poisons share one global "
        "cooldown and no longer have individual cooldowns."
    ),
    activation_causes=(
        "light_attack_damage",
        "heavy_attack_damage",
        "weapon_ability_damage",
    ),
    activation_authority=WeaponPoisonCadenceAuthority.AUTHORITATIVE,
    activation_evidence_note=(
        "ZOS Update 20 live patch notes tie poison proc checks to damaging Light "
        "Attacks, Heavy Attacks, and weapon abilities."
    ),
    single_target_dot_ticks_eligible=False,
    single_target_dot_authority=WeaponPoisonCadenceAuthority.AUTHORITATIVE,
    single_target_dot_evidence_note=(
        "ZOS v4.2.7 explicitly removed poison procs from single-target weapon-ability "
        "Damage over Time effects."
    ),
    poison_suppresses_weapon_enchantment=True,
    suppression_authority=WeaponPoisonCadenceAuthority.AUTHORITATIVE,
    suppression_evidence_note=(
        "ESO Support and Dark Brotherhood patch notes state that a poison suppresses "
        "weapon enchantments on the weapon set carrying it."
    ),
)


def authoritative_weapon_poison_cadence() -> WeaponPoisonCadenceEvidence:
    return AUTHORITATIVE_WEAPON_POISON_CADENCE


__all__ = [
    "AUTHORITATIVE_WEAPON_POISON_CADENCE",
    "WeaponPoisonCadenceAuthority",
    "WeaponPoisonCadenceEvidence",
    "authoritative_weapon_poison_cadence",
]
