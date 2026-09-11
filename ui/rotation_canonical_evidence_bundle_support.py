from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_build.passive_grant import PassiveGrant
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import RotationDemandWindow
from services.canonical_knowledge_gap import CanonicalKnowledgeGap
from services.canonical_mechanics_coverage_audit import CanonicalMechanicsCoverageReport
from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_rotation_demand_service import (
    EncounterRotationDemandPolicy,
    EncounterRotationDemandProjection,
    EncounterRotationDemandService,
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
    """Application-ready evidence for one canonical rotation candidate run.

    Broad mechanics coverage may be retained for later CharacterBuild-specific
    dependency discovery. Explicitly scoped coverage gaps can still participate in
    immediate readiness when the caller already knows the required dependency keys.

    ``restoration_resolver`` is now an optional explicit override. When omitted, the
    effect-aware recovery pipeline derives Heavy Attack completion/restoration from
    the generated plan's verified channel-reservation provenance and canonical saved-
    character mechanics. Explicit resolvers remain available for reviewed research,
    diagnostics, and compatibility callers.
    """

    encounter_id: str
    encounter_name: str
    demands: tuple[RotationDemandWindow, ...]
    options: tuple[RotationRefreshLeadCandidateOption, ...]
    requirements: tuple[RotationEffectUptimeRequirement, ...]
    passives: tuple[PassiveGrant, ...]
    evaluator_resolver: RecoveryCandidateEvaluatorResolver
    scorecard_resolver: RecoveryFinalScorecardResolver
    resource: ResourceType
    maximum_amount: int
    trigger_fraction: float
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
        """Return currently materialized blocking and advisory research for a consumer."""

        key = str(consumer or "").strip().casefold()
        if not key:
            raise ValueError("research consumer must be non-empty")
        return tuple(gap for gap in self.knowledge_gaps if key in gap.consumers)


class RotationCanonicalEvidenceBundleSupport:
    """Assemble canonical encounter evidence without inventing execution facts.

    If explicit ``coverage_dependency_keys`` are supplied, those mechanics are scoped
    immediately and can affect bundle readiness. If a broad coverage report is supplied
    without explicit dependencies, the report is retained but its global gaps are not
    merged yet; the resolved CharacterBuild later discovers which rows actually matter.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        guide_service: EncounterBossGuideService | None = None,
        demand_service: EncounterRotationDemandService | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.guide_service = guide_service or EncounterBossGuideService(database)
        self.demand_service = demand_service or EncounterRotationDemandService()

    def build(
        self,
        *,
        encounter_id: str,
        demand_policies: tuple[EncounterRotationDemandPolicy, ...],
        evaluator_resolver: RecoveryCandidateEvaluatorResolver,
        scorecard_resolver: RecoveryFinalScorecardResolver,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
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

        guide = self.guide_service.get(encounter_key)
        projection: EncounterRotationDemandProjection = self.demand_service.project(
            guide=guide,
            policies=tuple(demand_policies),
        )

        unresolved = tuple(
            str(item).strip()
            for item in projection.unresolved
            if str(item).strip()
        )
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
            demands=tuple(projection.demands),
            options=tuple(options),
            requirements=tuple(requirements),
            passives=tuple(passives),
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=scorecard_resolver,
            resource=resource,
            maximum_amount=int(maximum_amount),
            trigger_fraction=trigger,
            restoration_resolver=restoration_resolver,
            wait_decision_factory=wait_decision_factory,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=iterations,
            baseline_id=baseline,
            unresolved=unresolved,
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
