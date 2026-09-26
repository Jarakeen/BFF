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

    def __post_init__(self) -> None:
        if isinstance(self.time_seconds, bool) or not isinstance(self.time_seconds, (int, float)):
            raise TypeError("weapon-enchantment proc occurrence time_seconds must be numeric")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise TypeError("weapon-enchantment proc occurrence sequence must be an integer")
        if self.sequence < 0:
            raise ValueError("weapon-enchantment proc occurrence sequence cannot be negative")
        if not isinstance(self.source, ExtremeSustainedDPSWeaponEnchantmentRuntimeSource):
            raise TypeError("weapon-enchantment proc occurrence source must be canonical runtime source")
        if not isinstance(self.consequences, tuple):
            raise TypeError("weapon-enchantment proc occurrence consequences must be a tuple")
        if any(not isinstance(row, CombatEffect) for row in self.consequences):
            raise TypeError("weapon-enchantment proc occurrence consequences must contain CombatEffect records")


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution:
    occurrences: tuple[ExtremeSustainedDPSWeaponEnchantmentProcOccurrence, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.occurrences, tuple):
            raise TypeError("weapon-enchantment proc resolution occurrences must be a tuple")
        if any(
            not isinstance(row, ExtremeSustainedDPSWeaponEnchantmentProcOccurrence)
            for row in self.occurrences
        ):
            raise TypeError(
                "weapon-enchantment proc resolution occurrences must contain canonical occurrence records"
            )
        if not isinstance(self.evidence, tuple):
            raise TypeError("weapon-enchantment proc resolution evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("weapon-enchantment proc resolution unresolved must be a tuple")

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
        if not isinstance(attempts, tuple):
            raise TypeError("weapon-enchantment proc attempts must be a tuple")
        if any(not isinstance(row, RuntimeEffectEventAttempt) for row in attempts):
            raise TypeError("weapon-enchantment proc attempts must contain RuntimeEffectEventAttempt records")
        if not isinstance(sources, tuple):
            raise TypeError("weapon-enchantment proc sources must be a tuple")
        if any(
            not isinstance(row, ExtremeSustainedDPSWeaponEnchantmentRuntimeSource)
            for row in sources
        ):
            raise TypeError(
                "weapon-enchantment proc sources must contain canonical runtime source records"
            )

        source_by_key: dict[
            tuple[str, str, str, str],
            ExtremeSustainedDPSWeaponEnchantmentRuntimeSource,
        ] = {}
        unresolved: list[str] = []
        for source in sources:
            key = cls._source_key(source)
            if key in source_by_key:
                unresolved.append(
                    "duplicate canonical weapon-enchantment runtime source binding: "
                    f"{source.source_label} [{key[2]}/{key[3]}]"
                )
                continue
            source_by_key[key] = source

        occurrences: list[ExtremeSustainedDPSWeaponEnchantmentProcOccurrence] = []
        for attempt in attempts:
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
                    time_seconds=attempt.event.time_seconds,
                    sequence=attempt.event.sequence,
                    source=source,
                    consequences=source.effects,
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
                f"Canonical equipped enchant sources supplied: {len(sources)}",
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
