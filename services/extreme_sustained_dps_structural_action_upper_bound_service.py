from __future__ import annotations

"""Structural sustained-DPS ceiling from proven action-count and per-action maxima.

This service owns arithmetic only. It does not infer ESO global cooldowns, action
rates, skill coefficients, proc cadence, or damage formulas. Callers must prove both:
1) the maximum number of damage-bearing scheduled actions any descendant of the branch
   can contain over the exact comparison horizon; and
2) an absolute optimistic total-damage ceiling for any one such action, including all
   direct, periodic, and triggered consequences attributable to that action inside the
   same horizon.

When both are complete, branch DPS <= count * per_action_ceiling / duration.
"""

from dataclasses import dataclass
from math import isfinite

from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSDamageActionCountProof:
    maximum_damage_action_count: int | None
    proven_safe: bool
    source: str
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.maximum_damage_action_count is not None:
            count = int(self.maximum_damage_action_count)
            if count < 0:
                raise ValueError("maximum damage-action count cannot be negative")
            object.__setattr__(self, "maximum_damage_action_count", count)
        object.__setattr__(self, "source", str(self.source or "").strip())
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )

    @property
    def complete(self) -> bool:
        return (
            self.maximum_damage_action_count is not None
            and self.proven_safe
            and not self.unresolved
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSAbsoluteActionDamageCeiling:
    upper_bound_damage: float | None
    proven_safe: bool
    covers_periodic_and_triggered: bool
    source: str
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.upper_bound_damage is not None:
            value = float(self.upper_bound_damage)
            if not isfinite(value) or value < 0.0:
                raise ValueError(
                    "absolute action damage ceiling must be finite and non-negative"
                )
            object.__setattr__(self, "upper_bound_damage", value)
        object.__setattr__(self, "source", str(self.source or "").strip())
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )

    @property
    def complete(self) -> bool:
        return (
            self.upper_bound_damage is not None
            and self.proven_safe
            and self.covers_periodic_and_triggered
            and not self.unresolved
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSStructuralActionCeiling:
    candidate_key: str
    duration_seconds: float
    maximum_damage_action_count: int | None
    absolute_action_damage_ceiling: float | None
    bound: ExtremeSustainedDPSBoundEvidence
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSStructuralActionUpperBoundService:
    """Promote structural count × absolute-action proof into a branch DPS ceiling."""

    @classmethod
    def evaluate(
        cls,
        candidate_key: str,
        *,
        duration_seconds: float,
        action_count: ExtremeSustainedDPSDamageActionCountProof,
        action_damage: ExtremeSustainedDPSAbsoluteActionDamageCeiling,
    ) -> ExtremeSustainedDPSStructuralActionCeiling:
        key = str(candidate_key or "").strip()
        if not key:
            raise ValueError("structural action ceiling requires candidate_key")

        duration = float(duration_seconds)
        if not isfinite(duration) or duration <= 0.0:
            raise ValueError(
                "structural action ceiling duration must be finite and positive"
            )

        unresolved: list[str] = []
        unresolved.extend(
            f"action-count proof: {item}" for item in action_count.unresolved
        )
        unresolved.extend(
            f"action-damage proof: {item}" for item in action_damage.unresolved
        )

        if action_count.maximum_damage_action_count is None:
            unresolved.append("Maximum damage-bearing action count is unavailable")
        elif not action_count.proven_safe:
            unresolved.append(
                "Maximum damage-bearing action count exists but is not proven safe"
            )

        if action_damage.upper_bound_damage is None:
            unresolved.append("Absolute per-action damage ceiling is unavailable")
        elif not action_damage.proven_safe:
            unresolved.append(
                "Absolute per-action damage ceiling exists but is not proven safe"
            )
        if not action_damage.covers_periodic_and_triggered:
            unresolved.append(
                "Absolute per-action ceiling does not cover all periodic/triggered consequences"
            )

        complete = action_count.complete and action_damage.complete and not unresolved
        upper_dps = None
        if complete:
            upper_damage = (
                int(action_count.maximum_damage_action_count)
                * float(action_damage.upper_bound_damage)
            )
            upper_dps = upper_damage / duration

        deduped = tuple(dict.fromkeys(item for item in unresolved if item))
        bound = ExtremeSustainedDPSBoundEvidence(
            candidate_key=key,
            upper_bound_dps=upper_dps,
            proven_safe=bool(complete),
            source=(
                "proven maximum damage-action count × proven absolute per-action "
                "damage ceiling / exact horizon"
            ),
            unresolved=deduped,
        )
        return ExtremeSustainedDPSStructuralActionCeiling(
            candidate_key=key,
            duration_seconds=duration,
            maximum_damage_action_count=action_count.maximum_damage_action_count,
            absolute_action_damage_ceiling=action_damage.upper_bound_damage,
            bound=bound,
            evidence=(
                f"Comparison horizon: {duration:g}s",
                (
                    "Proven maximum damage-bearing scheduled actions: "
                    + (
                        str(action_count.maximum_damage_action_count)
                        if action_count.maximum_damage_action_count is not None
                        else "unavailable"
                    )
                ),
                (
                    "Proven absolute per-action total-damage ceiling: "
                    + (
                        f"{float(action_damage.upper_bound_damage):g}"
                        if action_damage.upper_bound_damage is not None
                        else "unavailable"
                    )
                ),
                (
                    f"Structural sustained-DPS ceiling: {upper_dps:g}"
                    if upper_dps is not None
                    else "Structural sustained-DPS ceiling: unavailable"
                ),
                "No ESO action-rate or damage formula is inferred by this service",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSAbsoluteActionDamageCeiling",
    "ExtremeSustainedDPSDamageActionCountProof",
    "ExtremeSustainedDPSStructuralActionCeiling",
    "ExtremeSustainedDPSStructuralActionUpperBoundService",
]
