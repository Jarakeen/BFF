from __future__ import annotations

"""Collect exact potion-relevant DD observation points from finalized runtime evidence.

This service does not schedule damage. It only collects timestamps already owned by
the finalized RotationPlan, reviewed periodic-runtime projections, and verified Heavy
Attack completion evidence.
"""

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    RotationPeriodicDamageRuntimeProjection,
)
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)


_DIRECT_DAMAGE_ACTION_KINDS = {
    RotationActionKind.SKILL,
    RotationActionKind.ULTIMATE,
    RotationActionKind.LIGHT_ATTACK,
}
_EPSILON = 1e-9
_PRECISION = 9


def _seconds(value: float) -> float:
    return round(float(value), _PRECISION)


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionObservationPoint:
    time_seconds: float
    sequence: int | None
    source: str
    kind: str

    def __post_init__(self) -> None:
        if isinstance(self.time_seconds, bool) or not isinstance(self.time_seconds, (int, float)):
            raise TypeError("potion observation time must be numeric")
        time_seconds = float(self.time_seconds)
        if not math.isfinite(time_seconds) or time_seconds < 0.0:
            raise ValueError("potion observation time must be finite and non-negative")
        if not isinstance(self.source, str):
            raise TypeError("potion observation point source must be a string")
        if not isinstance(self.kind, str):
            raise TypeError("potion observation point kind must be a string")
        source = self.source.strip()
        kind = self.kind.strip()
        if not source:
            raise ValueError("potion observation point requires source")
        if not kind:
            raise ValueError("potion observation point requires kind")
        if self.sequence is not None and (
            isinstance(self.sequence, bool) or not isinstance(self.sequence, int)
        ):
            raise TypeError("potion observation sequence must be an integer or None")
        sequence = self.sequence
        if sequence is not None and sequence < 0:
            raise ValueError("potion observation sequence cannot be negative")
        object.__setattr__(self, "time_seconds", _seconds(time_seconds))
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "kind", kind)


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionObservationFrontier:
    points: tuple[ExtremeSustainedDPSPotionObservationPoint, ...]
    observation_times: tuple[float, ...]
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSPotionObservationFrontierService:
    """Collect finite DD runtime observation coordinates for potion timing proof."""

    @staticmethod
    def _heavy_evidence_by_action(
        evidence: tuple[RotationHeavyAttackCompletionEvidence, ...],
    ) -> dict[tuple[float, int], RotationHeavyAttackCompletionEvidence]:
        indexed: dict[tuple[float, int], RotationHeavyAttackCompletionEvidence] = {}
        for item in evidence:
            key = (_seconds(item.action_time_seconds), int(item.action_sequence))
            if key in indexed:
                raise ValueError(
                    "duplicate Heavy Attack completion evidence for "
                    f"{item.action_time_seconds:g}s sequence {item.action_sequence}"
                )
            indexed[key] = item
        return indexed

    @classmethod
    def collect(
        cls,
        *,
        plan: RotationPlan,
        periodic_projections: tuple[RotationPeriodicDamageRuntimeProjection, ...] = (),
        heavy_attack_completion_evidence: tuple[
            RotationHeavyAttackCompletionEvidence, ...
        ] = (),
    ) -> ExtremeSustainedDPSPotionObservationFrontier:
        if not isinstance(periodic_projections, tuple):
            raise TypeError("periodic_projections must be a tuple")
        if any(
            not isinstance(item, RotationPeriodicDamageRuntimeProjection)
            for item in periodic_projections
        ):
            raise TypeError(
                "periodic_projections must contain RotationPeriodicDamageRuntimeProjection records"
            )
        if not isinstance(heavy_attack_completion_evidence, tuple):
            raise TypeError("heavy_attack_completion_evidence must be a tuple")
        if any(
            not isinstance(item, RotationHeavyAttackCompletionEvidence)
            for item in heavy_attack_completion_evidence
        ):
            raise TypeError(
                "heavy_attack_completion_evidence must contain RotationHeavyAttackCompletionEvidence records"
            )

        points: list[ExtremeSustainedDPSPotionObservationPoint] = []
        unresolved: list[str] = []
        heavy_by_action = cls._heavy_evidence_by_action(
            heavy_attack_completion_evidence
        )

        scheduled_heavy_keys = {
            (_seconds(action.time_seconds), int(action.sequence))
            for action in plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        }
        extra_heavy = tuple(
            key for key in heavy_by_action if key not in scheduled_heavy_keys
        )
        if extra_heavy:
            unresolved.append(
                "Heavy Attack completion evidence contains entries with no scheduled Heavy Attack"
            )

        for action in plan.actions:
            if action.kind in _DIRECT_DAMAGE_ACTION_KINDS:
                points.append(
                    ExtremeSustainedDPSPotionObservationPoint(
                        time_seconds=action.time_seconds,
                        sequence=action.sequence,
                        source=str(action.name or action.kind.value),
                        kind=action.kind.value,
                    )
                )
                continue

            if action.kind is RotationActionKind.HEAVY_ATTACK:
                key = (_seconds(action.time_seconds), int(action.sequence))
                completion = heavy_by_action.get(key)
                if completion is None:
                    unresolved.append(
                        "Scheduled Heavy Attack at "
                        f"{action.time_seconds:g}s sequence {action.sequence} "
                        "lacks verified completion evidence for potion observation timing"
                    )
                    continue
                if completion.completion_time_seconds > plan.duration_seconds + _EPSILON:
                    unresolved.append(
                        "Heavy Attack completion at "
                        f"{completion.completion_time_seconds:g}s exceeds rotation horizon"
                    )
                    continue
                points.append(
                    ExtremeSustainedDPSPotionObservationPoint(
                        time_seconds=completion.completion_time_seconds,
                        sequence=None,
                        source=str(action.name or "Heavy Attack"),
                        kind="heavy_attack_completion",
                    )
                )

        for projection_index, projection in enumerate(periodic_projections):
            if projection.unresolved:
                unresolved.extend(
                    f"Periodic projection {projection_index}: {item}"
                    for item in projection.unresolved
                    if str(item).strip()
                )
            for entry in projection.entries:
                if entry.unresolved:
                    unresolved.extend(
                        f"Periodic projection {projection_index}: {item}"
                        for item in entry.unresolved
                        if str(item).strip()
                    )
                    continue
                for event in entry.events:
                    if event.time_seconds > plan.duration_seconds + _EPSILON:
                        unresolved.append(
                            "Periodic runtime event at "
                            f"{event.time_seconds:g}s exceeds rotation horizon"
                        )
                        continue
                    points.append(
                        ExtremeSustainedDPSPotionObservationPoint(
                            time_seconds=event.time_seconds,
                            sequence=None,
                            source=str(event.source or entry.action.name or "periodic damage"),
                            kind="periodic_tick",
                        )
                    )

        unique: dict[tuple[float, int | None, str, str], ExtremeSustainedDPSPotionObservationPoint] = {}
        for point in points:
            key = (
                point.time_seconds,
                point.sequence,
                point.source.casefold(),
                point.kind.casefold(),
            )
            unique.setdefault(key, point)
        ordered = tuple(
            sorted(
                unique.values(),
                key=lambda row: (
                    row.time_seconds,
                    -1 if row.sequence is None else row.sequence,
                    row.kind.casefold(),
                    row.source.casefold(),
                ),
            )
        )
        observation_times = tuple(
            sorted({point.time_seconds for point in ordered})
        )
        deduped_unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )

        return ExtremeSustainedDPSPotionObservationFrontier(
            points=ordered,
            observation_times=observation_times,
            denominator_proven=bool(observation_times and not deduped_unresolved),
            evidence=(
                f"Scheduled direct-damage observation points: {sum(point.kind in {'skill', 'ultimate', 'light_attack'} for point in ordered)}",
                f"Verified Heavy Attack completion observations: {sum(point.kind == 'heavy_attack_completion' for point in ordered)}",
                f"Reviewed periodic tick observations: {sum(point.kind == 'periodic_tick' for point in ordered)}",
                f"Unique observation timestamps: {len(observation_times)}",
                "Observation collection reuses finalized plan/runtime evidence and does not schedule damage independently",
            ),
            unresolved=deduped_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSPotionObservationFrontier",
    "ExtremeSustainedDPSPotionObservationFrontierService",
    "ExtremeSustainedDPSPotionObservationPoint",
]
