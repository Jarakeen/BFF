from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import isclose

from models.build_model import PlayerBuild

from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_capability import (
    compare_capability_coverage,
    compare_provider_responsibilities,
)
from minmax.build_candidate_comparison import BuildCandidateComparison
from minmax.build_candidate_context import BuildCandidateContextResult
from minmax.build_candidate_healing import ModeledHealingPotency, measure_modeled_healing_potency
from minmax.build_candidate_sustain import BuildCandidateSustainComparison
from minmax.evaluation_objective import EvaluationObjective
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from services.encounter_provider_assignment import ProviderAssignment
from services.saved_build_capability_service import SavedBuildCapabilityAudit, SavedBuildCapabilityService


ContextResolver = Callable[[BuildCandidate], BuildCandidateContextResult]
SustainResolver = Callable[[BuildCandidateContextResult], BuildCandidateSustainComparison]
AssignmentResolver = Callable[[PlayerBuild], tuple[ProviderAssignment, ...]]
ObjectiveCoverageResolver = Callable[[BuildCandidate], tuple[str, ...]]


@dataclass(frozen=True)
class HealingCandidateEvaluation:
    comparison: BuildCandidateComparison
    healing: ModeledHealingPotency | None
    sustain: BuildCandidateSustainComparison | None
    capability: SavedBuildCapabilityAudit | None
    assignments: tuple[ProviderAssignment, ...] = ()


@dataclass(frozen=True)
class CandidateRanking:
    comparisons: tuple[BuildCandidateComparison, ...]
    ranked: tuple[BuildCandidateComparison, ...]

    @property
    def recommended(self) -> BuildCandidateComparison | None:
        for comparison in self.ranked:
            if comparison.is_preferred:
                return comparison
        return None

    @property
    def recommended_ties(self) -> tuple[BuildCandidateComparison, ...]:
        """Return every preferred candidate equivalent to the stable first choice.

        ``recommended`` remains deterministic for callers that require exactly one
        object. This property prevents that deterministic identifier tie-break from
        being presented as stronger ESO evidence when multiple candidates have the
        same modeled objective and preference class.
        """

        recommended = self.recommended
        if recommended is None or recommended.delta is None:
            return ()
        return tuple(
            comparison
            for comparison in self.ranked
            if comparison.is_preferred
            and comparison.delta is not None
            and comparison.is_constraint_repair is recommended.is_constraint_repair
            and comparison.is_improvement is recommended.is_improvement
            and isclose(
                float(comparison.delta),
                float(recommended.delta),
                rel_tol=0.0,
                abs_tol=1e-9,
            )
        )


def _dedupe(messages: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(message) for message in messages if str(message).strip()))


def evaluate_healing_candidate(
    *,
    candidate: BuildCandidate,
    baseline_build: PlayerBuild,
    baseline_healing: ModeledHealingPotency,
    baseline_capability: SavedBuildCapabilityAudit,
    baseline_assignments: tuple[ProviderAssignment, ...] | None,
    member_id: str,
    healing_skill_names: tuple[str, ...],
    tooltip_service: SavedBuildSkillTooltipService,
    capability_service: SavedBuildCapabilityService,
    resolve_context: ContextResolver,
    resolve_sustain: SustainResolver,
    resolve_assignments: AssignmentResolver | None,
    resolve_objective_coverage: ObjectiveCoverageResolver | None = None,
) -> HealingCandidateEvaluation:
    """Coordinate authoritative objective and hard-constraint evaluators.

    Provider responsibilities are checked only when an encounter assignment scope
    is supplied. Objective coverage may add explicit unresolved evidence for
    dimensions the selected objective metric does not yet model.
    """

    if not candidate.is_evaluable:
        reason = f"Candidate is not evaluable: {candidate.evaluation_state.value}"
        unresolved = candidate.unresolved or (reason,)
        comparison = BuildCandidateComparison(
            candidate=candidate,
            objective=EvaluationObjective.HEALING,
            baseline_value=baseline_healing.value if baseline_healing.resolved else None,
            candidate_value=None,
            constraints=(),
            unresolved=_dedupe(tuple(unresolved)),
            rejection_reason=reason,
        )
        return HealingCandidateEvaluation(comparison, None, None, None)

    candidate_context = resolve_context(candidate)
    candidate_build = candidate.candidate_build
    objective_coverage_unresolved = (
        resolve_objective_coverage(candidate) if resolve_objective_coverage is not None else ()
    )

    if candidate_context.context is None:
        healing = None
        healing_messages = candidate_context.unresolved or ("Candidate calculation context is unavailable",)
    else:
        healing = measure_modeled_healing_potency(
            build=candidate_build,
            context=candidate_context.context,
            skill_names=healing_skill_names,
            tooltip_service=tooltip_service,
        )
        healing_messages = healing.unresolved

    sustain = resolve_sustain(candidate_context)
    capability = capability_service.audit_build(candidate_build)
    capability_constraint = compare_capability_coverage(baseline_capability, capability)

    assignments: tuple[ProviderAssignment, ...] = ()
    constraints = [sustain.constraint, capability_constraint]
    if baseline_assignments is not None and resolve_assignments is not None:
        assignments = resolve_assignments(candidate_build)
        constraints.append(
            compare_provider_responsibilities(
                member_id=member_id,
                baseline_assignments=baseline_assignments,
                candidate_assignments=assignments,
            )
        )

    unresolved = _dedupe(
        tuple(baseline_healing.unresolved)
        + tuple(healing_messages)
        + tuple(sustain.unresolved)
        + tuple(objective_coverage_unresolved)
    )

    evidence: list[str] = []
    evidence.extend(f"baseline: {row}" for row in baseline_healing.evidence)
    if healing is not None:
        evidence.extend(f"candidate: {row}" for row in healing.evidence)

    comparison = BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.HEALING,
        baseline_value=baseline_healing.value if baseline_healing.resolved else None,
        candidate_value=healing.value if healing is not None and healing.resolved else None,
        constraints=tuple(constraints),
        evidence=tuple(evidence),
        unresolved=unresolved,
    )
    return HealingCandidateEvaluation(
        comparison=comparison,
        healing=healing,
        sustain=sustain,
        capability=capability,
        assignments=assignments,
    )


def rank_candidate_comparisons(
    comparisons: tuple[BuildCandidateComparison, ...],
) -> CandidateRanking:
    rankable = tuple(comparison for comparison in comparisons if comparison.is_rankable)
    ranked = tuple(
        sorted(
            rankable,
            key=lambda comparison: (
                -float(comparison.delta or 0.0),
                comparison.candidate.candidate_id.casefold(),
                comparison.candidate.candidate_id,
            ),
        )
    )
    return CandidateRanking(comparisons=tuple(comparisons), ranked=ranked)
