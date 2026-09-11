from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.saved_build_adapter import (
    SavedBuildAdaptation,
    SavedBuildCharacterAdapter,
)
from minmax.combat_state import CombatState
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_action_cooldown import (
    RotationActionCooldownAssessment,
    RotationActionCooldownAssessor,
)
from minmax.rotation_action_occupancy import (
    RotationActionOccupancyAssessment,
    RotationActionOccupancyAssessor,
)
from minmax.rotation_action_range import (
    RotationActionRangeAssessment,
    RotationActionRangeAssessor,
    RotationTargetDistanceWindow,
)
from minmax.rotation_action_slot_legality import (
    RotationActionSlotAssessment,
    RotationActionSlotAssessor,
)
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.rotation_potion_cadence import RotationPotionCadenceRequirement
from models.build_model import PlayerBuild
from services.canonical_knowledge_gap import CanonicalKnowledgeGap
from services.canonical_mechanics_coverage_audit import CanonicalMechanicsCoverageReport
from services.rotation_candidate_generation_service import RotationRefreshLeadCandidateOption
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_mechanics_dependency_service import (
    RotationMechanicsDependency,
    RotationMechanicsDependencyService,
)
from services.rotation_potion_cadence_cooldown_bridge_service import (
    RotationPotionCadenceCooldownBridgeService,
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
from services.rotation_saved_build_action_range_service import (
    RotationSavedBuildActionRangeEvidence,
    RotationSavedBuildActionRangeService,
)
from services.rotation_saved_build_action_slot_service import (
    RotationSavedBuildActionSlotEvidence,
    RotationSavedBuildActionSlotService,
)
from services.rotation_saved_build_action_timing_service import (
    RotationSavedBuildActionTimingEvidence,
    RotationSavedBuildActionTimingService,
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
    """Application-facing result for one canonical recovery candidate family."""

    build_adaptation: SavedBuildAdaptation
    pipeline_result: RotationRecoveryHeavyCandidateOrchestrationResult | None
    validation: RotationRecoveryValidationEvidence
    mechanics_dependencies: tuple[RotationMechanicsDependency, ...] = ()
    knowledge_gaps: tuple[CanonicalKnowledgeGap, ...] = ()
    static_context: RotationStaticBuildContextResolution | None = None
    canonical_maximum_amount: int | None = None
    action_timing_evidence: RotationSavedBuildActionTimingEvidence = field(
        default_factory=RotationSavedBuildActionTimingEvidence
    )
    action_range_evidence: RotationSavedBuildActionRangeEvidence = field(
        default_factory=RotationSavedBuildActionRangeEvidence
    )
    action_slot_evidence: RotationSavedBuildActionSlotEvidence = field(
        default_factory=RotationSavedBuildActionSlotEvidence
    )


class RotationCanonicalCandidateSupport:
    """Bridge a saved UI build into the effect-aware recovery candidate pipeline.

    When canonical static context is enabled, the front-bar maximum is the starting
    resource ceiling. Bar-sensitive maximum and displayed-recovery changes are
    derived from each actual candidate plan's BAR_SWAP actions and replayed through
    the Phase 4 sustain timeline. Different front/back values therefore remain
    modeled rather than forcing a false global static resource state.

    An explicit combat state may be supplied for the static build snapshot. Runtime
    buffs and other transient conditions are therefore caller-owned evidence rather
    than being inferred from the selected build. The same state is used for both bar
    contexts so a single candidate evaluation cannot accidentally compare different
    transient worlds across a bar swap.

    Canonical saved-skill timing, range, and exact slot ownership are resolved once
    from the selected build and applied to each *final stabilized* candidate
    scorecard. Final-plan BAR_SWAP progression is also audited so every bar-bound
    cast must match the bar that is actually active at that instant. Recovery or
    candidate regeneration can move actions, so legality is deliberately checked
    against the final plan rather than only the seed schedule. Range checks
    additionally require explicit encounter target-distance windows; this bridge
    never invents positioning from role, encounter name, or action identity.

    A caller may also supply an already-resolved effective shared potion cooldown.
    Potion cadence is then audited across all final-plan potion actions regardless
    of potion name and merged into the existing hard cooldown obligation evidence.
    This bridge does not assume the base 45-second potion cooldown is correct for a
    build with unmodeled cooldown-reduction mechanics.

    Ambiguous saved-build slot identity is structural unresolved evidence and blocks
    candidate evaluation rather than silently omitting legality for that action.
    Timing/range evidence is narrower: unresolved evidence becomes candidate-specific
    only when the *final plan* actually uses the affected action. Range evidence is
    relevant only when explicit target-distance windows were supplied.
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
        action_timing_service: RotationSavedBuildActionTimingService | None = None,
        action_range_service: RotationSavedBuildActionRangeService | None = None,
        action_slot_service: RotationSavedBuildActionSlotService | None = None,
        cooldown_assessor: RotationActionCooldownAssessor | None = None,
        occupancy_assessor: RotationActionOccupancyAssessor | None = None,
        range_assessor: RotationActionRangeAssessor | None = None,
        slot_assessor: RotationActionSlotAssessor | None = None,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
        potion_cadence_bridge: RotationPotionCadenceCooldownBridgeService | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(database)
        self.pipeline = pipeline or RotationRecoveryHeavyCandidatePipelineService()
        self.validation_support = validation_support or RotationRecoveryValidationSupport()
        self.dependency_service = dependency_service or RotationMechanicsDependencyService()
        self.static_context_service = static_context_service
        self.action_timing_service = (
            action_timing_service or RotationSavedBuildActionTimingService(database)
        )
        self.action_range_service = (
            action_range_service or RotationSavedBuildActionRangeService(database)
        )
        self.action_slot_service = action_slot_service or RotationSavedBuildActionSlotService()
        self.cooldown_assessor = cooldown_assessor or RotationActionCooldownAssessor()
        self.occupancy_assessor = occupancy_assessor or RotationActionOccupancyAssessor()
        self.range_assessor = range_assessor or RotationActionRangeAssessor()
        self.slot_assessor = slot_assessor or RotationActionSlotAssessor()
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()
        self.potion_cadence_bridge = (
            potion_cadence_bridge or RotationPotionCadenceCooldownBridgeService()
        )

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
        combat_state: CombatState = CombatState(),
        demands: Iterable[RotationDemandWindow] = (),
        options: Iterable[RotationRefreshLeadCandidateOption] = (),
        wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None,
        requirements: Iterable[RotationEffectUptimeRequirement] = (),
        passives: Iterable[PassiveGrant] = (),
        target_distance_windows: Iterable[RotationTargetDistanceWindow] = (),
        potion_cadence_requirement: RotationPotionCadenceRequirement | None = None,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        initial_bar: str = "front",
        max_iterations: int = 6,
        baseline_id: str = "baseline",
        character_id: str | None = None,
        coverage_report: CanonicalMechanicsCoverageReport | None = None,
    ) -> RotationCanonicalCandidateApplicationResult:
        adaptation = self.build_adapter.adapt(player_build, character_id=character_id)
        unresolved = tuple(str(item).strip() for item in adaptation.unresolved if str(item).strip())
        if adaptation.build is None or unresolved:
            reasons = [
                "canonical candidate evaluation was not run because the saved build could not be fully resolved into canonical mechanics"
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
        target_distance_tuple = tuple(target_distance_windows)
        action_timing_evidence = self.action_timing_service.resolve(player_build)
        action_range_evidence = self.action_range_service.resolve(player_build)
        action_slot_evidence = self.action_slot_service.resolve(player_build)
        if action_slot_evidence.unresolved:
            reasons = [
                "canonical candidate evaluation was not run because saved-build action slot identity is unresolved"
            ]
            reasons.extend(
                f"saved-build slot evidence: {item}"
                for item in action_slot_evidence.unresolved
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
                action_timing_evidence=action_timing_evidence,
                action_range_evidence=action_range_evidence,
                action_slot_evidence=action_slot_evidence,
            )
        legality_scorecard_resolver = self._with_action_legality(
            scorecard_resolver,
            action_timing_evidence=action_timing_evidence,
            action_range_evidence=action_range_evidence,
            action_slot_evidence=action_slot_evidence,
            target_distance_windows=target_distance_tuple,
            potion_cadence_requirement=potion_cadence_requirement,
            initial_bar=initial_bar,
        )
        dependencies: tuple[RotationMechanicsDependency, ...] = ()
        knowledge_gaps: tuple[CanonicalKnowledgeGap, ...] = ()
        static_context: RotationStaticBuildContextResolution | None = None
        effective_maximum_amount = int(maximum_amount)
        canonical_maximum_amount: int | None = None
        calculation_context = None
        maximum_event_resolver = None
        displayed_recovery_resolver_factory = None

        if self.static_context_service is not None:
            static_context = self.static_context_service.resolve(
                player_build,
                combat_state=combat_state,
            )
            if not static_context.resolved:
                reasons = [
                    "canonical candidate evaluation was not run because static build calculation evidence is unresolved"
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
                    action_timing_evidence=action_timing_evidence,
                    action_range_evidence=action_range_evidence,
                    action_slot_evidence=action_slot_evidence,
                )

            calculation_context = static_context.context_for("front")
            if calculation_context is None:
                return RotationCanonicalCandidateApplicationResult(
                    build_adaptation=adaptation,
                    pipeline_result=None,
                    validation=RotationRecoveryValidationEvidence(
                        scope=RotationRecoveryValidationScope.NOT_EVALUATED,
                        selectable=None,
                        reasons=("canonical static rotation context is missing the front-bar starting state",),
                    ),
                    static_context=static_context,
                    action_timing_evidence=action_timing_evidence,
                    action_range_evidence=action_range_evidence,
                    action_slot_evidence=action_slot_evidence,
                )
            canonical_maximum_amount = static_context.maximum_amount_for("front", resource)
            effective_maximum_amount = canonical_maximum_amount
            maximum_event_resolver = static_context.maximum_events_for
            displayed_recovery_resolver_factory = static_context.displayed_recovery_resolver_for

        if coverage_report is not None:
            dependencies = self.dependency_service.discover(
                character_build=adaptation.build,
                demands=demand_tuple,
                requirements=requirement_tuple,
                passives=passive_tuple,
                recovery_enabled=True,
            )
            knowledge_gaps = coverage_report.dependency_gaps_for(
                "rotation_maker",
                self.dependency_service.keys(dependencies),
            )
            blocking = tuple(gap for gap in knowledge_gaps if gap.blocking)
            if blocking:
                reasons = ["canonical candidate evaluation was not run because required mechanics coverage is unresolved"]
                for gap in blocking:
                    evidence = self._dependency_evidence_for(gap.key, dependencies)
                    detail = f"mechanics coverage: {gap.summary} Bring back: {gap.needed_evidence}"
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
                    action_timing_evidence=action_timing_evidence,
                    action_range_evidence=action_range_evidence,
                    action_slot_evidence=action_slot_evidence,
                )

        result = self.pipeline.run_effects(
            player_build=player_build,
            character_build=adaptation.build,
            seed_plan=seed_plan,
            priorities=priorities,
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=legality_scorecard_resolver,
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
            calculation_context=calculation_context,
            maximum_event_resolver=maximum_event_resolver,
            displayed_recovery_resolver_factory=displayed_recovery_resolver_factory,
        )
        return RotationCanonicalCandidateApplicationResult(
            build_adaptation=adaptation,
            pipeline_result=result,
            validation=self.validation_support.from_candidate_pipeline_result(result),
            mechanics_dependencies=dependencies,
            knowledge_gaps=knowledge_gaps,
            static_context=static_context,
            canonical_maximum_amount=canonical_maximum_amount,
            action_timing_evidence=action_timing_evidence,
            action_range_evidence=action_range_evidence,
            action_slot_evidence=action_slot_evidence,
        )

    def _with_action_legality(
        self,
        resolver: RecoveryFinalScorecardResolver,
        *,
        action_timing_evidence: RotationSavedBuildActionTimingEvidence,
        action_range_evidence: RotationSavedBuildActionRangeEvidence,
        action_slot_evidence: RotationSavedBuildActionSlotEvidence,
        target_distance_windows: tuple[RotationTargetDistanceWindow, ...],
        potion_cadence_requirement: RotationPotionCadenceRequirement | None,
        initial_bar: str,
    ) -> RecoveryFinalScorecardResolver:
        def resolve(snapshot):
            scorecard = resolver(snapshot)
            cooldown_assessment = scorecard.cooldown_assessment
            occupancy_assessment = scorecard.occupancy_assessment
            range_assessment = scorecard.range_assessment
            slot_assessment = scorecard.slot_assessment
            active_bar_assessment = self.active_bar_assessor.assess(
                snapshot.plan,
                initial_bar=initial_bar,
            )

            if action_timing_evidence.cooldown_requirements:
                automatic = self.cooldown_assessor.assess(
                    snapshot.plan,
                    action_timing_evidence.cooldown_requirements,
                )
                cooldown_assessment = RotationActionCooldownAssessment(
                    self._dedupe_objects(
                        scorecard.cooldown_violations + automatic.violations
                    )
                )

            if potion_cadence_requirement is not None:
                automatic = self.potion_cadence_bridge.assess(
                    snapshot.plan,
                    potion_cadence_requirement,
                )
                cooldown_assessment = RotationActionCooldownAssessment(
                    self._dedupe_objects(
                        tuple(
                            getattr(cooldown_assessment, "violations", ())
                            if cooldown_assessment is not None
                            else ()
                        )
                        + automatic.violations
                    )
                )

            if action_timing_evidence.occupancy_requirements:
                automatic = self.occupancy_assessor.assess(
                    snapshot.plan,
                    action_timing_evidence.occupancy_requirements,
                )
                occupancy_assessment = RotationActionOccupancyAssessment(
                    self._dedupe_objects(
                        scorecard.occupancy_violations + automatic.violations
                    )
                )

            if action_range_evidence.range_requirements and target_distance_windows:
                automatic = self.range_assessor.assess(
                    snapshot.plan,
                    action_range_evidence.range_requirements,
                    target_distance_windows,
                )
                range_assessment = RotationActionRangeAssessment(
                    self._dedupe_objects(
                        scorecard.range_violations + automatic.violations
                    )
                )

            if action_slot_evidence.slot_requirements:
                automatic = self.slot_assessor.assess(
                    snapshot.plan,
                    action_slot_evidence.slot_requirements,
                )
                slot_assessment = RotationActionSlotAssessment(
                    self._dedupe_objects(
                        scorecard.slot_violations + automatic.violations
                    )
                )

            relevant_unresolved = self._relevant_action_evidence_gaps(
                snapshot.plan,
                action_timing_evidence=action_timing_evidence,
                action_range_evidence=action_range_evidence,
                range_relevant=bool(target_distance_windows),
            )
            candidate_specific_unresolved = self._dedupe_strings(
                scorecard.candidate_specific_unresolved + relevant_unresolved
            )

            return replace(
                scorecard,
                cooldown_assessment=cooldown_assessment,
                occupancy_assessment=occupancy_assessment,
                range_assessment=range_assessment,
                slot_assessment=slot_assessment,
                active_bar_assessment=active_bar_assessment,
                candidate_specific_unresolved=candidate_specific_unresolved,
            )

        return resolve

    @staticmethod
    def _relevant_action_evidence_gaps(
        plan: RotationPlan,
        *,
        action_timing_evidence: RotationSavedBuildActionTimingEvidence,
        action_range_evidence: RotationSavedBuildActionRangeEvidence,
        range_relevant: bool,
    ) -> tuple[str, ...]:
        used_names = {
            str(action.name).strip().casefold()
            for action in plan.actions
            if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
            and action.name
            and str(action.name).strip()
        }
        gaps: list[str] = []
        for name in action_timing_evidence.unresolved_action_names:
            if name.casefold() in used_names:
                gaps.append(f"canonical action timing unresolved for used action: {name}")
        if range_relevant:
            for name in action_range_evidence.unresolved_action_names:
                if name.casefold() in used_names:
                    gaps.append(f"canonical action range unresolved for used action: {name}")
        return tuple(gaps)

    @staticmethod
    def _dedupe_objects(values: tuple[object, ...]) -> tuple:
        ordered: list[object] = []
        for value in values:
            if value not in ordered:
                ordered.append(value)
        return tuple(ordered)

    @staticmethod
    def _dedupe_strings(values: tuple[str, ...]) -> tuple[str, ...]:
        ordered: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = str(raw or "").strip()
            key = value.casefold()
            if not value or key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)

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
            if key == wanted:
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
