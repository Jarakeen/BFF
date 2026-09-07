from __future__ import annotations

from dataclasses import dataclass
import math

from ..support_effect_category import SupportEffectCategory
from .effect_instance import EffectVariant


STATUS_EFFECT_DURATION_INCREASE = "status_effect_duration_increase"


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

    Serpent's Disdain is currently the only canonical duration modifier in the
    repository. Its known EffectVariant identity is explicitly scoped to STATUS
    effects and adds seconds. Future duration mechanics should be added here only
    after the upstream effect registry has a verified semantic identity and the
    stacking/applicability rule is known.
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

        if effect.category is not SupportEffectCategory.STATUS:
            return EffectDurationResolution(
                effect_name=effect.name,
                base_duration_seconds=base,
                effective_duration_seconds=base,
            )

        candidates = tuple(
            candidate
            for candidate in available_effects
            if candidate.eligible
            and candidate.name.casefold() == STATUS_EFFECT_DURATION_INCREASE
        )
        if not candidates:
            return EffectDurationResolution(
                effect_name=effect.name,
                base_duration_seconds=base,
                effective_duration_seconds=base,
            )

        if len(candidates) > 1:
            sources = ", ".join(sorted({candidate.source for candidate in candidates}))
            return EffectDurationResolution(
                effect_name=effect.name,
                base_duration_seconds=base,
                effective_duration_seconds=None,
                unresolved=(
                    f"{effect.name}: multiple status-effect duration modifiers require "
                    f"explicit stacking resolution ({sources})",
                ),
            )

        modifier = candidates[0]
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
    "STATUS_EFFECT_DURATION_INCREASE",
]
