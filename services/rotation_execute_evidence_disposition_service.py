from __future__ import annotations

"""Classify canonical execute evidence by current runtime support level."""

from dataclasses import dataclass
from enum import Enum

from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequenceType,
)
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteCandidateEvidenceService,
)
from services.rotation_reviewed_execute_amplification_service import (
    RotationReviewedExecuteAmplificationService,
)


class RotationExecuteEvidenceDisposition(str, Enum):
    THRESHOLD_ACTIVATION_SUPPORTED = "threshold_activation_supported"
    CONTINUOUS_AMPLIFICATION_SUPPORTED = "continuous_amplification_supported"
    CONTINUOUS_AMPLIFICATION_UNRESOLVED = "continuous_amplification_unresolved"
    NO_THRESHOLD_EVIDENCE = "no_threshold_evidence"
    IDENTITY_OR_SOURCE_UNRESOLVED = "identity_or_source_unresolved"


@dataclass(frozen=True)
class RotationExecuteEvidenceDispositionResult:
    skill_name: str
    disposition: RotationExecuteEvidenceDisposition
    evidence: RotationExecuteCandidateEvidence
    unresolved: tuple[str, ...] = ()

    @property
    def scheduler_supported(self) -> bool:
        return self.disposition in {
            RotationExecuteEvidenceDisposition.THRESHOLD_ACTIVATION_SUPPORTED,
            RotationExecuteEvidenceDisposition.CONTINUOUS_AMPLIFICATION_SUPPORTED,
        }


class RotationExecuteEvidenceDispositionService:
    """Separate runtime-supported execute evidence from unresolved scaling semantics."""

    def __init__(
        self,
        *,
        evidence_service: RotationExecuteCandidateEvidenceService | None = None,
        amplification: RotationReviewedExecuteAmplificationService | None = None,
    ) -> None:
        self.evidence_service = evidence_service or RotationExecuteCandidateEvidenceService()
        self.amplification = amplification or RotationReviewedExecuteAmplificationService()

    def resolve(self, skill_name: str) -> RotationExecuteEvidenceDispositionResult:
        evidence = self.evidence_service.resolve(skill_name)
        if evidence.resolved_skill_name is None:
            return RotationExecuteEvidenceDispositionResult(
                skill_name=str(skill_name or "").strip(),
                disposition=RotationExecuteEvidenceDisposition.IDENTITY_OR_SOURCE_UNRESOLVED,
                evidence=evidence,
                unresolved=tuple(evidence.unresolved)
                or ("canonical execute identity/source is unresolved",),
            )

        activations = tuple(
            row
            for row in evidence.components
            if row.consequence_type
            is SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT
        )
        amplifications = tuple(
            row
            for row in evidence.components
            if row.consequence_type
            is SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE
        )
        if amplifications:
            reviewed = self.amplification.semantics(evidence.resolved_skill_name)
            complete_maximums = all(
                row.maximum_bonus_fraction is not None for row in amplifications
            )
            if reviewed is not None and complete_maximums:
                return RotationExecuteEvidenceDispositionResult(
                    skill_name=evidence.resolved_skill_name,
                    disposition=RotationExecuteEvidenceDisposition.CONTINUOUS_AMPLIFICATION_SUPPORTED,
                    evidence=evidence,
                )

            detail = (
                "continuous target-missing-Health damage amplification has positive canonical "
                "evidence, but exact interpolation from threshold to maximum bonus is not yet "
                "source-verified; active damage remains fail-closed"
            )
            if reviewed is not None and not complete_maximums:
                detail = (
                    "continuous target-missing-Health damage amplification has reviewed "
                    "interpolation semantics, but maximum bonus evidence is incomplete; "
                    "active damage remains fail-closed"
                )
            return RotationExecuteEvidenceDispositionResult(
                skill_name=evidence.resolved_skill_name,
                disposition=RotationExecuteEvidenceDisposition.CONTINUOUS_AMPLIFICATION_UNRESOLVED,
                evidence=evidence,
                unresolved=(detail,),
            )

        if activations:
            return RotationExecuteEvidenceDispositionResult(
                skill_name=evidence.resolved_skill_name,
                disposition=RotationExecuteEvidenceDisposition.THRESHOLD_ACTIVATION_SUPPORTED,
                evidence=evidence,
            )

        if evidence.unresolved:
            return RotationExecuteEvidenceDispositionResult(
                skill_name=evidence.resolved_skill_name,
                disposition=RotationExecuteEvidenceDisposition.IDENTITY_OR_SOURCE_UNRESOLVED,
                evidence=evidence,
                unresolved=tuple(evidence.unresolved),
            )

        return RotationExecuteEvidenceDispositionResult(
            skill_name=evidence.resolved_skill_name,
            disposition=RotationExecuteEvidenceDisposition.NO_THRESHOLD_EVIDENCE,
            evidence=evidence,
        )


__all__ = [
    "RotationExecuteEvidenceDisposition",
    "RotationExecuteEvidenceDispositionResult",
    "RotationExecuteEvidenceDispositionService",
]
