from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from services.encounter_provider_assignment import ProviderAssignment
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectObligationProjection,
    RotationAssignmentEffectObligationService,
    RotationAssignmentEffectPolicy,
)
from services.rotation_candidate_effect_evaluation_service import (
    RotationCandidateEffectEvaluationInput,
    RotationCandidateEffectEvaluationResult,
    RotationCandidateEffectEvaluationService,
)


@dataclass(frozen=True)
class RotationAssignmentCandidateEvaluationResult:
    """Assignment-derived obligation evidence plus final ranked candidates."""

    obligation_projection: RotationAssignmentEffectObligationProjection
    ranked_candidates: tuple[RotationCandidateEffectEvaluationResult, ...]


class _AssignmentObligationResolver(Protocol):
    def derive(
        self,
        *,
        build: CharacterBuild,
        member_id: str,
        assignments: tuple[ProviderAssignment, ...],
        policies: tuple[RotationAssignmentEffectPolicy, ...],
    ) -> RotationAssignmentEffectObligationProjection: ...


class _CandidateEffectEvaluator(Protocol):
    def evaluate_and_rank(
        self,
        *,
        build: CharacterBuild,
        candidates: tuple[RotationCandidateEffectEvaluationInput, ...],
        requirements=(),
        passives: Iterable[PassiveGrant] = (),
    ) -> tuple[RotationCandidateEffectEvaluationResult, ...]: ...


class RotationAssignmentCandidateEvaluationService:
    """Evaluate generated rotations directly from explicit provider assignments.

    This composition boundary removes the remaining manual handoff between provider
    ownership and candidate effect-uptime evaluation:

      ProviderAssignment + verified rotation policy
          -> build-owned RotationEffectUptimeRequirement(s)
          -> every generated candidate assessed against those requirements
          -> hard-gated final candidate ranking

    It does not infer strategy, effect identity, source skill, uptime target, or role
    convention. Those semantics must already be explicit in the supplied assignment
    and policy evidence.
    """

    def __init__(
        self,
        obligation_service: _AssignmentObligationResolver | None = None,
        candidate_service: _CandidateEffectEvaluator | None = None,
    ) -> None:
        self.obligation_service = (
            obligation_service or RotationAssignmentEffectObligationService()
        )
        self.candidate_service = (
            candidate_service or RotationCandidateEffectEvaluationService()
        )

    def evaluate_and_rank(
        self,
        *,
        build: CharacterBuild,
        member_id: str,
        assignments: tuple[ProviderAssignment, ...],
        policies: tuple[RotationAssignmentEffectPolicy, ...],
        candidates: tuple[RotationCandidateEffectEvaluationInput, ...],
        passives: Iterable[PassiveGrant] = (),
    ) -> RotationAssignmentCandidateEvaluationResult:
        projection = self.obligation_service.derive(
            build=build,
            member_id=member_id,
            assignments=tuple(assignments),
            policies=tuple(policies),
        )
        ranked = self.candidate_service.evaluate_and_rank(
            build=build,
            candidates=tuple(candidates),
            requirements=projection.requirements,
            passives=tuple(passives),
        )
        return RotationAssignmentCandidateEvaluationResult(
            obligation_projection=projection,
            ranked_candidates=tuple(ranked),
        )


__all__ = [
    "RotationAssignmentCandidateEvaluationResult",
    "RotationAssignmentCandidateEvaluationService",
]
