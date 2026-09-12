from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.passive_grant import PassiveGrant
from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.resource_costs import ResourceType
from services.canonical_knowledge_gap import CanonicalKnowledgeGap
from services.canonical_mechanics_coverage_audit import CanonicalMechanicsCoverageReport
from services.encounter_rotation_demand_service import EncounterRotationDemandPolicy
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
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
from ui.rotation_canonical_evidence_bundle_support import (
    RotationCanonicalEvidenceBundle,
    RotationCanonicalEvidenceBundleSupport,
)


@dataclass(frozen=True)
class RotationSelectedEncounterEvidenceInputs:
    """Explicit policy/runtime inputs used with one selected canonical encounter.

    Encounter identity determines which persisted boss-guide facts may participate.
    These fields remain explicit because they represent rotation policy or build/runtime
    evidence rather than encounter truth. This adapter does not infer them from boss
    name, role, class, prose, or UI labels.

    Clock-timed demand policies and health-threshold policies remain separate. Threshold
    policies require both an explicit difficulty and an explicit raid-damage trajectory;
    neither is inferred from build potency or encounter names.

    The evaluator and scorecard resolver pair may both be omitted. The canonical
    dashboard candidate boundary then composes both from the exact generated seed plan
    through the shared Generate resolver service. Supplying only one remains invalid at
    that boundary so evaluation cannot mix incompatible evidence worlds.
    """

    demand_policies: tuple[EncounterRotationDemandPolicy, ...]
    evaluator_resolver: RecoveryCandidateEvaluatorResolver | None
    scorecard_resolver: RecoveryFinalScorecardResolver | None
    resource: ResourceType
    maximum_amount: int
    trigger_fraction: float
    threshold_demand_policies: tuple[EncounterThresholdRotationDemandPolicy, ...] = ()
    threshold_damage_segments: tuple[RaidDamageSegment, ...] = ()
    difficulty: str = ""
    restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None
    options: tuple[RotationRefreshLeadCandidateOption, ...] = ()
    requirements: tuple[RotationEffectUptimeRequirement, ...] = ()
    passives: tuple[PassiveGrant, ...] = ()
    wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None
    reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None
    max_iterations: int = 6
    baseline_id: str = "baseline"
    knowledge_gaps: tuple[CanonicalKnowledgeGap, ...] = ()
    coverage_report: CanonicalMechanicsCoverageReport | None = None
    coverage_dependency_keys: tuple[str, ...] | None = None


class RotationSelectedEncounterEvidenceSupport:
    """Build canonical rotation evidence for the exact selected encounter id."""

    def __init__(
        self,
        *,
        bundle_support: RotationCanonicalEvidenceBundleSupport | None = None,
    ) -> None:
        self.bundle_support = bundle_support or RotationCanonicalEvidenceBundleSupport()

    def build(
        self,
        *,
        encounter_id: str | None,
        inputs: RotationSelectedEncounterEvidenceInputs,
    ) -> RotationCanonicalEvidenceBundle:
        encounter_key = str(encounter_id or "").strip()
        if not encounter_key:
            raise ValueError(
                "select an encounter before resolving canonical rotation evidence"
            )

        return self.bundle_support.build(
            encounter_id=encounter_key,
            demand_policies=tuple(inputs.demand_policies),
            threshold_demand_policies=tuple(inputs.threshold_demand_policies),
            threshold_damage_segments=tuple(inputs.threshold_damage_segments),
            difficulty=str(inputs.difficulty or ""),
            evaluator_resolver=inputs.evaluator_resolver,
            scorecard_resolver=inputs.scorecard_resolver,
            resource=inputs.resource,
            maximum_amount=inputs.maximum_amount,
            trigger_fraction=inputs.trigger_fraction,
            restoration_resolver=inputs.restoration_resolver,
            options=tuple(inputs.options),
            requirements=tuple(inputs.requirements),
            passives=tuple(inputs.passives),
            wait_decision_factory=inputs.wait_decision_factory,
            reserve_assessment_resolver=inputs.reserve_assessment_resolver,
            max_iterations=inputs.max_iterations,
            baseline_id=inputs.baseline_id,
            knowledge_gaps=tuple(inputs.knowledge_gaps),
            coverage_report=inputs.coverage_report,
            coverage_dependency_keys=(
                None
                if inputs.coverage_dependency_keys is None
                else tuple(inputs.coverage_dependency_keys)
            ),
        )


__all__ = [
    "RotationSelectedEncounterEvidenceInputs",
    "RotationSelectedEncounterEvidenceSupport",
]
