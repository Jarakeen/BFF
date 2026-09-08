from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild
from services.canonical_knowledge_gap import CanonicalKnowledgeGap
from services.encounter_provider_assignment import ProviderAssignment
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectObligationProjection,
    RotationAssignmentEffectObligationService,
    RotationAssignmentEffectPolicy,
)
from services.rotation_assignment_policy_resolver import (
    RotationAssignmentNonEffectPolicy,
    RotationAssignmentPolicyResolution,
    RotationAssignmentPolicyResolver,
)
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement


@dataclass(frozen=True)
class RotationAssignmentCanonicalEvidence:
    """Assignment-backed evidence ready for canonical rotation evaluation."""

    policy_resolution: RotationAssignmentPolicyResolution
    obligation_projection: RotationAssignmentEffectObligationProjection | None
    requirements: tuple[RotationEffectUptimeRequirement, ...]
    knowledge_gaps: tuple[CanonicalKnowledgeGap, ...]

    @property
    def ready(self) -> bool:
        return not self.knowledge_gaps


class RotationAssignmentCanonicalEvidenceService:
    """Translate assignment ownership into canonical runtime obligations.

    Policy resolution happens before obligation derivation so missing semantics never
    disappear through the low-level adapter's intentionally permissive "outside effect
    scope" behavior. Only a complete explicit disposition may proceed to runtime
    effect requirements.
    """

    def __init__(
        self,
        *,
        policy_resolver: RotationAssignmentPolicyResolver | None = None,
        obligation_service: RotationAssignmentEffectObligationService | None = None,
    ) -> None:
        self.policy_resolver = policy_resolver or RotationAssignmentPolicyResolver()
        self.obligation_service = obligation_service or RotationAssignmentEffectObligationService()

    def build(
        self,
        *,
        build: CharacterBuild,
        member_id: str,
        assignments: tuple[ProviderAssignment, ...],
        effect_policies: tuple[RotationAssignmentEffectPolicy, ...] = (),
        non_effect_policies: tuple[RotationAssignmentNonEffectPolicy, ...] = (),
    ) -> RotationAssignmentCanonicalEvidence:
        resolution = self.policy_resolver.resolve(
            member_id=member_id,
            assignments=tuple(assignments),
            effect_policies=tuple(effect_policies),
            non_effect_policies=tuple(non_effect_policies),
        )
        if not resolution.ready:
            return RotationAssignmentCanonicalEvidence(
                policy_resolution=resolution,
                obligation_projection=None,
                requirements=(),
                knowledge_gaps=resolution.knowledge_gaps,
            )

        projection = self.obligation_service.derive(
            build=build,
            member_id=member_id,
            assignments=tuple(assignments),
            policies=resolution.effect_policies,
        )
        return RotationAssignmentCanonicalEvidence(
            policy_resolution=resolution,
            obligation_projection=projection,
            requirements=projection.requirements,
            knowledge_gaps=(),
        )


__all__ = [
    "RotationAssignmentCanonicalEvidence",
    "RotationAssignmentCanonicalEvidenceService",
]
