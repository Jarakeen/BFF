from __future__ import annotations

"""Bind selected weapon-enchantment proc attempts back to canonical consequences."""

from dataclasses import dataclass

from minmax.combat_effects import CombatEffect
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
)
from services.extreme_sustained_dps_weapon_enchantment_runtime_source_service import (
    ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentProcOccurrence:
    time_seconds: float
    sequence: int
    source: ExtremeSustainedDPSWeaponEnchantmentRuntimeSource
    consequences: tuple[CombatEffect, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution:
    occurrences: tuple[ExtremeSustainedDPSWeaponEnchantmentProcOccurrence, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService:
    """Recover every canonical consequence after exact enchant source selection."""

    @staticmethod
    def _source_key(
        source: ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
    ) -> tuple[str, str, str, str]:
        return (
            str(source.identity or "").strip().casefold(),
            str(source.source_label or "").strip().casefold(),
            str(getattr(source.active_bar, "value", source.active_bar) or "")
            .strip()
            .casefold(),
            str(source.source_slot or "").strip().casefold(),
        )

    @classmethod
    def resolve(
        cls,
        *,
        attempts: tuple[RuntimeEffectEventAttempt, ...],
        sources: tuple[ExtremeSustainedDPSWeaponEnchantmentRuntimeSource, ...],
    ) -> ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution:
        source_by_key: dict[
            tuple[str, str, str, str],
            ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
        ] = {}
        unresolved: list[str] = []
        for source in tuple(sources):
            key = cls._source_key(source)
            if key in source_by_key:
                unresolved.append(
                    "duplicate canonical weapon-enchantment runtime source binding: "
                    f"{source.source_label} [{key[2]}/{key[3]}]"
                )
                continue
            source_by_key[key] = source

        occurrences: list[ExtremeSustainedDPSWeaponEnchantmentProcOccurrence] = []
        for attempt in tuple(attempts):
            if attempt.event.trigger != WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER:
                continue
            if attempt.bound_effect_key is None:
                unresolved.append(
                    f"{attempt.event.time_seconds:g}s #{attempt.event.sequence}: "
                    "weapon-enchantment proc attempt is not bound to an exact source"
                )
                continue
            source = source_by_key.get(tuple(attempt.bound_effect_key))
            if source is None:
                unresolved.append(
                    f"{attempt.event.time_seconds:g}s #{attempt.event.sequence}: "
                    "weapon-enchantment proc binding has no canonical equipped source"
                )
                continue
            if not source.effects:
                unresolved.append(
                    f"{attempt.event.time_seconds:g}s #{attempt.event.sequence}: "
                    f"{source.source_label} has no canonical proc consequences"
                )
                continue
            occurrences.append(
                ExtremeSustainedDPSWeaponEnchantmentProcOccurrence(
                    time_seconds=float(attempt.event.time_seconds),
                    sequence=int(attempt.event.sequence),
                    source=source,
                    consequences=tuple(source.effects),
                )
            )

        ordered = tuple(
            sorted(
                occurrences,
                key=lambda row: (
                    row.time_seconds,
                    row.sequence,
                    row.source.source_label.casefold(),
                ),
            )
        )
        return ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution(
            occurrences=ordered,
            evidence=(
                f"Canonical equipped enchant sources supplied: {len(tuple(sources))}",
                f"Source-bound enchant proc attempts inspected: {sum(1 for row in attempts if row.event.trigger == WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER)}",
                f"Exact enchant proc consequence occurrences resolved: {len(ordered)}",
                f"Canonical consequence rows attached to selected procs: {sum(len(row.consequences) for row in ordered)}",
                "This bridge resolves which canonical consequences occurred; it does not resolve final damage, mitigation, critical strikes, status effects, or resource/Health application.",
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentProcOccurrence",
    "ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution",
    "ExtremeSustainedDPSWeaponEnchantmentProcConsequenceService",
]
