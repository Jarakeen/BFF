from __future__ import annotations

"""Project selected Weapon/Spell Damage glyph consequences into exact active windows."""

from dataclasses import dataclass
import math

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
)


_WEAPON_SPELL_DAMAGE_EFFECT = "weapon_spell_damage"


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageWindow:
    start_seconds: float
    end_seconds: float
    magnitude: float
    source_label: str

    def __post_init__(self) -> None:
        for label, value in (
            ("start_seconds", self.start_seconds),
            ("end_seconds", self.end_seconds),
            ("magnitude", self.magnitude),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"weapon-enchantment Weapon/Spell Damage window {label} must be numeric"
                )
            if not math.isfinite(float(value)):
                raise ValueError(
                    f"weapon-enchantment Weapon/Spell Damage window {label} must be finite"
                )
        if float(self.start_seconds) < 0.0:
            raise ValueError(
                "weapon-enchantment Weapon/Spell Damage window start_seconds cannot be negative"
            )
        if float(self.end_seconds) <= float(self.start_seconds):
            raise ValueError(
                "weapon-enchantment Weapon/Spell Damage window end_seconds must be after start_seconds"
            )
        if float(self.magnitude) < 0.0:
            raise ValueError(
                "weapon-enchantment Weapon/Spell Damage window magnitude cannot be negative"
            )
        if not isinstance(self.source_label, str) or not self.source_label.strip():
            raise TypeError(
                "weapon-enchantment Weapon/Spell Damage window source_label must be a non-empty string"
            )

    def active_at(self, time_seconds: float) -> bool:
        if isinstance(time_seconds, bool) or not isinstance(time_seconds, (int, float)):
            raise TypeError("Weapon/Spell Damage active_at time_seconds must be numeric")
        instant = float(time_seconds)
        if not math.isfinite(instant):
            raise ValueError("Weapon/Spell Damage active_at time_seconds must be finite")
        return self.start_seconds <= instant < self.end_seconds

    def as_effect_variant(self) -> EffectVariant:
        return EffectVariant(
            name=_WEAPON_SPELL_DAMAGE_EFFECT,
            layer=EffectLayer.PROC,
            source=self.source_label,
            magnitude=float(self.magnitude),
            duration=float(self.end_seconds - self.start_seconds),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageResolution:
    windows: tuple[ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageWindow, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.windows, tuple):
            raise TypeError("Weapon/Spell Damage resolution windows must be a tuple")
        if any(
            not isinstance(
                row,
                ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageWindow,
            )
            for row in self.windows
        ):
            raise TypeError(
                "Weapon/Spell Damage resolution windows must contain canonical window records"
            )
        if not isinstance(self.evidence, tuple):
            raise TypeError("Weapon/Spell Damage resolution evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("Weapon/Spell Damage resolution unresolved must be a tuple")

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    def active_effects_at(self, time_seconds: float) -> tuple[EffectVariant, ...]:
        active = tuple(
            window
            for window in self.windows
            if window.active_at(time_seconds)
        )
        if not active:
            return ()
        return (active[0].as_effect_variant(),)


class ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageService:
    """Consume only reviewed selected Weapon/Spell Damage enchant consequences."""

    @staticmethod
    def resolve(
        resolution: ExtremeSustainedDPSWeaponEnchantmentProcConsequenceResolution,
    ) -> ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageResolution:
        windows: list[
            ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageWindow
        ] = []
        unresolved: list[str] = list(tuple(resolution.unresolved))

        for occurrence in tuple(resolution.occurrences):
            coordinate = (
                f"{float(occurrence.time_seconds):g}s #{int(occurrence.sequence)}"
            )
            for consequence in tuple(occurrence.consequences):
                effect_type = str(consequence.effect_type or "").strip().casefold()
                if effect_type != _WEAPON_SPELL_DAMAGE_EFFECT:
                    continue

                try:
                    magnitude = float(consequence.value)
                except (TypeError, ValueError):
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} Weapon/Spell "
                        "Damage consequence has no numeric magnitude"
                    )
                    continue
                if not math.isfinite(magnitude) or magnitude < 0.0:
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} Weapon/Spell "
                        "Damage consequence has invalid magnitude"
                    )
                    continue

                try:
                    duration = float(consequence.duration_value)
                except (TypeError, ValueError):
                    duration = float("nan")
                duration_unit = str(consequence.duration_unit or "").strip().casefold()
                if (
                    not math.isfinite(duration)
                    or duration <= 0.0
                    or duration_unit not in {"second", "seconds"}
                ):
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} Weapon/Spell "
                        "Damage consequence requires canonical positive duration in seconds"
                    )
                    continue

                target = str(consequence.target or "").strip().casefold()
                if target not in {"", "self"}:
                    unresolved.append(
                        f"{coordinate}: {occurrence.source.source_label} Weapon/Spell "
                        f"Damage consequence target is not reviewed: {target}"
                    )
                    continue

                start = float(occurrence.time_seconds)
                windows.append(
                    ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageWindow(
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
                    "selected weapon-enchantment Weapon/Spell Damage windows overlap; "
                    "cross-source stacking/refresh semantics are not reviewed"
                )
                break

        return ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageResolution(
            windows=ordered,
            evidence=(
                *tuple(resolution.evidence),
                f"Selected Weapon/Spell Damage enchantment windows: {len(ordered)}",
                "Resolved windows reuse the canonical timed weapon_spell_damage stat projection.",
                "Strictly overlapping selected windows fail closed rather than assuming stacking or refresh semantics.",
            ),
            unresolved=tuple(dict.fromkeys(row for row in unresolved if row)),
        )


__all__ = [
    "ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageResolution",
    "ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageService",
    "ExtremeSustainedDPSWeaponEnchantmentWeaponSpellDamageWindow",
]
