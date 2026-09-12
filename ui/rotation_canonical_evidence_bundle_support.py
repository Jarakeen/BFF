from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_build.passive_grant import PassiveGrant
from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import RotationDemandWindow
from services.canonical_knowledge_gap import CanonicalKnowledgeGap
from services.canonical_mechanics_coverage_audit import CanonicalMechanicsCoverageReport
from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjectionService,
)
from services.encounter_rotation_demand_service import (
    EncounterRotationDemandPolicy,
    EncounterRotationDemandProjection,
    EncounterRotationDemandService,
)
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
    EncounterThresholdRotationDemandService,
)
from services.rotation_candidate_generation_service import RotationRefreshLeadCandidateOption
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_recovery_heavy_candidate_generation_bridge_service import (
    RecoveryCandidateEvaluatorResolver,
    RecoveryPressureWaitDecisionFactory,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RecoveryFinalScorecardResolver,
)
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    VerifiedRecoveryHeavyRestorationResolver,
)


@dataclass(frozen=True)
class RotationCanonicalEvidenceBundle:
    """Application-ready evidence for one canonical rotation candidate run."""

    encounter_id: str
    encounter_name: str
    demands: tuple[RotationDemandWindow, ...]
    options: tuple[RotationRefreshLeadCandidateOption, ...]
    requirements: tuple[RotationEffectUptimeRequirement, ...]
    passives: tuple[PassiveGrant, ...]
    evaluator_resolver: RecoveryCandidateEvaluatorResolver | None
    scorecard_resolver: RecoveryFinalScorecardResolver | None
    resource: ResourceType
    maximum_amount: int
    trigger_fraction: float
    content_type: str = ""
    target_resistance: float | None = None
    restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None
    wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None
    reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None
    max_iterations: int = 6
    baseline_id: str = "baseline"
    unresolved: tuple[str, ...] = ()
    knowledge_gaps: tuple[CanonicalKnowledgeGap, ...] = ()
    coverage_report: CanonicalMechanicsCoverageReport | None = None

    @property
    def blocking_knowledge_gaps(self) -> tuple[CanonicalKnowledgeGap, ...]:
        return tuple(gap for gap in self.knowledge_gaps if gap.blocking)

    @property
    def advisory_knowledge_gaps(self) -> tuple[CanonicalKnowledgeGap, ...]:
        return tuple(gap for gap in self.knowledge_gaps if not gap.blocking)

    @property
    def ready(self) -> bool:
        return not self.unresolved and not self.blocking_knowledge_gaps

    def research_for(self, consumer: str) -> tuple[CanonicalKnowledgeGap, ...]:
        key = str(consumer or "").strip().casefold()
        if not key:
            raise ValueError("research consumer must be non-empty")
        return tuple(gap for gap in self.knowledge_gaps if key in gap.consumers)


