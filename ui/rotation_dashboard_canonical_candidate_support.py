from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from minmax.character_build.passive_grant import PassiveGrant
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow
from models.build_model import PlayerBuild
from services.canonical_mechanics_coverage_audit import CanonicalMechanicsCoverageReport
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
from ui.rotation_canonical_candidate_support import (
    RotationCanonicalCandidateApplicationResult,
    RotationCanonicalCandidateSupport,
)
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationResult,
    RotationGenerationSupport,
)


@dataclass(frozen=True)
class RotationDashboardCanonicalCandidateResult:
    """Dashboard seed-generation evidence plus canonical candidate evaluation."""

    seed_generation: RotationGenerationResult
    candidate_result: RotationCanonicalCandidateApplicationResult


class RotationDashboardCanonicalCandidateSupport:
    """Compose the existing dashboard generator with canonical candidate evaluation.

    The dashboard's current single-plan generator remains the owner of translating
    saved UI state into a deterministic seed schedule. This support layer then feeds
    that exact seed schedule and the same explicit ability priorities into the
    canonical saved-build candidate adapter/pipeline.

    Recovery stabilization is deliberately disabled while creating the seed. The
    candidate pipeline owns recovery fixed-point evaluation. Mechanics coverage, when
    supplied, is forwarded to the canonical bridge where the resolved CharacterBuild
    can discover only the dependencies relevant to this specific rotation.
    """

    def __init__(
        self,
        *,
        generation: RotationGenerationSupport | None = None,
        canonical_candidates: RotationCanonicalCandidateSupport | None = None,
    ) -> None:
        self.generation = generation or RotationGenerationSupport()
        self.canonical_candidates = (
            canonical_candidates or RotationCanonicalCandidateSupport()
        )

    def run_effects(
        self,
        *,
        player_build: PlayerBuild,
        generation_request: RotationGenerationRequest,
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
    ) -> RotationDashboardCanonicalCandidateResult:
        priorities = self._priority_list(
            player_build=player_build,
            generation_request=generation_request,
        )
        seed_request = replace(
            generation_request,
            stabilize_recovery_heavies=False,
            recovery_pressure_resolver=None,
        )
        seed_generation = self.generation.generate_with_evidence(
            build=player_build,
            request=seed_request,
        )

        candidate_result = self.canonical_candidates.run_effects(
            player_build=player_build,
            seed_plan=seed_generation.plan,
            priorities=priorities,
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=scorecard_resolver,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            demands=tuple(demands),
            options=tuple(options),
            wait_decision_factory=wait_decision_factory,
            requirements=tuple(requirements),
            passives=tuple(passives),
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
            baseline_id=baseline_id,
            character_id=character_id,
            coverage_report=coverage_report,
        )
        return RotationDashboardCanonicalCandidateResult(
            seed_generation=seed_generation,
            candidate_result=candidate_result,
        )

    @staticmethod
    def _priority_list(
        *,
        player_build: PlayerBuild,
        generation_request: RotationGenerationRequest,
    ) -> AbilityPriorityList:
        entries = tuple(generation_request.ability_priorities)
        if not entries:
            raise ValueError(
                "canonical dashboard candidate evaluation requires explicit ability priorities"
            )

        character_name = str(
            getattr(player_build, "CharacterName", "")
            or getattr(player_build, "Name", "")
            or getattr(player_build, "Gamertag", "")
            or ""
        ).strip()
        build_name = str(getattr(player_build, "BuildName", "") or "").strip()
        role = str(getattr(player_build, "Role", "") or "").strip()
        return AbilityPriorityList(
            character_name=character_name,
            build_name=build_name,
            role=role,
            entries=entries,
        )


__all__ = [
    "RotationDashboardCanonicalCandidateResult",
    "RotationDashboardCanonicalCandidateSupport",
]
