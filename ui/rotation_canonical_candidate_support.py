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
from services.canonical_knowledge_gap import CanonicalKnowledgeGap
from services.canonical_mechanics_coverage_audit import CanonicalMechanicsCoverageReport
from services.rotation_candidate_generation_service import RotationRefreshLeadCandidateOption
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_mechanics_dependency_service import (
    RotationMechanicsDependency,
    RotationMechanicsDependencyService,
)
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
from services.rotation_static_build_context_service import (
    RotationStaticBuildContextResolution,
    RotationStaticBuildContextService,
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
    adapted, when optional canonical static build context is unresolved, or when
    decision-critical mechanics coverage is unresolved. Discovered mechanics
    dependencies and research gaps are retained for explanation.
    """

    build_adaptation: SavedBuildAdaptation
    pipeline_result: RotationRecoveryHeavyCandidateOrchestrationResult | None
    validation: RotationRecoveryValidationEvidence
    mechanics_dependencies: tuple[RotationMechanicsDependency, ...] = ()
    knowledge_gaps: tuple[CanonicalKnowledgeGap, ...] = ()
    static_context: RotationStaticBuildContextResolution | None = None
    canonical_maximum_amount: int | None = None


class RotationCanonicalCandidateSupport:
    """Bridge a saved UI build into the effect-aware recovery candidate pipeline.

    Saved ``PlayerBuild`` state is first adapted through the canonical
    SavedBuildCharacterAdapter. A caller may also supply ``static_context_service``
    to require the existing MinMax static calculation pipeline, including verified
    armor/passive ownership and ranks, to resolve cleanly before candidate ranking.

    When static context is enabled, a single global recovery-resource ceiling is
    accepted only when every resolved bar has the same canonical maximum. The
    canonical value then replaces the caller's provisional maximum. If front/back
    maxima differ, the current one-ceiling sustain model fails closed rather than
    pretending either bar is globally authoritative.

    When a mechanics coverage report is supplied, the resolved CharacterBuild and
    current rotation evidence are used to discover which coverage domains actually
    matter to this decision. Unrelated global gaps do not block the candidate.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        build_adapter: SavedBuildCharacterAdapter | None = None,
        pipeline: RotationRecoveryHeavyCandidatePipelineService | None = None,
        validation_support: RotationRecoveryValidationSupport | None = None,
        dependency_service: RotationMechanicsDependencyService | None = None,
        static_context_service: RotationStaticBuildContextService | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(database)
        self.pipeline = pipeline or RotationRecoveryHeavyCandidatePipelineService()
        self.validation_support = validation_support or RotationRecoveryValidationSupport()
        self.dependency_service = dependency_service or RotationMechanicsDependencyService()
        self.static_context_service = static_context_service

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
        coverage_report: CanonicalMechanicsCoverageReport | None = None,
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
        dependencies: tuple[RotationMechanicsDependency, ...] = ()
        knowledge_gaps: tuple[CanonicalKnowledgeGap, ...] = ()
        static_context: RotationStaticBuildContextResolution | None = None
        effective_maximum_amount = int(maximum_amount)
        canonical_maximum_amount: int | None = None

        if self.static_context_service is not None:
            static_context = self.static_context_service.resolve(player_build)
            if not static_context.resolved:
                reasons = [
                    "canonical candidate evaluation was not run because static build "
                    "calculation evidence is unresolved"
                ]
                reasons.extend(
                    f"static build context: {item}"
                    for item in static_context.unresolved
                    if str(item).strip()
                )
                return RotationCanonicalCandidateApplicationResult(
                    build_adaptation=adaptation,
                    pipeline_result=None,
                    validation=RotationRecoveryValidationEvidence(
                        scope=RotationRecoveryValidationScope.NOT_EVALUATED,
                        selectable=None,
                        reasons=tuple(reasons),
                    ),
                    static_context=static_context,
                )

            canonical_maximum_amount = static_context.uniform_maximum_amount_for(resource)
            if canonical_maximum_amount is None:
                by_bar = static_context.maximum_amounts_for(resource)
                detail = ", ".join(f"{bar}={amount}" for bar, amount in by_bar)
                return RotationCanonicalCandidateApplicationResult(
                    build_adaptation=adaptation,
                    pipeline_result=None,
                    validation=RotationRecoveryValidationEvidence(
                        scope=RotationRecoveryValidationScope.NOT_EVALUATED,
                        selectable=None,
                        reasons=(
                            "canonical candidate evaluation was not run because the current "
                            "recovery model accepts one maximum resource amount but canonical "
                            f"static state is bar-sensitive for {resource.value}: {detail}",
                        ),
                    ),
                    static_context=static_context,
                )
            effective_maximum_amount = canonical_maximum_amount

        if coverage_report is not None:
            dependencies = self.dependency_service.discover(
                character_build=adaptation.build,
                demands=demand_tuple,
                requirements=requirement_tuple,
                passives=passive_tuple,
                recovery_enabled=True,
            )
            dependency_keys = self.dependency_service.keys(dependencies)
            knowledge_gaps = coverage_report.dependency_gaps_for(
                "rotation_maker",
                dependency_keys,
            )
            blocking = tuple(gap for gap in knowledge_gaps if gap.blocking)
            if blocking:
                reasons = [
                    "canonical candidate evaluation was not run because required "
                    "mechanics coverage is unresolved"
                ]
                for gap in blocking:
                    evidence = self._dependency_evidence_for(gap.key, dependencies)
                    detail = (
                        f"mechanics coverage: {gap.summary} Bring back: {gap.needed_evidence}"
                    )
                    if evidence:
                        detail += " Relevant build evidence: " + ", ".join(evidence)
                    reasons.append(detail)
                return RotationCanonicalCandidateApplicationResult(
                    build_adaptation=adaptation,
                    pipeline_result=None,
                    validation=RotationRecoveryValidationEvidence(
                        scope=RotationRecoveryValidationScope.NOT_EVALUATED,
                        selectable=None,
                        reasons=tuple(reasons),
                    ),
                    mechanics_dependencies=dependencies,
                    knowledge_gaps=knowledge_gaps,
                    static_context=static_context,
                    canonical_maximum_amount=canonical_maximum_amount,
                )

        result = self.pipeline.run_effects(
            player_build=player_build,
            character_build=adaptation.build,
            seed_plan=seed_plan,
            priorities=priorities,
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=scorecard_resolver,
            resource=resource,
            maximum_amount=effective_maximum_amount,
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
            mechanics_dependencies=dependencies,
            knowledge_gaps=knowledge_gaps,
            static_context=static_context,
            canonical_maximum_amount=canonical_maximum_amount,
        )

    @staticmethod
    def _dependency_evidence_for(
        gap_key: str,
        dependencies: tuple[RotationMechanicsDependency, ...],
    ) -> tuple[str, ...]:
        wanted = str(gap_key or "").strip().casefold()
        if not wanted:
            return ()
        for dependency in dependencies:
            key = str(getattr(dependency, "key", dependency) or "").strip().casefold()
            if key != wanted:
                continue
            return tuple(
                str(item).strip()
                for item in getattr(dependency, "evidence", ())
                if str(item).strip()
            )
        return ()


__all__ = [
    "RotationCanonicalCandidateApplicationResult",
    "RotationCanonicalCandidateSupport",
]
