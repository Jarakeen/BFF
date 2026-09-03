from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from models.build_model import PlayerBuild

from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_capability import (
    compare_capability_coverage,
    compare_provider_responsibilities,
)
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.build_candidate_context import BuildCandidateContextResult
from minmax.build_candidate_healing import (
    ModeledHealingPotency,
    measure_modeled_healing_potency,
)
from minmax.build_candidate_sustain import BuildCandidateSustainComparison
from minmax.evaluation_objective import EvaluationObjective
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from services.encounter_provider_assignment import ProviderAssignment
from services.saved_build_capability_service import (
    SavedBuildCapabilityAudit,
    SavedBuildCapabilityService,
)


ContextResolver = Callable[[BuildCandidate], BuildCandidateContextResult]
SustainResolver = Callable[[BuildCandidateContextResult], BuildCandidateSustainComparison]
AssignmentResolver = Callable[[PlayerBuild], tuple[ProviderAssignment, ...]]


@dataclass(frozen=True)
class HealingCandidateEvaluation:
    """Authoritative Phase 12 evidence collected for one healing candidate."""

    comparison: BuildCandidateComparison
    healing: ModeledHealingPotency | None
    sustain: BuildCandidateSustainComparison | None
    capability: SavedBuildCapabilityAudit | None
    assignments: tuple[ProviderAssignment, ...] = ()


@dataclass(frozen=True)
class CandidateRanking:
    """Deterministic ranking over only candidates proven safe to compare."""

    comparisons: tuple[BuildCandidateComparison, ...]
    ranked: tuple[BuildCandidateComparison, ...]

    @property
    def recommended(self) -> BuildCandidateComparison | None:
        for comparison in self.ranked:
            if comparison.is_improvement:
                return comparison
        return None


def _dedupe(messages: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(message) for message in messages if str(message).strip()))


def _unknown_constraint(name: str, explanation: str) -> CandidateConstraint:
    return CandidateConstraint(
        name=name,
        status=ConstraintStatus.UNKNOWN,
        explanation=explanation,
    )


def evaluate_healing_candidate(
    *,
    candidate: BuildCandidate,
    baseline_build: PlayerBuild,
    baseline_healing: ModeledHealingPotency,
    baseline_capability: SavedBuildCapabilityAudit,
    baseline_assignments: tuple[ProviderAssignment, ...],
    member_id: str,
    healing_skill_names: tuple[str, ...],
    tooltip_service: SavedBuildSkillTooltipService,
    capability_service: SavedBuildCapabilityService,
    resolve_context: ContextResolver,
    resolve_sustain: SustainResolver,
    resolve_assignments: AssignmentResolver,
) -> HealingCandidateEvaluation:
    """Evaluate one candidate without duplicating combat, sustain, or provider math.

    Phase 12 coordinates existing authoritative engines. Context construction,
    healing coefficient math, Phase 4 sustain, Phase 10 capability resolution,
    and Phase 11 provider assignment remain owned by their existing services.
    A candidate that cannot prove its objective or every hard constraint remains
    unrankable.

    ``BuildCalculationContext`` may contain diagnostics for stat/mechanic channels
    unrelated to the current objective or hard constraints. Those raw context
    diagnostics are not promoted into a universal Phase 12 veto. Each consuming
    evaluator is responsible for returning the unresolved evidence relevant to
    the channel it actually evaluates.
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
        return HealingCandidateEvaluation(
            comparison=comparison,
            healing=None,
            sustain=None,
            capability=None,
        )

    candidate_context = resolve_context(candidate)
    candidate_build = candidate.candidate_build

    if candidate_context.context is None:
        healing = None
        healing_constraint_messages = candidate_context.unresolved or (
            "Candidate calculation context is unavailable",
        )
    else:
        healing = measure_modeled_healing_potency(
            build=candidate_build,
            context=candidate_context.context,
            skill_names=healing_skill_names,
            tooltip_service=tooltip_service,
        )
        healing_constraint_messages = healing.unresolved

    sustain = resolve_sustain(candidate_context)
    capability = capability_service.audit_build(candidate_build)
    assignments = resolve_assignments(candidate_build)

    capability_constraint = compare_capability_coverage(
        baseline_capability,
        capability,
    )
    responsibility_constraint = compare_provider_responsibilities(
        member_id=member_id,
        baseline_assignments=baseline_assignments,
        candidate_assignments=assignments,
    )

    constraints = (
        sustain.constraint,
        capability_constraint,
        responsibility_constraint,
    )
    unresolved = _dedupe(
        tuple(baseline_healing.unresolved)
        + tuple(healing_constraint_messages)
        + tuple(sustain.unresolved)
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
        constraints=constraints,
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
    """Rank only proven-comparable candidates by objective delta, deterministically."""

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
    return CandidateRanking(
        comparisons=tuple(comparisons),
        ranked=ranked,
    )
