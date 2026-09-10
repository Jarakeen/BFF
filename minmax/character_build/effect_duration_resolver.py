from __future__ import annotations

from dataclasses import dataclass
import math

from ..support_effect_category import SupportEffectCategory
from .effect_instance import EffectVariant


STATUS_EFFECT_DURATION_INCREASE = "status_effect_duration_increase"
MAJOR_MINOR_BUFF_DURATION_INCREASE = "major_minor_buff_duration_increase"


@dataclass(frozen=True)
class AppliedEffectDurationModifier:
    """One verified build effect that changed another effect's duration."""

    name: str
    source: str
    seconds: float


@dataclass(frozen=True)
class EffectDurationResolution:
    """Build-effective duration for one already-resolved EffectVariant.

    The resolver works only from semantic EffectVariant identities produced by
    the canonical build/effect layer. It never parses tooltip text and never
    guesses whether an arbitrary bonus modifies duration.
    """

    effect_name: str
    base_duration_seconds: float | None
    effective_duration_seconds: float | None
    applied_modifiers: tuple[AppliedEffectDurationModifier, ...] = ()
    unresolved: tuple[str, ...] = ()


class EffectDurationResolver:
    """Apply verified build duration modifiers to a concrete effect.

    Serpent's Disdain extends STATUS effects by a verified additive number of
    seconds. Jorvuld's Guidance extends wearer-applied Major/Minor BUFF effects by
    a verified percentage. Damage-shield duration remains outside this resolver
    until the canonical effect taxonomy can identify shields explicitly.
    """

    def resolve(
        self,
        effect: EffectVariant,
        *,
        available_effects: tuple[EffectVariant, ...] = (),
    ) -> EffectDurationResolution:
        base = self._finite_positive(effect.duration)
        if base is None:
            return EffectDurationResolution(
                effect_name=effect.name,
                base_duration_seconds=None,
                effective_duration_seconds=None,
                unresolved=(f"{effect.name}: base effect duration unresolved",),
            )

        applicable = self._applicable_modifiers(effect, available_effects)
        if not applicable:
            return EffectDurationResolution(
                effect_name=effect.name,
                base_duration_seconds=base,
                effective_duration_seconds=base,
            )

        if len(applicable) > 1:
            sources = ", ".join(sorted({candidate.source for candidate in applicable}))
            return EffectDurationResolution(
                effect_name=effect.name,
                base_duration_seconds=base,
                effective_duration_seconds=None,
                unresolved=(
                    f"{effect.name}: multiple applicable duration modifiers require "
                    f"explicit stacking resolution ({sources})",
                ),
            )

        modifier = applicable[0]
        if modifier.name.casefold() == STATUS_EFFECT_DURATION_INCREASE:
            seconds = self._finite_nonnegative(modifier.magnitude)
            if seconds is None:
                return EffectDurationResolution(
                    effect_name=effect.name,
                    base_duration_seconds=base,
                    effective_duration_seconds=None,
                    unresolved=(
                        f"{effect.name}: {modifier.source} has unresolved "
                        "status-effect duration magnitude",
                    ),
                )
        elif modifier.name.casefold() == MAJOR_MINOR_BUFF_DURATION_INCREASE:
            fraction = self._finite_nonnegative(modifier.magnitude)
            if fraction is None:
                return EffectDurationResolution(
                    effect_name=effect.name,
                    base_duration_seconds=base,
                    effective_duration_seconds=None,
                    unresolved=(
                        f"{effect.name}: {modifier.source} has unresolved "
                        "Major/Minor buff duration magnitude",
                    ),
                )
            seconds = base * fraction
        else:
            return EffectDurationResolution(
                effect_name=effect.name,
                base_duration_seconds=base,
                effective_duration_seconds=base,
            )

        applied = AppliedEffectDurationModifier(
            name=modifier.name,
            source=modifier.source,
            seconds=seconds,
        )
        return EffectDurationResolution(
            effect_name=effect.name,
            base_duration_seconds=base,
            effective_duration_seconds=base + seconds,
            applied_modifiers=(applied,),
        )

    @staticmethod
    def _applicable_modifiers(
        effect: EffectVariant,
        available_effects: tuple[EffectVariant, ...],
    ) -> tuple[EffectVariant, ...]:
        candidates: list[EffectVariant] = []
        for candidate in available_effects:
            if not candidate.eligible:
                continue
            name = candidate.name.casefold()
            if (
                name == STATUS_EFFECT_DURATION_INCREASE
                and effect.category is SupportEffectCategory.STATUS
            ):
                candidates.append(candidate)
                continue
            if (
                name == MAJOR_MINOR_BUFF_DURATION_INCREASE
                and effect.category is SupportEffectCategory.BUFF
                and effect.name.casefold().startswith(("major_", "minor_"))
            ):
                candidates.append(candidate)
        return tuple(candidates)

    @staticmethod
    def _finite_positive(value: float | None) -> float | None:
        if value is None:
            return None
        resolved = float(value)
        if not math.isfinite(resolved) or resolved <= 0.0:
            return None
        return resolved

    @staticmethod
    def _finite_nonnegative(value: float | None) -> float | None:
        if value is None:
            return None
        resolved = float(value)
        if not math.isfinite(resolved) or resolved < 0.0:
            return None
        return resolved


__all__ = [
    "AppliedEffectDurationModifier",
    "EffectDurationResolution",
    "EffectDurationResolver",
    "MAJOR_MINOR_BUFF_DURATION_INCREASE",
    "STATUS_EFFECT_DURATION_INCREASE",
]
