from __future__ import annotations

"""Finite resource-event observation frontier for finalized potion timing."""

from dataclasses import dataclass
import math

from minmax.recovery_timing import IN_COMBAT_RECOVERY_INTERVAL_SECONDS
from minmax.rotation_plan import RotationPlan
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)


_PRECISION = 9
_EPSILON = 1e-9


def _seconds(value: float) -> float:
    return round(float(value), _PRECISION)


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionResourceObservationFrontier:
    observation_times: tuple[float, ...]
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSPotionResourceObservationFrontierService:
    """Collect every modeled resource-timeline timestamp relevant to potion restore timing.

    Scheduled action timestamps are intentionally over-inclusive: some actions may
    ultimately have no primary-resource cost, but retaining an extra breakpoint is
    proof-safe. Ordinary recovery ticks are deterministic at the canonical two-second
    cadence. Heavy Attack completion timestamps are included because verified heavy
    restoration may share the resource timeline with potion restoration.

    Any other resource-maximum or restoration event family must be supplied explicitly,
    together with a caller proof that the supplied family is complete for the modeled
    descendant. This service never infers hidden proc/resource events.
    """

    @classmethod
    def collect(
        cls,
        *,
        plan: RotationPlan,
        heavy_attack_completion_evidence: tuple[
            RotationHeavyAttackCompletionEvidence, ...
        ] = (),
        additional_resource_event_times: tuple[float, ...] = (),
        additional_resource_event_denominator_proven: bool = False,
    ) -> ExtremeSustainedDPSPotionResourceObservationFrontier:
        if not isinstance(heavy_attack_completion_evidence, tuple):
            raise TypeError("heavy_attack_completion_evidence must be a tuple")
        if not isinstance(additional_resource_event_times, tuple):
            raise TypeError("additional_resource_event_times must be a tuple")
        if not isinstance(additional_resource_event_denominator_proven, bool):
            raise TypeError("additional_resource_event_denominator_proven must be boolean")

        duration = float(plan.duration_seconds)
        if not math.isfinite(duration) or duration <= 0.0:
            raise ValueError(
                "potion resource observation frontier requires positive finite duration"
            )

        unresolved: list[str] = []
        values: set[float] = {
            _seconds(action.time_seconds)
            for action in plan.actions
            if 0.0 <= float(action.time_seconds) <= duration + _EPSILON
        }

        tick = float(IN_COMBAT_RECOVERY_INTERVAL_SECONDS)
        while tick <= duration + _EPSILON:
            values.add(_seconds(tick))
            tick = round(
                tick + float(IN_COMBAT_RECOVERY_INTERVAL_SECONDS),
                _PRECISION,
            )

        scheduled_heavy_keys = {
            (_seconds(action.time_seconds), int(action.sequence))
            for action in plan.actions
            if action.kind.value == "heavy_attack"
        }
        seen_heavy: set[tuple[float, int]] = set()
        for item in heavy_attack_completion_evidence:
            key = (_seconds(item.action_time_seconds), int(item.action_sequence))
            if key in seen_heavy:
                raise ValueError(
                    "duplicate Heavy Attack completion evidence for potion resource observation"
                )
            seen_heavy.add(key)
            if key not in scheduled_heavy_keys:
                unresolved.append(
                    "Heavy Attack completion evidence has no matching scheduled heavy"
                )
                continue
            completion = float(item.completion_time_seconds)
            if completion > duration + _EPSILON:
                unresolved.append(
                    f"Heavy Attack completion at {completion:g}s exceeds rotation horizon"
                )
                continue
            values.add(_seconds(completion))

        for raw in additional_resource_event_times:
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise TypeError(
                    "additional potion resource observation times must be numeric"
                )
            value = float(raw)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(
                    "additional potion resource observation times must be finite and non-negative"
                )
            if value > duration + _EPSILON:
                raise ValueError(
                    "additional potion resource observation time exceeds rotation duration"
                )
            values.add(_seconds(value))

        if not additional_resource_event_denominator_proven:
            unresolved.append(
                "Additional resource maximum/restoration event denominator is not proven complete"
            )

        ordered = tuple(sorted(values))
        deduped = tuple(dict.fromkeys(unresolved))
        return ExtremeSustainedDPSPotionResourceObservationFrontier(
            observation_times=ordered,
            denominator_proven=bool(ordered and not deduped),
            evidence=(
                f"Scheduled action timestamps retained: {len(plan.actions)}",
                f"Canonical recovery cadence: {IN_COMBAT_RECOVERY_INTERVAL_SECONDS:g}s",
                f"Verified Heavy Attack completion rows: {len(tuple(heavy_attack_completion_evidence))}",
                f"Caller-supplied additional resource-event timestamps: {len(tuple(additional_resource_event_times))}",
                f"Unique resource observation timestamps: {len(ordered)}",
                "Scheduled action timestamps are deliberately over-inclusive; extra breakpoints cannot invalidate continuous-time closure",
                "Additional resource maximum/restoration event families require explicit caller denominator proof",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSPotionResourceObservationFrontier",
    "ExtremeSustainedDPSPotionResourceObservationFrontierService",
]
