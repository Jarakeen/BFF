from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from minmax.character_build.passive_grant import PassiveGrant
from minmax.combat_state import CombatState
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_action_target_legality import RotationTargetStateWindow
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_ultimate_affordability import RotationUltimateAffordabilityRequirement
from minmax.ultimate_generation_sources import CombatAttackUltimateGenerationSource
from models.build_model import PlayerBuild
from services.canonical_mechanics_coverage_audit import CanonicalMechanicsCoverageReport
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
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
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from ui.rotation_automatic_potion_cadence_candidate_support import (
    RotationAutomaticPotionCadenceCandidateSupport,
    RotationPotionCooldownScenarioEvidence,
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
from ui.rotation_runtime_snapshot_candidate_support import (
    RotationRuntimeSnapshotCandidateSupport,
)
from ui.rotation_saved_build_target_candidate_support import (
    RotationSavedBuildTargetCandidateSupport,
)
from ui.rotation_ultimate_affordability_candidate_support import (
    RotationUltimateAffordabilityCandidateSupport,
)
from ui.rotation_weapon_attack_candidate_support import (
    RotationWeaponAttackCandidateSupport,
)


@dataclass(frozen=True)
class RotationDashboardCanonicalCandidateResult:
    """Dashboard seed-generation evidence plus canonical candidate evaluation."""

    seed_generation: RotationGenerationResult
    candidate_result: RotationCanonicalCandidateApplicationResult


class RotationDashboardCanonicalCandidateSupport:
    """Compose dashboard seed generation with canonical candidate evaluation.

    The dashboard's current single-plan generator remains the owner of translating
    saved UI state into a deterministic seed schedule. This support layer then feeds
    that exact seed schedule and the same explicit ability priorities into the
    canonical saved-build candidate adapter/pipeline.

    Recovery stabilization is deliberately disabled while creating the seed. The
    candidate pipeline owns recovery fixed-point evaluation. The production default
    canonical candidate bridge also resolves static front/back build context, so
    verified armor/passive progression and canonical resource ceilings participate in
    readiness before recovery ranking. Explicit ``CombatState`` can provide base
    snapshot facts, while an optional runtime snapshot is projected through BFF's
    existing role-neutral runtime-state service before static candidate evaluation.
    Runtime snapshot bar ownership remains explicit rather than guessed.

    Heavy restoration defaults to the canonical generated-plan evidence path. Callers
    may still provide an explicit reviewed resolver for compatibility or research.

    Production defaults compose final-candidate evidence adapters for weapon attacks,
    saved-build targets, automatic potion cadence, Ultimate affordability, and shared
    runtime snapshot state. Weapon attack evidence projects final light/heavy attacks
    through the same canonical saved-build weapon adapter and promotes unresolved
    weapon identity to candidate-specific evidence; wrong-bar attacks remain the
    existing active-bar hard obligation. Saved-build target evidence enforces
    unambiguous Enemy, Self, and Ground identities only when explicit target-state
    windows are supplied. Missing evidence preserves the existing no-guess behavior.
    """

    def __init__(
        self,
        *,
        generation: RotationGenerationSupport | None = None,
        canonical_candidates: (
            RotationCanonicalCandidateSupport
            | RotationWeaponAttackCandidateSupport
            | RotationSavedBuildTargetCandidateSupport
            | RotationAutomaticPotionCadenceCandidateSupport
            | RotationUltimateAffordabilityCandidateSupport
            | RotationRuntimeSnapshotCandidateSupport
            | None
        ) = None,
    ) -> None:
        self.generation = generation or RotationGenerationSupport()
        if canonical_candidates is not None:
            self.canonical_candidates = canonical_candidates
        else:
            canonical = RotationCanonicalCandidateSupport(
                static_context_service=RotationStaticBuildContextService(),
            )
            weapon_aware = RotationWeaponAttackCandidateSupport(
                canonical_candidates=canonical,
                build_adapter=canonical.build_adapter,
            )
            target_aware = RotationSavedBuildTargetCandidateSupport(
                canonical_candidates=weapon_aware,
            )
            potion_aware = RotationAutomaticPotionCadenceCandidateSupport(
                canonical_candidates=target_aware,
            )
            ultimate_aware = RotationUltimateAffordabilityCandidateSupport(
                canonical_candidates=potion_aware,
            )
            self.canonical_candidates = RotationRuntimeSnapshotCandidateSupport(
                canonical_candidates=ultimate_aware,
                base_canonical=canonical,
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
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None,
        combat_state: CombatState = CombatState(),
        runtime_snapshot: ExtremeRuntimeSnapshot | None = None,
        runtime_snapshot_active_bar: str | None = None,
        demands: Iterable[RotationDemandWindow] = (),
        options: Iterable[RotationRefreshLeadCandidateOption] = (),
        wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None,
        requirements: Iterable[RotationEffectUptimeRequirement] = (),
        passives: Iterable[PassiveGrant] = (),
        target_state_windows: Iterable[RotationTargetStateWindow] = (),
        potion_cooldown_scenario_evidence: RotationPotionCooldownScenarioEvidence | None = None,
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

        candidate_kwargs = dict(
            player_build=player_build,
            seed_plan=seed_generation.plan,
            priorities=priorities,
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=scorecard_resolver,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            combat_state=combat_state,
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
        if runtime_snapshot is not None:
            candidate_kwargs["runtime_snapshot"] = runtime_snapshot
            candidate_kwargs["runtime_snapshot_active_bar"] = runtime_snapshot_active_bar
        target_state_tuple = tuple(target_state_windows)
        if target_state_tuple:
            candidate_kwargs["target_state_windows"] = target_state_tuple
        if potion_cooldown_scenario_evidence is not None:
            candidate_kwargs["potion_cooldown_scenario_evidence"] = (
                potion_cooldown_scenario_evidence
            )

        ultimate_projection = seed_generation.ultimate_projection
        spend_rules = tuple(
            getattr(ultimate_projection, "spend_rules", ())
            if ultimate_projection is not None
            else ()
        )
        attack_generation_is_candidate_dependent = bool(
            generation_request.use_scheduled_combat_attacks_for_ultimate
        )
        if spend_rules:
            static_generation_events = (
                ()
                if attack_generation_is_candidate_dependent
                else tuple(getattr(ultimate_projection, "generation_events", ()))
            )
            candidate_kwargs["ultimate_affordability_requirement"] = (
                RotationUltimateAffordabilityRequirement(
                    starting_amount=float(generation_request.starting_ultimate),
                    spend_rules=spend_rules,
                    generation_events=static_generation_events,
                )
            )
            if attack_generation_is_candidate_dependent:
                attack_source = CombatAttackUltimateGenerationSource()
                candidate_kwargs["ultimate_generation_event_resolver"] = (
                    lambda plan: attack_source.events_from_plan(
                        plan=plan,
                        assume_scheduled_attacks_damage=True,
                    )
                )

        candidate_result = self.canonical_candidates.run_effects(**candidate_kwargs)
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