class RotationCanonicalEvidenceBundleSupport:
    """Assemble canonical encounter evidence without inventing execution facts.

    Clock-timed facts are projected directly through ``EncounterRotationDemandService``.
    Health-threshold policies are projected separately through the canonical encounter
    health/raid-damage clock layer, and only when the caller supplies explicit difficulty
    plus raid-damage segments. The two demand families are merged only after each has
    independently resolved its own evidence.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        guide_service: EncounterBossGuideService | None = None,
        demand_service: EncounterRotationDemandService | None = None,
        threshold_projection_service: EncounterHealthThresholdProjectionService | None = None,
        threshold_demand_service: EncounterThresholdRotationDemandService | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.guide_service = guide_service or EncounterBossGuideService(database)
        self.demand_service = demand_service or EncounterRotationDemandService()
        self.threshold_projection_service = (
            threshold_projection_service or EncounterHealthThresholdProjectionService()
        )
        self.threshold_demand_service = (
            threshold_demand_service or EncounterThresholdRotationDemandService()
        )

    def build(
        self,
        *,
        encounter_id: str,
        demand_policies: tuple[EncounterRotationDemandPolicy, ...],
        evaluator_resolver: RecoveryCandidateEvaluatorResolver | None,
        scorecard_resolver: RecoveryFinalScorecardResolver | None,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        threshold_demand_policies: tuple[EncounterThresholdRotationDemandPolicy, ...] = (),
        threshold_damage_segments: tuple[RaidDamageSegment, ...] = (),
        difficulty: str = "",
        target_resistance: float | None = None,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None,
        options: tuple[RotationRefreshLeadCandidateOption, ...] = (),
        requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: tuple[PassiveGrant, ...] = (),
        wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
        baseline_id: str = "baseline",
        knowledge_gaps: tuple[CanonicalKnowledgeGap, ...] = (),
        coverage_report: CanonicalMechanicsCoverageReport | None = None,
        coverage_dependency_keys: tuple[str, ...] | None = None,
    ) -> RotationCanonicalEvidenceBundle:
        encounter_key = str(encounter_id or "").strip()
        if not encounter_key:
            raise ValueError("canonical rotation evidence requires an encounter_id")
        if int(maximum_amount) <= 0:
            raise ValueError("canonical rotation evidence requires a positive maximum_amount")
        trigger = float(trigger_fraction)
        if not 0.0 <= trigger <= 1.0:
            raise ValueError("canonical rotation evidence trigger_fraction must be between 0 and 1")
        iterations = int(max_iterations)
        if iterations <= 0:
            raise ValueError("canonical rotation evidence max_iterations must be positive")
        baseline = str(baseline_id or "").strip()
        if not baseline:
            raise ValueError("canonical rotation evidence requires a non-empty baseline_id")
        resistance = None if target_resistance is None else float(target_resistance)
        if resistance is not None and resistance < 0.0:
            raise ValueError("canonical rotation target_resistance cannot be negative")

        guide = self.guide_service.get(encounter_key)
        projection: EncounterRotationDemandProjection = self.demand_service.project(
            guide=guide,
            policies=tuple(demand_policies),
        )
        demands = list(projection.demands)
        unresolved = [
            str(item).strip()
            for item in projection.unresolved
            if str(item).strip()
        ]

        threshold_policies = tuple(threshold_demand_policies)
        if threshold_policies:
            difficulty_key = str(difficulty or "").strip().casefold()
            damage_segments = tuple(threshold_damage_segments)
            if difficulty_key not in {"normal", "veteran", "hardmode"}:
                unresolved.append(
                    "health-threshold encounter demands require explicit normal, veteran, or hardmode difficulty"
                )
            elif not damage_segments:
                unresolved.append(
                    "health-threshold encounter demands require an explicit raid-damage trajectory"
                )
            else:
                threshold_projection = self.threshold_projection_service.project(
                    guide=guide,
                    difficulty=difficulty_key,
                    damage_segments=damage_segments,
                )
                threshold_demands = self.threshold_demand_service.project(
                    thresholds=threshold_projection,
                    policies=threshold_policies,
                )
                demands.extend(threshold_demands.demands)
                unresolved.extend(
                    str(item).strip()
                    for item in threshold_projection.unresolved
                    if str(item).strip()
                )
                unresolved.extend(
                    str(item).strip()
                    for item in threshold_demands.unresolved
                    if str(item).strip()
                )

        demands.sort(key=lambda item: (item.start_seconds, item.end_seconds, item.name))
        merged_gaps = list(knowledge_gaps)
        if coverage_report is not None and coverage_dependency_keys is not None:
            merged_gaps.extend(
                coverage_report.dependency_gaps_for(
                    "rotation_maker",
                    tuple(coverage_dependency_keys),
                )
            )

        return RotationCanonicalEvidenceBundle(
            encounter_id=guide.encounter_id,
            encounter_name=guide.name,
            content_type=str(getattr(guide, "content_type", "") or "").strip(),
            demands=tuple(demands),
            options=tuple(options),
            requirements=tuple(requirements),
            passives=tuple(passives),
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=scorecard_resolver,
            resource=resource,
            maximum_amount=int(maximum_amount),
            trigger_fraction=trigger,
            target_resistance=resistance,
            restoration_resolver=restoration_resolver,
            wait_decision_factory=wait_decision_factory,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=iterations,
            baseline_id=baseline,
            unresolved=tuple(dict.fromkeys(unresolved)),
            knowledge_gaps=self._dedupe_gaps(tuple(merged_gaps)),
            coverage_report=coverage_report,
        )

    @staticmethod
    def _dedupe_gaps(
        gaps: tuple[CanonicalKnowledgeGap, ...],
    ) -> tuple[CanonicalKnowledgeGap, ...]:
        result: list[CanonicalKnowledgeGap] = []
        seen: set[tuple[str, str, bool]] = set()
        for gap in gaps:
            key = (gap.domain.value, gap.key.casefold(), bool(gap.blocking))
            if key in seen:
                continue
            seen.add(key)
            result.append(gap)
        return tuple(result)


__all__ = [
    "RotationCanonicalEvidenceBundle",
    "RotationCanonicalEvidenceBundleSupport",
]
