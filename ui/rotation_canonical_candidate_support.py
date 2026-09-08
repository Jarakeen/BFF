from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.saved_build_adapter import (
    SavedBuildAdaptation,
    SavedBuildCharacterAdapter,
)
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_generation_service import RotationRefreshLeadCandidateOption
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_recovery_heavy_candidate_generation_bridge_service import (
    RecoveryCandidateEvaluatorResolver,
    RecoveryPressureWaitDecisionFactory,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RotationRecoveryHeavyCandidateOrchestrationResult,
)
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RecoveryFinalScorecardResolver,
)
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    VerifiedRecoveryHeavyRestorationResolver,
)
from ui.rotation_recovery_validation_support import (
    RotationRecoveryValidationEvidence,
    RotationRecoveryValidationScope,
    RotationRecoveryValidationSupport,
)


@dataclass(frozen=True)
class RotationCanonicalCandidateApplicationResult:
    """Application-facing result for one canonical recovery candidate family.

    ``pipeline_result`` is absent when the selected saved build could not be fully
    adapted into canonical mechanics. In that case validation remains explicitly
    NOT_EVALUATED instead of treating partial build evidence as a valid rotation.
    """

    build_adaptation: SavedBuildAdaptation
    pipeline_result: RotationRecoveryHeavyCandidateOrchestrationResult | None
    validation: RotationRecoveryValidationEvidence


class RotationCanonicalCandidateSupport:
    """Bridge a saved UI build into the effect-aware recovery candidate pipeline.

    This layer owns application plumbing only. Saved ``PlayerBuild`` state is adapted
    through the existing canonical SavedBuildCharacterAdapter, then the resolved
    ``CharacterBuild`` is supplied to the existing effect-aware candidate pipeline.

    Canonical candidate evaluation fails closed when the saved build adaptation has
    unresolved evidence. That prevents missing set, skill, passive, weapon, race,
    enchantment, or other canonical identity from silently disappearing before
    effective-duration and uptime evaluation.

    Encounter demands, refresh policies, recovery thresholds, restoration amounts,
    reserve policy, required effects, passives, candidate scorecards, and strategy
    semantics remain explicit caller-owned evidence.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        build_adapter: SavedBuildCharacterAdapter | None = None,
        pipeline: RotationRecoveryHeavyCandidatePipelineService | None = None,
        validation_support: RotationRecoveryValidationSupport | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(database)
        self.pipeline = pipeline or RotationRecoveryHeavyCandidatePipelineService()
        self.validation_support = validation_support or RotationRecoveryValidationSupport()

    def run_effects(
        self,
        *,
        player_build: PlayerBuild,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        evaluator_resolver: RecoveryCandidateEvaluatorResolver,
        scorecard_resolver: RecoveryFinalScorecardResolver,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver,
        demands: Iterable[RotationDemandWindow] = (),
        options: Iterable[RotationRefreshLeadCandidateOption] = (),
        wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None,
        requirements: Iterable[RotationEffectUptimeRequirement] = (),
        passives: Iterable[PassiveGrant] = (),
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
        baseline_id: str = "baseline",
        character_id: str | None = None,
    ) -> RotationCanonicalCandidateApplicationResult:
        adaptation = self.build_adapter.adapt(
            player_build,
            character_id=character_id,
        )
        unresolved = tuple(str(item).strip() for item in adaptation.unresolved if str(item).strip())
        if adaptation.build is None or unresolved:
            reasons = [
                "canonical candidate evaluation was not run because the saved build "
                "could not be fully resolved into canonical mechanics"
            ]
            reasons.extend(f"saved-build adaptation: {item}" for item in unresolved)
            if adaptation.build is None and not unresolved:
                reasons.append("saved-build adaptation returned no canonical CharacterBuild")
            return RotationCanonicalCandidateApplicationResult(
                build_adaptation=adaptation,
                pipeline_result=None,
                validation=RotationRecoveryValidationEvidence(
                    scope=RotationRecoveryValidationScope.NOT_EVALUATED,
                    selectable=None,
                    reasons=tuple(reasons),
                ),
            )

        demand_tuple = tuple(demands)
        option_tuple = tuple(options)
        requirement_tuple = tuple(requirements)
        passive_tuple = tuple(passives)
        result = self.pipeline.run_effects(
            player_build=player_build,
            character_build=adaptation.build,
            seed_plan=seed_plan,
            priorities=priorities,
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=scorecard_resolver,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            demands=demand_tuple,
            options=option_tuple,
            wait_decision_factory=wait_decision_factory,
            requirements=requirement_tuple,
            passives=passive_tuple,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
            baseline_id=baseline_id,
        )
        return RotationCanonicalCandidateApplicationResult(
            build_adaptation=adaptation,
            pipeline_result=result,
            validation=self.validation_support.from_candidate_pipeline_result(result),
        )


__all__ = [
    "RotationCanonicalCandidateApplicationResult",
    "RotationCanonicalCandidateSupport",
]
