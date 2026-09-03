from __future__ import annotations

from dataclasses import dataclass

from models.build_model import PlayerBuild

from .build_action_cost_modifiers import BuildActionCostModifierResolver
from .build_calculation_context import BuildCalculationContext
from .build_candidate_comparison import CandidateConstraint, ConstraintStatus
from .build_candidate_context import BuildCandidateContextResult
from .build_sustain import BuildSustainRun, PlannedBuildAction, evaluate_build_sustain
from .build_sustain_relevance import sustain_relevant_context_unresolved
from .conditional_recovery import TimedRecoveryModifier
from .recovery_timing import RecoveryActivityResolver
from .resource_costs import ResourceType
from .restoration_events import ResourceRestorationEvent


@dataclass(frozen=True)
class BuildCandidateSustainComparison:
    """Phase 12 baseline-vs-candidate result from the authoritative Phase 4 runner."""

    baseline_run: BuildSustainRun | None
    candidate_run: BuildSustainRun | None
    constraint: CandidateConstraint
    unresolved: tuple[str, ...] = ()


def compare_sustain_runs(
    *,
    resource: ResourceType,
    baseline_run: BuildSustainRun,
    candidate_run: BuildSustainRun,
) -> CandidateConstraint:
    """Translate Phase 4 sustain evidence into one hard candidate constraint."""

    unresolved = tuple(baseline_run.unresolved) + tuple(candidate_run.unresolved)
    if unresolved:
        return CandidateConstraint(
            name=f"{resource.value} sustain",
            status=ConstraintStatus.UNKNOWN,
            explanation=(
                "Sustain comparison is unresolved: " + "; ".join(unresolved)
            ),
        )

    baseline = baseline_run.sustain
    candidate = candidate_run.sustain

    if not candidate.sustains:
        failure = candidate.first_failure
        detail = (
            f"first shortfall {failure.shortfall} at {failure.time_seconds:g}s from {failure.source}"
            if failure is not None
            else "candidate resource timeline does not sustain"
        )
        return CandidateConstraint(
            name=f"{resource.value} sustain",
            status=ConstraintStatus.WORSENED,
            explanation=f"Candidate fails {resource.value} sustain: {detail}.",
        )

    if not baseline.sustains:
        return CandidateConstraint(
            name=f"{resource.value} sustain",
            status=ConstraintStatus.IMPROVED,
            explanation=(
                f"Candidate sustains {resource.value}; baseline does not. "
                f"Candidate minimum={candidate.minimum_amount}, ending={candidate.ending_margin}."
            ),
        )

    improved_margin = (
        candidate.minimum_amount >= baseline.minimum_amount
        and candidate.ending_margin >= baseline.ending_margin
        and (
            candidate.minimum_amount > baseline.minimum_amount
            or candidate.ending_margin > baseline.ending_margin
        )
    )
    status = ConstraintStatus.IMPROVED if improved_margin else ConstraintStatus.PRESERVED
    return CandidateConstraint(
        name=f"{resource.value} sustain",
        status=status,
        explanation=(
            f"Baseline sustains with minimum={baseline.minimum_amount}, ending={baseline.ending_margin}; "
            f"candidate sustains with minimum={candidate.minimum_amount}, ending={candidate.ending_margin}."
        ),
    )


def evaluate_candidate_sustain(
    *,
    baseline_build: PlayerBuild,
    baseline_context: BuildCalculationContext,
    candidate_context: BuildCandidateContextResult,
    resource: ResourceType,
    duration_seconds: float,
    actions: tuple[PlannedBuildAction, ...],
    cost_modifier_resolver: BuildActionCostModifierResolver,
    restoration_events: tuple[ResourceRestorationEvent, ...] = (),
    recovery_modifiers: tuple[TimedRecoveryModifier, ...] = (),
    activity_at: RecoveryActivityResolver | None = None,
    starting_amount: int | None = None,
    first_recovery_tick_seconds: float = 2.0,
) -> BuildCandidateSustainComparison:
    """Run baseline and candidate through the existing Phase 4 sustain pipeline.

    Phase 12 supplies orchestration only. Static resource state, action costs,
    cost modifiers, recovery timing, restoration events, and timeline semantics
    remain owned by the existing Phase 4 implementation. Shared-context
    diagnostics are filtered only through the explicit Phase 4 relevance rules;
    unrelated stat-channel gaps do not become sustain failures.
    """

    if candidate_context.context is None:
        evidence = candidate_context.unresolved or (
            "Candidate calculation context is unavailable",
        )
        return BuildCandidateSustainComparison(
            baseline_run=None,
            candidate_run=None,
            constraint=CandidateConstraint(
                name=f"{resource.value} sustain",
                status=ConstraintStatus.UNKNOWN,
                explanation="Sustain comparison is unresolved: " + "; ".join(evidence),
            ),
            unresolved=tuple(evidence),
        )

    candidate_build = candidate_context.candidate.candidate_build
    context_unresolved = (
        sustain_relevant_context_unresolved(
            baseline_build,
            tuple(baseline_context.unresolved_gear_effects),
        )
        + sustain_relevant_context_unresolved(
            candidate_build,
            tuple(candidate_context.unresolved),
        )
    )
    if context_unresolved:
        return BuildCandidateSustainComparison(
            baseline_run=None,
            candidate_run=None,
            constraint=CandidateConstraint(
                name=f"{resource.value} sustain",
                status=ConstraintStatus.UNKNOWN,
                explanation="Sustain comparison is unresolved: " + "; ".join(context_unresolved),
            ),
            unresolved=context_unresolved,
        )

    baseline_run = evaluate_build_sustain(
        build=baseline_build,
        context=baseline_context,
        resource=resource,
        duration_seconds=duration_seconds,
        actions=actions,
        cost_modifier_resolver=cost_modifier_resolver,
        restoration_events=restoration_events,
        recovery_modifiers=recovery_modifiers,
        activity_at=activity_at,
        starting_amount=starting_amount,
        first_recovery_tick_seconds=first_recovery_tick_seconds,
    )
    candidate_run = evaluate_build_sustain(
        build=candidate_build,
        context=candidate_context.context,
        resource=resource,
        duration_seconds=duration_seconds,
        actions=actions,
        cost_modifier_resolver=cost_modifier_resolver,
        restoration_events=restoration_events,
        recovery_modifiers=recovery_modifiers,
        activity_at=activity_at,
        starting_amount=starting_amount,
        first_recovery_tick_seconds=first_recovery_tick_seconds,
    )

    run_unresolved = tuple(baseline_run.unresolved) + tuple(candidate_run.unresolved)
    return BuildCandidateSustainComparison(
        baseline_run=baseline_run,
        candidate_run=candidate_run,
        constraint=compare_sustain_runs(
            resource=resource,
            baseline_run=baseline_run,
            candidate_run=candidate_run,
        ),
        unresolved=run_unresolved,
    )
