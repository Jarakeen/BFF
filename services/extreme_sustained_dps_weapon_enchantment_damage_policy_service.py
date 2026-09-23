from __future__ import annotations

"""Verified policy semantics for selected weapon-enchantment damage consequences."""

from dataclasses import dataclass
import math

from minmax.proc_critical_eligibility import (
    ProcDamageKind,
    ProcScalingKind,
    resolve_proc_critical_eligibility,
)
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentDamageConsequence:
    time_seconds: float
    sequence: int
    source_label: str
    damage_type: str
    raw_value: float
    can_crit: bool | None
    critical_evidence: str


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentDamagePolicyResolution:
    consequences: tuple[ExtremeSustainedDPSWeaponEnchantmentDamageConsequence, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService:
    """Project only reviewed damage semantics from exact selected glyph procs."""

    @staticmethod
    def resolve(
        occurrences: tuple[ExtremeSustainedDPSWeaponEnchantmentProcOccurrence, ...],
    ) -> ExtremeSustainedDPSWeaponEnchantmentDamagePolicyResolution:
        rows: list[ExtremeSustainedDPSWeaponEnchantmentDamageConsequence] = []
        unresolved: list[str] = []
        inspected_damage_rows = 0

        for occurrence in tuple(occurrences):
            source_label = str(occurrence.source.source_label or "").strip()
            coordinate = f"{occurrence.time_seconds:g}s #{occurrence.sequence}"

            for effect in tuple(occurrence.consequences):
                if str(effect.effect_type or "").strip().casefold() != "damage":
                    continue

                inspected_damage_rows += 1
                damage_type = str(effect.damage_type or "").strip().casefold()
                if not damage_type:
                    unresolved.append(
                        f"{coordinate}: {source_label} damage consequence has no canonical damage type"
                    )
                    continue

                try:
                    raw_value = float(effect.value)
                except (TypeError, ValueError):
                    unresolved.append(
                        f"{coordinate}: {source_label} damage consequence has a non-numeric magnitude"
                    )
                    continue
                if not math.isfinite(raw_value) or raw_value < 0.0:
                    unresolved.append(
                        f"{coordinate}: {source_label} damage consequence has an invalid magnitude"
                    )
                    continue

                damage_kind = (
                    ProcDamageKind.OBLIVION
                    if damage_type == "oblivion"
                    else ProcDamageKind.STANDARD
                )
                critical = resolve_proc_critical_eligibility(
                    scaling_kind=ProcScalingKind.FLAT_OR_UNRESOLVED,
                    damage_kind=damage_kind,
                )
                rows.append(
                    ExtremeSustainedDPSWeaponEnchantmentDamageConsequence(
                        time_seconds=float(occurrence.time_seconds),
                        sequence=int(occurrence.sequence),
                        source_label=source_label,
                        damage_type=damage_type,
                        raw_value=raw_value,
                        can_crit=critical.can_crit,
                        critical_evidence=critical.reason,
                    )
                )

                if critical.can_crit is None:
                    unresolved.append(
                        f"{coordinate}: {source_label} {damage_type} weapon-enchantment "
                        "critical eligibility is not authoritatively resolved"
                    )

        return ExtremeSustainedDPSWeaponEnchantmentDamagePolicyResolution(
            consequences=tuple(rows),
            evidence=(
                f"Selected weapon-enchantment proc occurrences supplied: {len(tuple(occurrences))}",
                f"Canonical damage consequence rows inspected: {inspected_damage_rows}",
                f"Damage-policy consequence rows projected: {len(rows)}",
                "Oblivion weapon-enchantment damage uses the reviewed non-critical proc exception.",
                "Ordinary weapon-enchantment damage does not inherit normal skill critical eligibility.",
                "This service preserves raw canonical magnitude only; final applied damage remains downstream.",
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentDamageConsequence",
    "ExtremeSustainedDPSWeaponEnchantmentDamagePolicyResolution",
    "ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService",
]
