from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from minmax.build_calculation_context import BuildCalculationContext
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateResult,
)
from services.rotation_recovery_heavy_candidate_selection_service import (
    RecoveryFinalCandidateEvaluation,
    RecoveryStabilizedCandidateInput,
    RecoveryStabilizedCandidateSelectionResult,
    RotationRecoveryHeavyCandidateSelectionService,
)
from services.rotation_recovery_heavy_candidate_stabilization_service import (
    RecoveryCandidateEvaluator,
    RecoveryCandidateEvaluationResult,
    RotationRecoveryHeavyCandidateStabilizationService,
)
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    RotationRecoveryHeavyReplay,
    VerifiedRecoveryHeavyRestorationResolver,
)
from services.rotation_recovery_heavy_stabilization_service import (
    RecoveryAwareRotationGenerator,
    RecoveryDisplayedRecoveryResolverFactory,
    RecoveryMaximumEventResolver,
    RecoveryRestorationResolverFactory,
    RotationRecoveryHeavyStabilizationResult,
)


RecoveryRuntimeCombatStateResolver = Callable[
    [float, int | None],
    RotationPlanRuntimeCombatStateResult,
]
RecoveryRuntimeCombatStateResolverFactory = Callable[
    [RotationPlan],
    RecoveryRuntimeCombatStateResolver,
]
RecoveryRuntimeActivationAnchorResolver = Callable[..., float | None]
RecoveryRuntimeActivationAnchorResolverFactory = Callable[
    [RotationPlan],
    RecoveryRuntimeActivationAnchorResolver,
]


@dataclass(frozen=True)
class RecoveryHeavyCandidateOrchestrationInput:
    """One candidate policy that can regenerate under recovery pressure."""

    candidate_id: str
    generate: RecoveryAwareRotationGenerator
    evaluate_candidate: RecoveryCandidateEvaluator

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("recovery orchestration candidate_id must be non-empty")
        object.__setattr__(self, "candidate_id", candidate_id)


@dataclass(frozen=True)
class RecoveryHeavyStabilizedCandidateSnapshot:
    """Final stabilized execution evidence supplied to family-level ranking.

    Runtime resolvers are bound only after the candidate plan reaches its final
    stabilized form. Family-level scorecards and role-output evaluators may therefore
    query exact runtime state or activation anchors without consulting the seed
    schedule or rebuilding timing evidence independently.
    """

    candidate_id: str
    plan: RotationPlan
    replay: RotationRecoveryHeavyReplay
    stabilization: RotationRecoveryHeavyStabilizationResult
    runtime_combat_state_resolver: RecoveryRuntimeCombatStateResolver | None = None
    runtime_activation_anchor_resolver: RecoveryRuntimeActivationAnchorResolver | None = None


RecoveryFinalFamilyEvaluator = Callable[
    [tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...]],
    tuple[RecoveryFinalCandidateEvaluation, ...],
]


@dataclass(frozen=True)
class RotationRecoveryHeavyCandidateOrchestrationResult:
    stabilized_candidates: tuple[RecoveryHeavyStabilizedCandidateSnapshot, ...]
    ranked_candidates: tuple[RecoveryStabilizedCandidateSelectionResult, ...]
    selected_candidate: RecoveryStabilizedCandidateSelectionResult | None


