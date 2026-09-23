from __future__ import annotations

"""Audit selected weapon-enchantment proc consequences at exact-leaf evaluation."""

from dataclasses import dataclass

from minmax.combat_effects import CombatEffect
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverage:
    selected_consequence_count: int
    consumed_consequence_count: int
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverageService:
    """Require every selected glyph consequence to have an explicit runtime consumer."""

    @staticmethod
    def assess(
        resolution: ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
        *,
        consumed_effect_types: tuple[str, ...] = (),
    ) -> ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverage:
        consumed = {
            str(value or "").strip().casefold()
            for value in tuple(consumed_effect_types)
            if str(value or "").strip()
        }
        unresolved: list[str] = list(tuple(resolution.unresolved))
        selected_count = 0
        consumed_count = 0

        for occurrence in tuple(resolution.occurrences):
            coordinate = (
                f"{float(occurrence.time_seconds):g}s #{int(occurrence.sequence)}"
            )
            for consequence in tuple(occurrence.consequences):
                selected_count += 1
                effect_type = str(consequence.effect_type or "").strip().casefold()
                if not effect_type:
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} selected "
                        "weapon-enchantment consequence has no canonical effect type"
                    )
                    continue
                if effect_type in consumed:
                    consumed_count += 1
                    continue
                unresolved.append(
                    f"{coordinate}: {occurrence.source.source_label} selected "
                    f"weapon-enchantment consequence is not consumed by exact runtime "
                    f"evaluation: {effect_type}"
                )

        return ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverage(
            selected_consequence_count=selected_count,
            consumed_consequence_count=consumed_count,
            evidence=(
                *tuple(resolution.evidence),
                f"Selected weapon-enchantment consequence rows: {selected_count}",
                f"Selected weapon-enchantment consequence rows with explicit consumers: {consumed_count}",
                "A selected glyph proc is not leaf-complete merely because source selection and cooldown sequencing are resolved.",
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverage",
    "ExtremeSustainedDPSWeaponEnchantmentConsequenceCoverageService",
]
