from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationPlan
from minmax.rotation_wait_decision import PrematureRecastDecisionProvider
from minmax.runtime_healer_wait_decision_provider import RecoveryHeavyPressureResolver
from services.rotation_candidate_generation_service import (
    RotationCandidateGenerationService,
    RotationRefreshLeadCandidateOption,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryCandidateEvaluator,
    RecoveryHeavyCandidateOrchestrationInput,
)


RecoveryPressureWaitDecisionFactory = Callable[
    [str, RecoveryHeavyPressureResolver | None],
    PrematureRecastDecisionProvider | None,
]
RecoveryCandidateEvaluatorResolver = Callable[
    [str],
    RecoveryCandidateEvaluator,
]


@dataclass(frozen=True)
class RotationRecoveryHeavyCandidateGenerationBridgeResult:
    """Canonical recovery inputs derived from one generated candidate family."""

    candidates: tuple[RecoveryHeavyCandidateOrchestrationInput, ...]


class RotationRecoveryHeavyCandidateGenerationBridgeService:
    """Convert refresh-lead candidate policies into recovery-aware generators.

    The ordinary candidate generator owns deterministic schedule policy. Recovery
    stabilization owns resource-pressure iteration. This bridge joins the two without
    teaching either layer the other's semantics.

    Each recovery candidate regenerates only its own policy through
    ``RotationCandidateGenerationService.generate_policy``. A caller-supplied
    pressure-aware wait-decision factory may build a fresh provider for each
    regeneration, preventing runtime state from leaking across candidates or fixed-
    point iterations.

    Candidate judgment remains explicit through ``evaluator_resolver``. No scorecard,
    encounter obligation, effect target, recovery threshold, restore amount, or role
    convention is inferred here.
    """

    def __init__(
        self,
        generation_service: RotationCandidateGenerationService | None = None,
    ) -> None:
        self.generation_service = generation_service or RotationCandidateGenerationService()

    def build(
        self,
        *,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        evaluator_resolver: RecoveryCandidateEvaluatorResolver,
        demands: tuple[RotationDemandWindow, ...] = (),
        options: tuple[RotationRefreshLeadCandidateOption, ...] = (),
        wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None,
        baseline_id: str = "baseline",
    ) -> RotationRecoveryHeavyCandidateGenerationBridgeResult:
        baseline = str(baseline_id or "").strip()
        if not baseline:
            raise ValueError("recovery candidate generation baseline_id is required")

        normalized_options = self.generation_service._dedupe_options(tuple(options))
        candidate_ids = [baseline]
        refresh_by_id = {baseline.casefold(): ()}
        seen = {baseline.casefold()}

        for option in normalized_options:
            key = option.option_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate recovery candidate generation id: {option.option_id!r}"
                )
            seen.add(key)
            candidate_ids.append(option.option_id)
            refresh_by_id[key] = option.refresh_leads

        if len(candidate_ids) > self.generation_service.max_candidates:
            raise ValueError(
                "recovery candidate family exceeds explicit limit: "
                f"{len(candidate_ids)} > {self.generation_service.max_candidates}"
            )

        candidates: list[RecoveryHeavyCandidateOrchestrationInput] = []
        for candidate_id in candidate_ids:
            key = candidate_id.casefold()
            refresh_leads = refresh_by_id[key]
            evaluator = evaluator_resolver(candidate_id)

            def generate(
                pressure: RecoveryHeavyPressureResolver | None,
                *,
                _candidate_id: str = candidate_id,
                _refresh_leads=refresh_leads,
            ) -> RotationPlan:
                provider_factory = None
                if wait_decision_factory is not None:
                    provider_factory = lambda: wait_decision_factory(_candidate_id, pressure)
                generated = self.generation_service.generate_policy(
                    candidate_id=_candidate_id,
                    seed_plan=seed_plan,
                    priorities=priorities,
                    demands=tuple(demands),
                    refresh_leads=tuple(_refresh_leads),
                    wait_decision_factory=provider_factory,
                )
                if generated.candidate_id.casefold() != _candidate_id.casefold():
                    raise ValueError(
                        "recovery candidate generation changed candidate_id: "
                        f"expected {_candidate_id!r}, got {generated.candidate_id!r}"
                    )
                return generated.plan

            candidates.append(
                RecoveryHeavyCandidateOrchestrationInput(
                    candidate_id=candidate_id,
                    generate=generate,
                    evaluate_candidate=evaluator,
                )
            )

        return RotationRecoveryHeavyCandidateGenerationBridgeResult(
            candidates=tuple(candidates)
        )


__all__ = [
    "RecoveryCandidateEvaluatorResolver",
    "RecoveryPressureWaitDecisionFactory",
    "RotationRecoveryHeavyCandidateGenerationBridgeResult",
    "RotationRecoveryHeavyCandidateGenerationBridgeService",
]
