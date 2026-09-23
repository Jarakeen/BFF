from __future__ import annotations

"""Classify canonical equipped weapon-enchantment sources into cadence families.

This service classifies from imported consequence semantics only. It does not assign
cooldown seconds, cooldown scope, timer sharing, or any other cadence authority.
"""

from dataclasses import dataclass

from minmax.weapon_enchantment_runtime_cadence import WeaponEnchantmentEffectFamily
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


_BUFF_OR_DEBUFF_EFFECT_TYPES = frozenset(
    {
        "damage_shield",
        "weapon_spell_damage",
        "weapon_spell_damage_reduction",
        "physical_spell_resistance_reduction",
    }
)
_RESTORE_EFFECT_TYPES = frozenset(
    {
        "health_restore",
        "magicka_restore",
        "stamina_restore",
    }
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyResolution:
    source: ExtremeSustainedDPSWeaponEnchantmentRuntimeSource
    family: WeaponEnchantmentEffectFamily | None
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.family is not None and not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService:
    """Resolve cadence family without promoting any cooldown mechanics."""

    @staticmethod
    def resolve(
        source: ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
    ) -> ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyResolution:
        effect_types = tuple(
            dict.fromkeys(
                str(effect.effect_type or "").strip().casefold()
                for effect in source.effects
                if str(effect.effect_type or "").strip()
            )
        )
        if not effect_types:
            return ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyResolution(
                source=source,
                family=None,
                unresolved=(
                    f"{source.source_label} has no canonical consequence effect types for cadence-family classification",
                ),
            )

        unknown = tuple(
            effect_type
            for effect_type in effect_types
            if effect_type
            not in (
                {"damage"}
                | _BUFF_OR_DEBUFF_EFFECT_TYPES
                | _RESTORE_EFFECT_TYPES
            )
        )
        if unknown:
            return ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyResolution(
                source=source,
                family=None,
                evidence=(
                    "Canonical weapon-enchantment consequence types: "
                    + ", ".join(effect_types),
                ),
                unresolved=(
                    f"{source.source_label} has unreviewed cadence-family consequence types: "
                    + ", ".join(unknown),
                ),
            )

        if "damage" in effect_types:
            return ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyResolution(
                source=source,
                family=WeaponEnchantmentEffectFamily.DIRECT_DAMAGE,
                evidence=(
                    "Canonical weapon-enchantment consequence types: "
                    + ", ".join(effect_types),
                    "A canonical direct-damage consequence classifies the enchant source in the direct-damage cadence family; co-produced restoration remains a consequence of the same proc.",
                ),
            )

        non_restore = tuple(
            effect_type
            for effect_type in effect_types
            if effect_type not in _RESTORE_EFFECT_TYPES
        )
        if non_restore and all(
            effect_type in _BUFF_OR_DEBUFF_EFFECT_TYPES
            for effect_type in non_restore
        ):
            return ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyResolution(
                source=source,
                family=WeaponEnchantmentEffectFamily.BUFF_OR_DEBUFF,
                evidence=(
                    "Canonical weapon-enchantment consequence types: "
                    + ", ".join(effect_types),
                    "The source has no direct-damage consequence and its canonical non-restoration consequences belong to the reviewed buff/debuff cadence family.",
                ),
            )

        return ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyResolution(
            source=source,
            family=None,
            evidence=(
                "Canonical weapon-enchantment consequence types: "
                + ", ".join(effect_types),
            ),
            unresolved=(
                f"{source.source_label} restoration-only cadence family is not reviewed",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyResolution",
    "ExtremeSustainedDPSWeaponEnchantmentCadenceFamilyService",
]
