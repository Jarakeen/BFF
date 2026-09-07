from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
    RotationHeavyAttackRestorationEvidenceService,
    RotationHeavyAttackRestorationProjection,
)
from services.rotation_recovery_heavy_replay_service import (
    RotationRecoveryHeavyReplay,
    RotationRecoveryHeavyReplayService,
)


@dataclass(frozen=True)
class RotationHeavySustainProjection:
    """Pre-scorecard sustain evidence after verified heavy restoration replay.

    A resolved projection is safe to hand to RotationCandidateScorecardService as
    `candidate_sustain`. Unresolved heavy completion/weapon evidence never becomes a
    zero-value restore or a silently ignored mechanic.
    """

    restoration_projection: RotationHeavyAttackRestorationProjection
    replay: RotationRecoveryHeavyReplay | None
    unresolved: tuple[str, ...]

    @property
    def is_resolved(self) -> bool:
        return self.replay is not None and not self.unresolved

    @property
    def sustain_projection(self):
        """Final replayed sustain projection, when heavy evidence is complete."""
        return None if self.replay is None else self.replay.final_projection


class RotationHeavySustainProjectionService:
    """Replay build-aware heavy restores before scorecard hard obligations run.

    Ordering matters. Resource shortfall and reserve requirements are hard candidate
    obligations, so verified heavy restoration must alter the resource timeline
    before those obligations are assessed. Applying heavy restoration after ranking
    would make an otherwise valid candidate impossible to recover from an artificial
    pre-heavy shortfall.

    Heavy weapon identity comes from CharacterBuild. Runtime cost/sustain evaluation
    still uses the saved PlayerBuild bridge. Completion/full-charge/base-restore and
    modifiers remain explicit evidence. A heavy that restores a different resource
    than the resource currently being evaluated is resolved but irrelevant to that
    resource timeline, so it is ignored rather than treated as an error.
    """

    def __init__(
        self,
        *,
        restoration_service: RotationHeavyAttackRestorationEvidenceService | None = None,
        replay_service: RotationRecoveryHeavyReplayService | None = None,
    ) -> None:
        self.restoration_service = (
            restoration_service or RotationHeavyAttackRestorationEvidenceService()
        )
        self.replay_service = replay_service or RotationRecoveryHeavyReplayService()

    def project(
        self,
        *,
        character_build: CharacterBuild,
        sustain_build: PlayerBuild,
        plan: RotationPlan,
        resource: ResourceType,
        initial_bar: str,
        completion_evidence: tuple[RotationHeavyAttackCompletionEvidence, ...],
    ) -> RotationHeavySustainProjection:
        restoration = self.restoration_service.project(
            build=character_build,
            plan=plan,
            initial_bar=initial_bar,
            completion_evidence=tuple(completion_evidence),
        )

        unresolved = list(restoration.unresolved)
        unresolved.extend(
            f"heavy-attack weapon projection violation at "
            f"{item.action.time_seconds:.3f}s sequence {item.action.sequence}: {item.reason}"
            for item in restoration.weapon_projection.violations
        )
        if unresolved:
            return RotationHeavySustainProjection(
                restoration_projection=restoration,
                replay=None,
                unresolved=self._dedupe(tuple(unresolved)),
            )

        event_by_action = {
            (float(item.action.time_seconds), int(item.action.sequence)): item.restoration_event
            for item in restoration.resolutions
            if item.restoration_event is not None
            and item.restoration_event.resource is resource
        }

        def resolve(action: RotationAction):
            return event_by_action.get((float(action.time_seconds), int(action.sequence)))

        replay = self.replay_service.replay(
            build=sustain_build,
            plan=plan,
            resource=resource,
            restoration_resolver=resolve,
        )
        return RotationHeavySustainProjection(
            restoration_projection=restoration,
            replay=replay,
            unresolved=(),
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "RotationHeavySustainProjection",
    "RotationHeavySustainProjectionService",
]
