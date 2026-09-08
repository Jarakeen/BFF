from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.character_build.effect_instance import EffectVariant


POTION_COOLDOWN_REDUCTION_EFFECT = "potion_cooldown_reduction"


@dataclass(frozen=True)
class RotationPotionCooldownEffectReduction:
    """One verified non-item contribution to potion cooldown reduction."""

    source: str
    seconds: float
    layer: str

    def __post_init__(self) -> None:
        source = str(self.source or "").strip()
        if not source:
            raise ValueError("potion cooldown effect reduction needs source")
        seconds = float(self.seconds)
        if not math.isfinite(seconds) or seconds <= 0.0:
            raise ValueError("potion cooldown effect reduction must be finite and positive")
        layer = str(self.layer or "").strip()
        if not layer:
            raise ValueError("potion cooldown effect reduction needs layer")
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "seconds", seconds)
        object.__setattr__(self, "layer", layer)


@dataclass(frozen=True)
class RotationPotionCooldownEffectEvidence:
    """Canonical skill/set/passive potion-cooldown evidence.

    Only unconditional, deterministic, globally applicable variants are reduced to
    a static number. Conditional/triggered/bar-scoped/stochastic variants remain
    unresolved because their contribution depends on runtime state and cannot be
    safely folded into one global potion cadence.
    """

    reductions: tuple[RotationPotionCooldownEffectReduction, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def total_reduction_seconds(self) -> float:
        return sum(item.seconds for item in self.reductions)


class RotationPotionCooldownEffectVariantService:
    """Resolve explicit canonical EffectVariant potion-cooldown contributions.

    This service does not discover effects from names, roles, sets, or skill lines.
    It consumes already-canonical EffectVariant evidence and therefore preserves the
    CharacterBuild effect-resolution boundary.
    """

    def resolve(
        self,
        effects: tuple[EffectVariant, ...],
    ) -> RotationPotionCooldownEffectEvidence:
        reductions: list[RotationPotionCooldownEffectReduction] = []
        unresolved: list[str] = []

        for effect in effects:
            if str(effect.name or "").strip().casefold() != POTION_COOLDOWN_REDUCTION_EFFECT:
                continue
            if not effect.eligible:
                # A canonically ineligible effect is known not to contribute in the
                # supplied state; preserving it as unresolved would over-block.
                continue

            source = str(effect.source or "").strip() or "unknown source"
            reasons: list[str] = []
            if effect.condition:
                reasons.append(f"condition={effect.condition}")
            if effect.trigger:
                reasons.append(f"trigger={effect.trigger}")
            if effect.active_bar is not None:
                reasons.append(f"active_bar={effect.active_bar.value}")
            if effect.chance is not None and effect.chance < 1.0:
                reasons.append(f"chance={effect.chance:g}")

            magnitude = effect.magnitude
            if magnitude is None:
                reasons.append("magnitude missing")
            else:
                try:
                    seconds = float(magnitude)
                except (TypeError, ValueError):
                    seconds = float("nan")
                if not math.isfinite(seconds) or seconds <= 0.0:
                    reasons.append(f"invalid magnitude={magnitude!r}")

            if reasons:
                unresolved.append(
                    "canonical potion cooldown reduction cannot be folded into static cadence: "
                    f"{source} ({', '.join(reasons)})"
                )
                continue

            reductions.append(
                RotationPotionCooldownEffectReduction(
                    source=source,
                    seconds=float(magnitude),
                    layer=effect.layer.value,
                )
            )

        return RotationPotionCooldownEffectEvidence(
            reductions=tuple(reductions),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "POTION_COOLDOWN_REDUCTION_EFFECT",
    "RotationPotionCooldownEffectEvidence",
    "RotationPotionCooldownEffectReduction",
    "RotationPotionCooldownEffectVariantService",
]
