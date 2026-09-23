from __future__ import annotations

"""Project selected resistance-reduction weapon glyph consequences into time windows."""

from dataclasses import dataclass
import math

from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
)


_RESISTANCE_REDUCTION_EFFECT = "physical_spell_resistance_reduction"


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentResistanceWindow:
    start_seconds: float
    end_seconds: float
    magnitude: float
    source_label: str

    def active_at(self, time_seconds: float) -> bool:
        instant = float(time_seconds)
        return self.start_seconds <= instant < self.end_seconds


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentResistanceResolution:
    windows: tuple[ExtremeSustainedDPSWeaponEnchantmentResistanceWindow, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    def reduction_at(self, time_seconds: float) -> float:
        active = tuple(
            window
            for window in self.windows
            if window.active_at(float(time_seconds))
        )
        if not active:
            return 0.0
        # Overlapping active windows are rejected during construction, so one
        # exact window is the only resolved state here.
        return float(active[0].magnitude)


class ExtremeSustainedDPSWeaponEnchantmentResistanceReductionService:
    """Consume reviewed target-resistance reduction consequences only."""

    @staticmethod
    def resolve(
        resolution: ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
    ) -> ExtremeSustainedDPSWeaponEnchantmentResistanceResolution:
        windows: list[ExtremeSustainedDPSWeaponEnchantmentResistanceWindow] = []
        unresolved: list[str] = list(tuple(resolution.unresolved))

        for occurrence in tuple(resolution.occurrences):
            coordinate = (
                f"{float(occurrence.time_seconds):g}s #{int(occurrence.sequence)}"
            )
            for consequence in tuple(occurrence.consequences):
                effect_type = str(consequence.effect_type or "").strip().casefold()
                if effect_type != _RESISTANCE_REDUCTION_EFFECT:
                    continue

                try:
                    magnitude = float(consequence.value)
                except (TypeError, ValueError):
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} resistance "
                        "reduction has no numeric magnitude"
                    )
                    continue
                if not math.isfinite(magnitude) or magnitude < 0.0:
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} resistance "
                        "reduction has invalid magnitude"
                    )
                    continue

                duration_value = consequence.duration_value
                duration_unit = str(consequence.duration_unit or "").strip().casefold()
                try:
                    duration = float(duration_value)
                except (TypeError, ValueError):
                    duration = float("nan")
                if (
                    not math.isfinite(duration)
                    or duration <= 0.0
                    or duration_unit not in {"second", "seconds"}
                ):
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} resistance "
                        "reduction requires canonical positive duration in seconds"
                    )
                    continue

                target = str(consequence.target or "").strip().casefold()
                if target not in {"target", "enemy"}:
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} resistance "
                        f"reduction target is not reviewed: {target or 'unspecified'}"
                    )
                    continue

                start = float(occurrence.time_seconds)
                windows.append(
                    ExtremeSustainedDPSWeaponEnchantmentResistanceWindow(
                        start_seconds=start,
                        end_seconds=start + duration,
                        magnitude=magnitude,
                        source_label=str(occurrence.source.source_label),
                    )
                )

        ordered = tuple(
            sorted(
                windows,
                key=lambda row: (
                    row.start_seconds,
                    row.end_seconds,
                    row.source_label.casefold(),
                ),
            )
        )
        for previous, current in zip(ordered, ordered[1:]):
            if current.start_seconds < previous.end_seconds - 1e-12:
                unresolved.append(
                    "selected weapon-enchantment resistance-reduction windows overlap; "
                    "cross-source stacking/overwrite semantics are not reviewed"
                )
                break

        return ExtremeSustainedDPSWeaponEnchantmentResistanceResolution(
            windows=ordered,
            evidence=(
                *tuple(resolution.evidence),
                f"Selected weapon-enchantment resistance-reduction windows: {len(ordered)}",
                "Resolved windows feed the canonical exact-time target-resistance path.",
                "Strictly overlapping selected windows fail closed rather than assuming stacking or overwrite semantics.",
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentResistanceResolution",
    "ExtremeSustainedDPSWeaponEnchantmentResistanceReductionService",
    "ExtremeSustainedDPSWeaponEnchantmentResistanceWindow",
]
