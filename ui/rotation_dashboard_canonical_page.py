from __future__ import annotations

from collections.abc import Iterable

from minmax.character_build.passive_grant import PassiveGrant
from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import RotationDemandWindow
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
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateResult,
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_dashboard_page import RotationDashboardPage
from ui.rotation_generation_support import RotationGenerationRequest


class CanonicalRotationDashboardPage(RotationDashboardPage):
    """Rotation dashboard with an explicit canonical-candidate execution seam.

    The inherited Generate Rotation button remains the current single-plan dashboard
    behavior. Canonical candidate evaluation is a separate guarded method until the
    page can supply all encounter, effect, recovery, and scorecard evidence needed to
    make a defensible selection.

    This class deliberately does not invent those inputs and does not silently fall
    back to resource-only recovery validation.
    """

    def __init__(
        self,
        parent=None,
        *,
        canonical_candidates: RotationDashboardCanonicalCandidateSupport | None = None,
    ) -> None:
        super().__init__(parent)
        self.rotation_canonical_candidates = (
            canonical_candidates
            or RotationDashboardCanonicalCandidateSupport(
                generation=self.rotation_generation,
            )
        )
        self.last_canonical_candidate_result: (
            RotationDashboardCanonicalCandidateResult | None
        ) = None

    def canonical_generation_request(self) -> RotationGenerationRequest:
        """Capture the dashboard's current saved-build generation inputs exactly once."""
        build = self._selected_build()
        if build is None:
            raise ValueError("select a saved build before canonical candidate evaluation")

        priorities = self.ability_priorities()
        if not priorities:
            raise ValueError(
                "canonical candidate evaluation requires explicit dashboard ability priorities"
            )

        settings = self.rotation_settings()
        return RotationGenerationRequest(
            duration_seconds=60.0,
            rotation_type=str(settings["rotation_type"]),
            potion=str(settings["potion"]),
            potion_on_cooldown=bool(settings["potion_on_cooldown"]),
            weave_light_attacks=True,
            ultimate_bar=str(settings["ultimate_bar"]),
            starting_ultimate=float(settings["starting_ultimate"]),
            use_scheduled_combat_attacks_for_ultimate=bool(
                settings["use_scheduled_combat_attacks_for_ultimate"]
            ),
            ability_priorities=priorities,
        )

    def evaluate_canonical_candidates(
        self,
        *,
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
    ) -> RotationDashboardCanonicalCandidateResult:
        """Run the page's current saved build through the canonical candidate path.

        The method intentionally returns evidence without replacing the timeline UI.
        Applying a selected candidate is a separate concern because final rendering
        must use post-recovery duration/sustain evidence rather than stale seed-plan
        evidence.
        """
        build = self._selected_build()
        if build is None:
            raise ValueError("select a saved build before canonical candidate evaluation")

        request = self.canonical_generation_request()
        result = self.rotation_canonical_candidates.run_effects(
            player_build=build,
            generation_request=request,
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
        )
        self.last_canonical_candidate_result = result
        return result


__all__ = ["CanonicalRotationDashboardPage"]
