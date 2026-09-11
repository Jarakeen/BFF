from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from minmax.demand_action_claim_duration_scheduler import DemandActionClaim
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationPlan
from minmax.rotation_wait_decision import PrematureRecastDecisionProvider
from services.rotation_candidate_generation_service import (
    GeneratedRotationCandidate,
    RotationCandidateGenerationService,
    RotationCandidateWaitDecisionFactory,
    RotationRefreshLeadCandidateOption,
)
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyAssessment,
)
from services.rotation_role_aware_ranking_service import (
    RotationRoleAwareRankingInput,
    RotationRoleAwareRankingResult,
    RotationRoleAwareRankingService,
)


@dataclass(frozen=True)
class RotationCandidateRoleEvidence:
    """Caller-proven role measurements for one already-generated whole plan."""

    scorecard: RotationCandidateScorecard
    role_output_value: float
    assigned_support_value: float
    sustain_margin: float
    primary_role_displacement_seconds: float
    gameplay_policy_assessment: RotationGameplayPolicyAssessment | None = None


RotationCandidateEvidenceEvaluator = Callable[
    [GeneratedRotationCandidate, GeneratedRotationCandidate],
    RotationCandidateRoleEvidence,
]


@dataclass(frozen=True)
class RotationCandidateRecommendationEntry:
    candidate: GeneratedRotationCandidate
    evidence: RotationCandidateRoleEvidence
    ranking: RotationRoleAwareRankingResult

    @property
    def reasons(self) -> tuple[str, ...]:
        """Hard-plan evidence first, then role-policy evidence."""
        return self.ranking.base_ranking.reasons + self.ranking.role_reasons


@dataclass(frozen=True)
class RotationCandidateFamilyRecommendation:
    """Ordered family judgment with fail-closed recommendation semantics."""

    entries: tuple[RotationCandidateRecommendationEntry, ...]
    recommended: RotationCandidateRecommendationEntry | None

    @property
    def has_recommendation(self) -> bool:
        return self.recommended is not None


class RotationCandidateFamilyRecommendationService:
    """Run candidate generation, whole-plan evaluation, and role-aware ranking.

    This is deliberately a thin orchestration layer. Candidate generation still owns
    schedule variants, the supplied evaluator still owns shared mechanics/scorecard
    truth, and the role-aware ranker still owns policy. The coordinator does not
    duplicate ESO calculations or invent a weighted score.

    The first generated candidate is the family baseline and is supplied to every
    evaluation so consequence services can make like-for-like comparisons. Shared
    encounter action claims are forwarded unchanged into family generation. If no
    generated candidate survives the shared hard gates, ``recommended`` is ``None``
    rather than blessing the least-bad invalid plan as a recommendation.
    """

    def __init__(
        self,
        generation_service: RotationCandidateGenerationService | None = None,
        ranking_service: RotationRoleAwareRankingService | None = None,
    ) -> None:
        self.generation_service = generation_service or RotationCandidateGenerationService()
        self.ranking_service = ranking_service or RotationRoleAwareRankingService()

    def recommend(
        self,
        *,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        evaluator: RotationCandidateEvidenceEvaluator,
        role_key: str,
        role_output_label: str,
        assigned_support_label: str,
        demands: tuple[RotationDemandWindow, ...] = (),
        options: tuple[RotationRefreshLeadCandidateOption, ...] = (),
        action_claims: tuple[DemandActionClaim, ...] = (),
        wait_decision: PrematureRecastDecisionProvider | None = None,
        wait_decision_factory: RotationCandidateWaitDecisionFactory | None = None,
        baseline_id: str = "baseline",
    ) -> RotationCandidateFamilyRecommendation:
        candidates = self.generation_service.generate(
            seed_plan=seed_plan,
            priorities=priorities,
            demands=tuple(demands),
            options=tuple(options),
            action_claims=tuple(action_claims),
            wait_decision=wait_decision,
            wait_decision_factory=wait_decision_factory,
            baseline_id=baseline_id,
        )
        if not candidates:
            return RotationCandidateFamilyRecommendation(entries=(), recommended=None)

        baseline = candidates[0]
        evidence_by_id: dict[str, RotationCandidateRoleEvidence] = {}
        candidate_by_id: dict[str, GeneratedRotationCandidate] = {}
        ranking_inputs: list[RotationRoleAwareRankingInput] = []

        for candidate in candidates:
            evidence = evaluator(candidate, baseline)
            if not isinstance(evidence, RotationCandidateRoleEvidence):
                raise TypeError(
                    "rotation candidate evaluator must return RotationCandidateRoleEvidence"
                )
            assessment = evidence.gameplay_policy_assessment
            if assessment is not None and assessment.candidate_id.casefold() != candidate.candidate_id.casefold():
                raise ValueError(
                    "rotation candidate gameplay-policy candidate mismatch: "
                    f"expected {candidate.candidate_id!r}, got {assessment.candidate_id!r}"
                )
            key = candidate.candidate_id.casefold()
            evidence_by_id[key] = evidence
            candidate_by_id[key] = candidate
            ranking_inputs.append(
                RotationRoleAwareRankingInput(
                    candidate_id=candidate.candidate_id,
                    scorecard=evidence.scorecard,
                    role_key=role_key,
                    role_output_value=evidence.role_output_value,
                    role_output_label=role_output_label,
                    assigned_support_value=evidence.assigned_support_value,
                    assigned_support_label=assigned_support_label,
                    sustain_margin=evidence.sustain_margin,
                    primary_role_displacement_seconds=(
                        evidence.primary_role_displacement_seconds
                    ),
                    gameplay_policy_assessment=(
                        evidence.gameplay_policy_assessment
                    ),
                )
            )

        ranked = self.ranking_service.rank(tuple(ranking_inputs))
        entries = tuple(
            RotationCandidateRecommendationEntry(
                candidate=candidate_by_id[item.candidate_id.casefold()],
                evidence=evidence_by_id[item.candidate_id.casefold()],
                ranking=item,
            )
            for item in ranked
        )
        recommended = (
            entries[0]
            if entries and entries[0].ranking.tier is RotationCandidateTier.ELIGIBLE
            else None
        )
        return RotationCandidateFamilyRecommendation(
            entries=entries,
            recommended=recommended,
        )


__all__ = [
    "RotationCandidateEvidenceEvaluator",
    "RotationCandidateFamilyRecommendation",
    "RotationCandidateFamilyRecommendationService",
    "RotationCandidateRecommendationEntry",
    "RotationCandidateRoleEvidence",
]
