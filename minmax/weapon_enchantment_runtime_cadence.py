from __future__ import annotations

"""Canonical weapon-enchantment runtime cadence evidence.

Research observations stay explicitly provisional. Objective #32 may consume a
cadence only after the evidence is promoted to authoritative current-version data.
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
    activation_authority: WeaponEnchantmentCadenceAuthority
    activation_evidence_note: str
    off_bar_source_persists: bool | None
    cooldown_scope: str | None
    poison_replaces_enchantment: bool | None
    same_effect_identity_shares_cooldown: bool | None
    evidence_note: str

    @property
    def runtime_ready(self) -> bool:
        return (
            self.authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
            and self.base_cooldown_seconds is not None
            and bool(self.activation_causes)
            and self.activation_authority is WeaponEnchantmentCadenceAuthority.AUTHORITATIVE
            and self.off_bar_source_persists is not None
            and self.cooldown_scope is not None
            and self.poison_replaces_enchantment is not None
            and self.same_effect_identity_shares_cooldown is not None
        )

    def require_runtime_ready(self) -> "WeaponEnchantmentCadenceEvidence":
        if not self.runtime_ready:
            raise ValueError(
                "Weapon-enchantment cadence evidence is not authoritative enough "
                "for exact runtime simulation."
            )
        return self


# ZOS Update 20 patch notes establish the activation family: any Light Attack, Heavy
# Attack, or weapon ability that deals damage procs a weapon enchantment 100% of the
# time when that enchantment is not on cooldown. Dual Wield weapon abilities may proc
# either weapon, favoring one whose enchantment is not on cooldown. Remaining cadence
# topology below is still provisional: ground weapon DoTs can continue firing the
# originating weapon enchant after a bar swap; damage enchants are observed with a
# four-second base cooldown; an equipped alchemical poison suppresses the enchantment;
# and duplicate enchantment identities share cooldown while different identities can
# retain independent timers. Buff/debuff base cooldown evidence conflicts between
# roughly nine and ten seconds. None of this is promoted to exact runtime math until
# current-version authoritative evidence closes the remaining uncertainty.
_PROVISIONAL = {
    WeaponEnchantmentEffectFamily.DIRECT_DAMAGE: WeaponEnchantmentCadenceEvidence(
        family=WeaponEnchantmentEffectFamily.DIRECT_DAMAGE,
        base_cooldown_seconds=4.0,
        authority=WeaponEnchantmentCadenceAuthority.PROVISIONAL,
        activation_causes=(
            "light_attack_damage",
            "heavy_attack_damage",
            "weapon_ability_damage",
        ),
        activation_authority=WeaponEnchantmentCadenceAuthority.AUTHORITATIVE,
        activation_evidence_note=(
            "ZOS Update 20 patch notes: weapon enchantments proc 100% when not on "
            "cooldown when a Light Attack, Heavy Attack, or weapon ability deals damage; "
            "Dual Wield weapon abilities favor an enchantment that is not on cooldown."
        ),
        off_bar_source_persists=True,
        cooldown_scope="per_effect_identity",
        poison_replaces_enchantment=True,
        same_effect_identity_shares_cooldown=True,
        evidence_note=(
            "Community-observed ESO behavior; current-version authoritative source "
            "still required before Objective #32 may consume this cadence."
        ),
    ),
    WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF: WeaponEnchantmentCadenceEvidence(
        family=WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF,
        base_cooldown_seconds=10.0,
        authority=WeaponEnchantmentCadenceAuthority.PROVISIONAL,
        activation_causes=(
            "light_attack_damage",
            "heavy_attack_damage",
            "weapon_ability_damage",
        ),
        activation_authority=WeaponEnchantmentCadenceAuthority.AUTHORITATIVE,
        activation_evidence_note=(
            "ZOS Update 20 patch notes: weapon enchantments proc 100% when not on "
            "cooldown when a Light Attack, Heavy Attack, or weapon ability deals damage; "
            "Dual Wield weapon abilities favor an enchantment that is not on cooldown."
        ),
        off_bar_source_persists=True,
        cooldown_scope="per_effect_identity",
        poison_replaces_enchantment=True,
        same_effect_identity_shares_cooldown=True,
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