class RotationRecoveryHeavyCandidateOrchestrationService:
    """Run candidate recovery stabilization, final family ranking, and selection."""

    def __init__(
        self,
        *,
        stabilization_service: RotationRecoveryHeavyCandidateStabilizationService | None = None,
        selection_service: RotationRecoveryHeavyCandidateSelectionService | None = None,
    ) -> None:
        self.stabilization_service = (
            stabilization_service or RotationRecoveryHeavyCandidateStabilizationService()
        )
        self.selection_service = (
            selection_service or RotationRecoveryHeavyCandidateSelectionService()
        )

    def orchestrate(
        self,
        *,
        build: PlayerBuild,
        candidates: tuple[RecoveryHeavyCandidateOrchestrationInput, ...],
        evaluate_final_family: RecoveryFinalFamilyEvaluator,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None,
        restoration_resolver_factory: RecoveryRestorationResolverFactory | None = None,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
        calculation_context: BuildCalculationContext | None = None,
        maximum_event_resolver: RecoveryMaximumEventResolver | None = None,
        displayed_recovery_resolver_factory: RecoveryDisplayedRecoveryResolverFactory | None = None,
        runtime_combat_state_resolver_factory: RecoveryRuntimeCombatStateResolverFactory | None = None,
        runtime_activation_anchor_resolver_factory: RecoveryRuntimeActivationAnchorResolverFactory | None = None,
    ) -> RotationRecoveryHeavyCandidateOrchestrationResult:
        if not candidates:
            return RotationRecoveryHeavyCandidateOrchestrationResult(
                stabilized_candidates=(),
                ranked_candidates=(),
                selected_candidate=None,
            )

        expected_ids: dict[str, str] = {}
        for candidate in candidates:
            key = candidate.candidate_id.casefold()
            if key in expected_ids:
                raise ValueError(
                    f"duplicate recovery orchestration candidate_id: {candidate.candidate_id!r}"
                )
            expected_ids[key] = candidate.candidate_id

        stabilized: list[RecoveryHeavyStabilizedCandidateSnapshot] = []
        for candidate in candidates:
            expected_key = candidate.candidate_id.casefold()

            def evaluate_current(
                plan: RotationPlan,
                replay: RotationRecoveryHeavyReplay,
                *,
                _candidate: RecoveryHeavyCandidateOrchestrationInput = candidate,
                _expected_key: str = expected_key,
            ) -> RecoveryCandidateEvaluationResult:
                result = _candidate.evaluate_candidate(plan, replay)
                actual_id = str(result.candidate_id or "").strip()
                if actual_id.casefold() != _expected_key:
                    raise ValueError(
                        "recovery iteration evaluation candidate_id mismatch: "
                        f"expected {_candidate.candidate_id!r}, got {actual_id!r}"
                    )
                return result

            stabilization_kwargs = dict(
                build=build,
                generate=candidate.generate,
                evaluate_candidate=evaluate_current,
                resource=resource,
                maximum_amount=maximum_amount,
                trigger_fraction=trigger_fraction,
                reserve_assessment_resolver=reserve_assessment_resolver,
                max_iterations=max_iterations,
                calculation_context=calculation_context,
                maximum_event_resolver=maximum_event_resolver,
                displayed_recovery_resolver_factory=displayed_recovery_resolver_factory,
            )
            if restoration_resolver_factory is not None:
                stabilization_kwargs["restoration_resolver_factory"] = (
                    restoration_resolver_factory
                )
            if restoration_resolver is not None:
                stabilization_kwargs["restoration_resolver"] = restoration_resolver

            stabilization = self.stabilization_service.stabilize(
                **stabilization_kwargs,
            )
            runtime_resolver = (
                None
                if runtime_combat_state_resolver_factory is None
                else runtime_combat_state_resolver_factory(stabilization.plan)
            )
            activation_anchor_resolver = (
                None
                if runtime_activation_anchor_resolver_factory is None
                else runtime_activation_anchor_resolver_factory(stabilization.plan)
            )
            stabilized.append(
                RecoveryHeavyStabilizedCandidateSnapshot(
                    candidate_id=candidate.candidate_id,
                    plan=stabilization.plan,
                    replay=stabilization.replay,
                    stabilization=stabilization,
                    runtime_combat_state_resolver=runtime_resolver,
                    runtime_activation_anchor_resolver=activation_anchor_resolver,
                )
            )

        snapshots = tuple(stabilized)
        evaluations = tuple(evaluate_final_family(snapshots))
        evaluation_by_id = self._validate_final_family(
            expected_ids=expected_ids,
            evaluations=evaluations,
        )

        joined = tuple(
            RecoveryStabilizedCandidateInput(
                evaluation=evaluation_by_id[item.candidate_id.casefold()],
                stabilization=item.stabilization,
            )
            for item in snapshots
        )
        ranked = self.selection_service.rank(joined)
        selected = next((item for item in ranked if item.selectable), None)
        return RotationRecoveryHeavyCandidateOrchestrationResult(
            stabilized_candidates=snapshots,
            ranked_candidates=tuple(ranked),
            selected_candidate=selected,
        )

    @staticmethod
    def _validate_final_family(
        *,
        expected_ids: dict[str, str],
        evaluations: tuple[RecoveryFinalCandidateEvaluation, ...],
    ) -> dict[str, RecoveryFinalCandidateEvaluation]:
        resolved: dict[str, RecoveryFinalCandidateEvaluation] = {}
        for evaluation in evaluations:
            candidate_id = str(evaluation.candidate_id or "").strip()
            if not candidate_id:
                raise ValueError("final recovery family evaluation candidate_id is empty")
            key = candidate_id.casefold()
            if key in resolved:
                raise ValueError(
                    f"duplicate final recovery family candidate_id: {candidate_id!r}"
                )
            resolved[key] = evaluation

        missing = sorted(expected_ids[key] for key in expected_ids.keys() - resolved.keys())
        unexpected = sorted(
            str(resolved[key].candidate_id) for key in resolved.keys() - expected_ids.keys()
        )
        if missing or unexpected:
            details: list[str] = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected: " + ", ".join(unexpected))
            raise ValueError(
                "final recovery family evaluation candidate set mismatch: " + "; ".join(details)
            )
        return resolved


__all__ = [
    "RecoveryFinalFamilyEvaluator",
    "RecoveryHeavyCandidateOrchestrationInput",
    "RecoveryHeavyStabilizedCandidateSnapshot",
    "RecoveryRuntimeActivationAnchorResolver",
    "RecoveryRuntimeActivationAnchorResolverFactory",
    "RecoveryRuntimeCombatStateResolver",
    "RecoveryRuntimeCombatStateResolverFactory",
    "RotationRecoveryHeavyCandidateOrchestrationResult",
    "RotationRecoveryHeavyCandidateOrchestrationService",
]
