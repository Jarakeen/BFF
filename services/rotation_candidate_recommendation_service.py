from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from minmax.demand_action_claim_duration_scheduler import DemandActionClaim
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
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
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_role_aware_ranking_service import (
    RotationRoleAwareRankingInput,
    RotationRoleAwareRankingResult,
    RotationRoleAwareRankingService,
)
from services.rotation_candidate_ranking_service import RotationCandidateTier


@dataclass(frozen=True)
class RotationCandidateRecommendationEvidence:
    """Authoritative downstream evidence used to judge one generated whole plan.

    This service deliberately does not calculate ESO mechanics. Callers provide a
    scorecard from the shared candidate-evaluation path plus explicit role-policy
    measurements from the appropriate damage/support/workload services. Unknown
    role-critical evidence remains ``None`` and therefore fails closed in the
    role-aware ranking layer instead of being silently converted to zero.

    Role-specific hard obligations remain a separate channel from the generic
    scorecard so encounter healer criteria, future tank checks, and similar role
    gates do not masquerade as missing support effects or unresolved mechanics.
    """

    candidate_id: str
    scorecard: RotationCandidateScorecard
    role_output_value: float | None
    assigned_support_value: float | None
    sustain_margin: float | None
    primary_role_displacement_seconds: float | None
    role_hard_obligation_satisfied: bool | None = True
    role_hard_obligation_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("rotation recommendation evidence candidate_id is required")
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(
            self,
            "role_hard_obligation_reasons",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.role_hard_obligation_reasons
                    if str(item).strip()
                )
            ),
        )


