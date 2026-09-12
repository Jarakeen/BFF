from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.skill_coefficient_repository import ability_entity_id
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
)
from services.rotation_dd_periodic_esologs_anchor_correlation_service import (
    RotationDDPeriodicEsoLogsCastImpactObservation,
)
from services.rotation_runtime_activation_anchor_evidence_service import (
    RotationRuntimeActivationAnchorEvidence,
)


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsReplayAnchorMappingResult:
    evidence: tuple[RotationRuntimeActivationAnchorEvidence, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsReplayAnchorMappingService:
    """Map exact observed ESO Logs cast/impact pairs onto exact replay actions.

    The caller supplies the replay origin that places ESO Logs timestamps onto the
    rotation-plan clock. Matching then requires an exact plan timestamp and canonical
    skill identity. This service deliberately does not search for the nearest action,
    infer a travel delay, or use numeric ESO ability IDs as executable identity.

    Only cast-track-linked impact observations are eligible to become semantic runtime
    activation-anchor evidence. Weaker fallback correlations remain observational.
    """

    _EPSILON = 1e-9

    def map(
        self,
        *,
        plan: RotationPlan,
        observations: tuple[RotationDDPeriodicEsoLogsCastImpactObservation, ...],
        replay_origin_timestamp_ms: float,
    ) -> RotationDDPeriodicEsoLogsReplayAnchorMappingResult:
        origin = float(replay_origin_timestamp_ms)
        if not math.isfinite(origin) or origin < 0.0:
            raise ValueError("replay origin timestamp must be finite and non-negative")

        evidence_by_action: dict[
            tuple[float, int], RotationRuntimeActivationAnchorEvidence
        ] = {}
        blocked_actions: set[tuple[float, int]] = set()
        unresolved: list[str] = []

        for observation in tuple(observations):
            if not isinstance(
                observation, RotationDDPeriodicEsoLogsCastImpactObservation
            ):
                raise TypeError(
                    "ESO Logs replay anchor mapping requires exact cast-impact observations"
                )

            provenance = self._provenance(observation)
            if not observation.cast_track_linked:
                unresolved.append(
                    f"{provenance}: impact is not cast-track-linked; replay mapping remains observational"
                )
                continue

            cast_time = (float(observation.cast_timestamp_ms) - origin) / 1000.0
            impact_time = (float(observation.impact_timestamp_ms) - origin) / 1000.0
            if cast_time < -self._EPSILON:
                unresolved.append(f"{provenance}: cast precedes the replay origin")
                continue
            if impact_time + self._EPSILON < cast_time:
                unresolved.append(f"{provenance}: impact precedes its observed cast")
                continue

            cast_time = 0.0 if abs(cast_time) <= self._EPSILON else cast_time
            impact_time = 0.0 if abs(impact_time) <= self._EPSILON else impact_time
            identity = ability_entity_id(observation.skill_entity_id)
            candidates = tuple(
                action
                for action in plan.actions
                if action.kind is RotationActionKind.SKILL
                and ability_entity_id(action.name or "") == identity
                and abs(float(action.time_seconds) - cast_time) <= self._EPSILON
            )
            if not candidates:
                unresolved.append(
                    f"{provenance}: no exact {identity} rotation action exists at {cast_time:g}s"
                )
                continue
            if len(candidates) != 1:
                unresolved.append(
                    f"{provenance}: {len(candidates)} exact {identity} rotation actions exist at {cast_time:g}s"
                )
                continue

            action = candidates[0]
            action_key = (float(action.time_seconds), int(action.sequence))
            if action_key in blocked_actions:
                continue

            row = RotationRuntimeActivationAnchorEvidence(
                skill_entity_id=identity,
                action_time_seconds=float(action.time_seconds),
                action_sequence=int(action.sequence),
                activation_anchor=PeriodicDamageActivationAnchor.IMPACT,
                anchor_time_seconds=impact_time,
                source=provenance,
            )
            existing = evidence_by_action.get(action_key)
            if existing is None:
                evidence_by_action[action_key] = row
                continue
            if (
                abs(existing.anchor_time_seconds - row.anchor_time_seconds)
                <= self._EPSILON
            ):
                continue

            evidence_by_action.pop(action_key, None)
            blocked_actions.add(action_key)
            unresolved.append(
                f"{provenance}: conflicting exact impact observations map to the same rotation action"
            )

        return RotationDDPeriodicEsoLogsReplayAnchorMappingResult(
            evidence=tuple(
                evidence_by_action[key]
                for key in sorted(evidence_by_action)
                if key not in blocked_actions
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _provenance(
        observation: RotationDDPeriodicEsoLogsCastImpactObservation,
    ) -> str:
        track = (
            f" track {observation.cast_track_id}"
            if observation.cast_track_id is not None
            else ""
        )
        return (
            f"ESO Logs report {observation.report_code} fight {observation.fight_id} "
            f"source {observation.source_id}{track} cast event "
            f"{observation.cast_event_index} impact event {observation.impact_event_index}"
        )


__all__ = [
    "RotationDDPeriodicEsoLogsReplayAnchorMappingResult",
    "RotationDDPeriodicEsoLogsReplayAnchorMappingService",
]
