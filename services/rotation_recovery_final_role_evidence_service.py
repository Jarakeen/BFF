from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidateGameplayPolicyContextProvider,
    RotationCandidatePlanEvidenceProvider,
)
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyAssessmentService,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyStabilizedCandidateSnapshot,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RecoveryFinalRoleAwareInputResolver,
    RecoveryFinalScorecardResolver,
)
from services.rotation_role_aware_ranking_service import RotationRoleAwareRankingInput


RotationSnapshotPlanEvidenceProviderFactory = Callable[
    [RecoveryHeavyStabilizedCandidateSnapshot],
    RotationCandidatePlanEvidenceProvider,
]


@dataclass(frozen=True)
class RotationRecoveryFinalRoleEvidenceConfiguration:
    """Explicit labels and role identity for final stabilized candidate ranking."""

    role_key: str
    role_output_label: str
    assigned_support_label: str

    def __post_init__(self) -> None:
        for field_name in ("role_key", "role_output_label", "assigned_support_label"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"{field_name} must be non-empty")
            object.__setattr__(self, field_name, value)


class RotationRecoveryFinalRoleEvidenceService:
    """Compose final stabilized recovery evidence into role-aware ranking input.

    The stabilized recovery replay is authoritative for sustain margin. Canonical
    plan evidence providers remain authoritative for role output, assigned-support
    coverage, displacement, and role-specific hard obligations. Gameplay-practice
    policy is assessed separately from mechanics through the existing context and
    policy services.

    Callers with final-plan runtime evidence may supply a snapshot-bound plan-evidence
    provider factory. It is invoked only after stabilization, so role-output services
    that need exact runtime state cannot accidentally bind themselves to a seed plan.
    Callers without runtime-sensitive role output continue to use the ordinary static
    plan-evidence provider.

    This adapter never recalculates the final scorecard. The caller supplies the
    same final scorecard resolver used by the recovery pipeline, and the pipeline
    still replaces the scorecard once more with its saved-build legality-decorated
    version before final selection. That deliberate redundancy prevents stale
    pre-recovery or pre-legality evidence from entering role-aware ranking.
    """

    def __init__(
        self,
        *,
        plan_evidence_provider: RotationCandidatePlanEvidenceProvider,
        scorecard_resolver: RecoveryFinalScorecardResolver,
        configuration: RotationRecoveryFinalRoleEvidenceConfiguration,
        snapshot_plan_evidence_provider_factory: (
            RotationSnapshotPlanEvidenceProviderFactory | None
        ) = None,
        gameplay_policy_context_provider: (
            RotationCandidateGameplayPolicyContextProvider | None
        ) = None,
        gameplay_policy_assessment_service: (
            RotationGameplayPolicyAssessmentService | None
        ) = None,
    ) -> None:
        self.plan_evidence_provider = plan_evidence_provider
        self.snapshot_plan_evidence_provider_factory = (
            snapshot_plan_evidence_provider_factory
        )
        self.scorecard_resolver = scorecard_resolver
        self.configuration = configuration
        self.gameplay_policy_context_provider = gameplay_policy_context_provider
        self.gameplay_policy_assessment_service = (
            gameplay_policy_assessment_service or RotationGameplayPolicyAssessmentService()
        )

    def resolver(self) -> RecoveryFinalRoleAwareInputResolver:
        return self.resolve

    def resolve(
        self,
        snapshot: RecoveryHeavyStabilizedCandidateSnapshot,
    ) -> RotationRoleAwareRankingInput:
        candidate = GeneratedRotationCandidate(
            candidate_id=snapshot.candidate_id,
            plan=snapshot.plan,
            refresh_leads=(),
        )
        provider = self.plan_evidence_provider
        if self.snapshot_plan_evidence_provider_factory is not None:
            provider = self.snapshot_plan_evidence_provider_factory(snapshot)
        evidence = provider.evaluate_plan(candidate)
        gameplay_policy_assessment = self._gameplay_policy_assessment(candidate)

        sustain_margin = float(
            snapshot.replay.final_projection.run.sustain.minimum_amount
        )
        configuration = self.configuration
        return RotationRoleAwareRankingInput(
            candidate_id=snapshot.candidate_id,
            scorecard=self.scorecard_resolver(snapshot),
            role_key=configuration.role_key,
            role_output_value=evidence.role_output_value,
            role_output_label=configuration.role_output_label,
            assigned_support_value=evidence.assigned_support_value,
            assigned_support_label=configuration.assigned_support_label,
            sustain_margin=sustain_margin,
            primary_role_displacement_seconds=(
                evidence.primary_role_displacement_seconds
            ),
            role_hard_obligation_satisfied=(
                evidence.role_hard_obligation_satisfied
            ),
            role_hard_obligation_reasons=(
                evidence.role_hard_obligation_reasons
            ),
            gameplay_policy_assessment=gameplay_policy_assessment,
        )

    def _gameplay_policy_assessment(self, candidate: GeneratedRotationCandidate):
        provider = self.gameplay_policy_context_provider
        if provider is None:
            return None
        context = provider.context_for(candidate)
        if context is None:
            return None
        if context.candidate_id.casefold() != candidate.candidate_id.casefold():
            raise ValueError(
                "final recovery gameplay-policy context candidate mismatch: "
                f"expected {candidate.candidate_id!r}, got {context.candidate_id!r}"
            )
        return self.gameplay_policy_assessment_service.assess_dd_personal_heal(context)


__all__ = [
    "RotationRecoveryFinalRoleEvidenceConfiguration",
    "RotationRecoveryFinalRoleEvidenceService",
    "RotationSnapshotPlanEvidenceProviderFactory",
]