class RotationCandidateRecommendationEvidenceProvider(Protocol):
    """Adapter from canonical whole-plan evaluation into recommendation evidence."""

    def evaluate(
        self,
        *,
        baseline: GeneratedRotationCandidate,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRecommendationEvidence: ...


@dataclass(frozen=True)
class RotationCandidateRecommendationEntry:
    candidate: GeneratedRotationCandidate
    evidence: RotationCandidateRecommendationEvidence
    ranking: RotationRoleAwareRankingResult

    @property
    def reasons(self) -> tuple[str, ...]:
        """Hard-validity reasons first, then role-policy reasons."""
        return self.ranking.base_ranking.reasons + self.ranking.role_reasons


@dataclass(frozen=True)
class RotationCandidateRecommendationResult:
    """Ordered candidate family with an optional safe recommendation.

    ``recommended`` is intentionally ``None`` when no candidate satisfies both the
    shared hard gates and role-critical evidence requirements. The first ordered
    candidate remains available through ``best_available`` for diagnostics, but an
    ineligible plan is never mislabeled as a recommendation.
    """

    entries: tuple[RotationCandidateRecommendationEntry, ...]
    recommended: RotationCandidateRecommendationEntry | None

    @property
    def best_available(self) -> RotationCandidateRecommendationEntry | None:
        return self.entries[0] if self.entries else None

    @property
    def has_recommendation(self) -> bool:
        return self.recommended is not None


class RotationCandidateRecommendationService:
    """Orchestrate candidate generation, evidence evaluation, ranking, and explanation.

    Mechanics remain owned by the generator/refiner and shared evaluation services.
    This layer only keeps candidate identity aligned, invokes the existing
    role-aware lexicographic ranking policy, and returns the winning whole plan with
    its evidence and explanation. It never invents a weighted score or encounter
    strategy.
    """

    def __init__(
        self,
        generation_service: RotationCandidateGenerationService | None = None,
        ranking_service: RotationRoleAwareRankingService | None = None,
    ) -> None:
        self.generation_service = generation_service or RotationCandidateGenerationService()
        self.ranking_service = ranking_service or RotationRoleAwareRankingService()

    def generate_and_recommend(
        self,
        *,
        evidence_provider: RotationCandidateRecommendationEvidenceProvider,
        role_key: str,
        role_output_label: str,
        assigned_support_label: str,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...] = (),
        options: tuple[RotationRefreshLeadCandidateOption, ...] = (),
        action_claims: tuple[DemandActionClaim, ...] = (),
        wait_decision: PrematureRecastDecisionProvider | None = None,
        wait_decision_factory: RotationCandidateWaitDecisionFactory | None = None,
        baseline_id: str = "baseline",
    ) -> RotationCandidateRecommendationResult:
        candidates = self.generation_service.generate(
            seed_plan=seed_plan,
            priorities=priorities,
            demands=demands,
            options=options,
            action_claims=action_claims,
            wait_decision=wait_decision,
            wait_decision_factory=wait_decision_factory,
            baseline_id=baseline_id,
        )
        return self.recommend(
            candidates=candidates,
            evidence_provider=evidence_provider,
            role_key=role_key,
            role_output_label=role_output_label,
            assigned_support_label=assigned_support_label,
        )

    def recommend(
        self,
        *,
        candidates: tuple[GeneratedRotationCandidate, ...],
        evidence_provider: RotationCandidateRecommendationEvidenceProvider,
        role_key: str,
        role_output_label: str,
        assigned_support_label: str,
    ) -> RotationCandidateRecommendationResult:
        candidates = tuple(candidates)
        if not candidates:
            return RotationCandidateRecommendationResult(entries=(), recommended=None)

        self._validate_candidate_ids(candidates)
        baseline = candidates[0]
        evidence_by_id: dict[str, RotationCandidateRecommendationEvidence] = {}
        ranking_inputs: list[RotationRoleAwareRankingInput] = []

        for candidate in candidates:
            evidence = evidence_provider.evaluate(
                baseline=baseline,
                candidate=candidate,
            )
            if evidence.candidate_id.casefold() != candidate.candidate_id.casefold():
                raise ValueError(
                    "rotation recommendation evidence candidate mismatch: "
                    f"expected {candidate.candidate_id!r}, got {evidence.candidate_id!r}"
                )
            key = candidate.candidate_id.casefold()
            if key in evidence_by_id:
                raise ValueError(
                    f"duplicate rotation recommendation evidence for {candidate.candidate_id!r}"
                )
            evidence_by_id[key] = evidence
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
                    role_hard_obligation_satisfied=(
                        evidence.role_hard_obligation_satisfied
                    ),
                    role_hard_obligation_reasons=(
                        evidence.role_hard_obligation_reasons
                    ),
                )
            )

        ranked = self.ranking_service.rank(tuple(ranking_inputs))
        candidate_by_id = {item.candidate_id.casefold(): item for item in candidates}
        entries = tuple(
            RotationCandidateRecommendationEntry(
                candidate=candidate_by_id[item.candidate_id.casefold()],
                evidence=evidence_by_id[item.candidate_id.casefold()],
                ranking=item,
            )
            for item in ranked
        )
        recommended = next(
            (
                entry
                for entry in entries
                if entry.ranking.tier is RotationCandidateTier.ELIGIBLE
            ),
            None,
        )
        return RotationCandidateRecommendationResult(
            entries=entries,
            recommended=recommended,
        )

    @staticmethod
    def _validate_candidate_ids(
        candidates: tuple[GeneratedRotationCandidate, ...],
    ) -> None:
        seen: set[str] = set()
        for candidate in candidates:
            candidate_id = str(candidate.candidate_id or "").strip()
            if not candidate_id:
                raise ValueError("rotation recommendation candidate_id is required")
            key = candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate rotation recommendation candidate_id: {candidate.candidate_id!r}"
                )
            seen.add(key)


__all__ = [
    "RotationCandidateRecommendationEntry",
    "RotationCandidateRecommendationEvidence",
    "RotationCandidateRecommendationEvidenceProvider",
    "RotationCandidateRecommendationResult",
    "RotationCandidateRecommendationService",
]
