from __future__ import annotations

"""Canonical weapon-enchantment runtime cadence evidence.

This module deliberately separates mechanics we can model from mechanics that are
still only community-observed.  Objective #32 may consume a cadence only when the
row is marked authoritative; provisional observations remain research evidence and
must fail closed rather than becoming combat math by accident.
"""

from dataclasses import dataclass
from enum import Enum


class WeaponEnchantmentCadenceAuthority(str, Enum):
    AUTHORITATIVE = "authoritative"
    PROVISIONAL = "provisional"


class WeaponEnchantmentEffectFamily(str, Enum):
    DIRECT_DAMAGE = "direct_damage"
    BUFF_OR_DEBUFF = "buff_or_debuff"


@dataclass(frozen=True)
class WeaponEnchantmentCadenceEvidence:
    family: WeaponEnchantmentEffectFamily
    base_cooldown_seconds: float | None
    authority: WeaponEnchantmentCadenceAuthority
    activation_causes: tuple[str, ...]
    off_bar_source_persists: bool | None
    cooldown_scope: str | None
    evidence_note: str

    @property
    def runtime_ready(self) -> bool:
        return (
            self.authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
            and self.base_cooldown_seconds is not None
            and bool(self.activation_causes)
            and self.off_bar_source_persists is not None
            and self.cooldown_scope is not None
        )

    def require_runtime_ready(self) -> "WeaponEnchantmentCadenceEvidence":
        if not self.runtime_ready:
            raise ValueError(
                "Weapon-enchantment cadence evidence is not authoritative enough "
                "for exact runtime simulation."
            )
        return self


# Community testing is consistent on the broad topology: eligible light/heavy attacks
# and weapon abilities can fire enchants; ground weapon DoTs can continue firing the
# originating weapon enchant after a bar swap; damage enchants are commonly observed
# around a four-second base cooldown while buff/debuff enchants are commonly reported
# around nine-to-ten seconds.  The exact buff/debuff base value is disputed even in
# detailed tests, so neither family is promoted to authoritative runtime math here.
_PROVISIONAL = {
    WeaponEnchantmentEffectFamily.DIRECT_DAMAGE: WeaponEnchantmentCadenceEvidence(
        family=WeaponEnchantmentEffectFamily.DIRECT_DAMAGE,
        base_cooldown_seconds=4.0,
        authority=WeaponEnchantmentCadenceAuthority.PROVISIONAL,
        activation_causes=("light_attack", "heavy_attack", "weapon_ability"),
        off_bar_source_persists=True,
        cooldown_scope="per_weapon_enchantment",
        evidence_note=(
            "Community-observed ESO behavior; exact current-version authoritative "
            "source still required before Objective #32 may consume this cadence."
        ),
    ),
    WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF: WeaponEnchantmentCadenceEvidence(
        family=WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF,
        base_cooldown_seconds=None,
        authority=WeaponEnchantmentCadenceAuthority.PROVISIONAL,
        activation_causes=("light_attack", "heavy_attack", "weapon_ability"),
        off_bar_source_persists=True,
        cooldown_scope="per_weapon_enchantment",
        evidence_note=(
            "Community observations disagree between roughly nine and ten seconds; "
            "the disputed base cooldown is intentionally unresolved."
        ),
    ),
}


def provisional_weapon_enchantment_cadence(
    family: WeaponEnchantmentEffectFamily,
) -> WeaponEnchantmentCadenceEvidence:
    return _PROVISIONAL[family]


__all__ = [
    "WeaponEnchantmentCadenceAuthority",
    "WeaponEnchantmentCadenceEvidence",
    "WeaponEnchantmentEffectFamily",
    "provisional_weapon_enchantment_cadence",
]
