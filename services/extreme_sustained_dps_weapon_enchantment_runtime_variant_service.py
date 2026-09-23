from __future__ import annotations

"""Project canonical equipped enchant sources into one runtime source variant each."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.support_effect_category import SupportEffectCategory
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantResolution:
    effects: tuple[EffectVariant, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantService:
    """Create exactly one selection/binding EffectVariant for each enchant source.

    These variants represent proc-source identity only. Combat consequences remain
    attached to the runtime source rows and are projected after a source is selected.
    """

    @staticmethod
    def resolve(
        sources: tuple[ExtremeSustainedDPSWeaponEnchantmentRuntimeSource, ...],
    ) -> ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantResolution:
        effects: list[EffectVariant] = []
        unresolved: list[str] = []
        seen: set[tuple[str, str, str]] = set()

        for source in tuple(sources):
            identity = str(source.identity or "").strip()
            label = str(source.source_label or "").strip()
            slot = str(source.source_slot or "").strip().casefold()
            if not identity or not label or slot not in {"main_hand", "off_hand"}:
                unresolved.append(
                    f"weapon-enchantment runtime source lacks complete binding provenance: {source.identity_label}"
                )
                continue
            key = (
                str(getattr(source.active_bar, "value", source.active_bar) or "").casefold(),
                slot,
                identity.casefold(),
            )
            if key in seen:
                unresolved.append(
                    f"duplicate weapon-enchantment runtime source for one bar/slot/identity: {source.identity_label}"
                )
                continue
            seen.add(key)
            effects.append(
                EffectVariant(
                    name=identity,
                    layer=EffectLayer.PROC,
                    source=label,
                    active_bar=source.active_bar,
                    source_slot=slot,
                    trigger=WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
                    category=SupportEffectCategory.OTHER,
                )
            )

        return ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantResolution(
            effects=tuple(effects),
            evidence=(
                f"Canonical enchant runtime sources supplied: {len(tuple(sources))}",
                f"Source-level weapon-enchantment runtime variants emitted: {len(effects)}",
                "Runtime source variants carry selection identity only; proc consequences remain separately owned",
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantResolution",
    "ExtremeSustainedDPSWeaponEnchantmentRuntimeVariantService",
]
