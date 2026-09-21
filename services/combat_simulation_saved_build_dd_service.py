from __future__ import annotations

"""Run Combat Simulation with canonical saved-build DD damage evidence."""

from dataclasses import replace

from minmax.combat_state import CombatState
from minmax.combat_state_snapshot import CombatStateSnapshot
from minmax.rotation_plan import RotationPlan
from models.combat_simulation import (
    CombatSimulationIncomingDamage,
    CombatSimulationResult,
    CombatSimulationTargetState,
)
from models.effective_build_snapshot import EffectiveBuildSnapshot
from services.combat_simulation_fight_termination_service import (
    CombatSimulationFightTerminationService,
)
from services.combat_simulation_saved_build_dd_provider_service import (
    CombatSimulationSavedBuildDDProviderService,
    TargetCombatStateResolver,
    TargetResistanceResolver,
    TargetSnapshotResolver,
)
from services.combat_simulation_sequential_dd_damage_service import (
    CombatSimulationSequentialDDDamageService,
    CombatSimulationTargetHealthLedger,
)
from services.combat_simulation_service import CombatSimulationService
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


class CombatSimulationSavedBuildDDService:
    """Compose saved-build DD mechanics and run the deterministic simulator."""

    def __init__(
        self,
        *,
        provider_service: CombatSimulationSavedBuildDDProviderService | None = None,
        simulation_service: CombatSimulationService | None = None,
        sequential_damage_service: CombatSimulationSequentialDDDamageService | None = None,
        fight_termination_service: CombatSimulationFightTerminationService | None = None,
    ) -> None:
        self.provider_service = (
            provider_service or CombatSimulationSavedBuildDDProviderService()
        )
        self.simulation_service = simulation_service or CombatSimulationService()
        self.sequential_damage_service = (
            sequential_damage_service or CombatSimulationSequentialDDDamageService()
        )
        self.fight_termination_service = (
            fight_termination_service or CombatSimulationFightTerminationService()
        )

    def simulate(
        self,
        *,
        build_snapshot: EffectiveBuildSnapshot,
        plan: RotationPlan,
        target_state: CombatSimulationTargetState,
        damage_target_identity: str,
        target_resistance: float,
        initial_bar: str = "front",
        incoming_damage: tuple[CombatSimulationIncomingDamage, ...] = (),
        damage_candidate: GeneratedRotationCandidate | None = None,
        target_combat_state_resolver: TargetCombatStateResolver | None = None,
        target_resistance_resolver: TargetResistanceResolver | None = None,
        target_snapshot_resolver: TargetSnapshotResolver | None = None,
    ) -> CombatSimulationResult:
        build = build_snapshot.materialize()
        candidate = damage_candidate or GeneratedRotationCandidate(
            candidate_id="combat-simulation-saved-build",
            plan=plan,
            refresh_leads=(),
            action_claims=(),
        )
        if candidate.plan != plan:
            raise ValueError(
                "saved-build combat simulation candidate plan does not match simulation plan"
            )

        ledger = CombatSimulationTargetHealthLedger(
            target_state=target_state,
            target_identity=damage_target_identity,
            player_identity=str(build.Name or plan.character_name or "simulation_player"),
        )
        effective_snapshot_resolver = (
            target_snapshot_resolver
            if target_snapshot_resolver is not None
            else ledger.snapshot_at
        )

        resolution = self.provider_service.resolve(
            player_build=build,
            plan=plan,
            target_resistance=float(target_resistance),
            initial_bar=initial_bar,
            target_combat_state_resolver=target_combat_state_resolver,
            target_resistance_resolver=target_resistance_resolver,
            target_snapshot_resolver=effective_snapshot_resolver,
            execute_target_identity=damage_target_identity,
        )

        sequential_unresolved: tuple[str, ...] = ()
        replay_provider = resolution.provider
        execution_plan = plan
        execution_candidate = candidate
        if resolution.provider is not None:
            sequential = self.sequential_damage_service.project(
                plan=plan,
                candidate=candidate,
                action_damage_evidence_provider=resolution.provider,
                target_state=target_state,
                target_identity=damage_target_identity,
                player_identity=str(build.Name or plan.character_name or "simulation_player"),
                ledger=ledger,
            )
            sequential_unresolved = sequential.unresolved
            replay_provider = sequential.evidence_provider()
            if (
                sequential.terminated_at_seconds is not None
                and sequential.terminated_at_sequence is not None
            ):
                execution_plan = self.fight_termination_service.truncate(
                    plan,
                    time_seconds=sequential.terminated_at_seconds,
                    sequence=sequential.terminated_at_sequence,
                )
                execution_candidate = GeneratedRotationCandidate(
                    candidate_id=candidate.candidate_id,
                    plan=execution_plan,
                    refresh_leads=candidate.refresh_leads,
                    action_claims=candidate.action_claims,
                )

        result = self.simulation_service.simulate(
            build_snapshot=build_snapshot,
            plan=execution_plan,
            initial_bar=initial_bar,
            target_state=target_state,
            incoming_damage=tuple(
                item
                for item in incoming_damage
                if item.time_seconds <= execution_plan.duration_seconds
            ),
            damage_target_identity=damage_target_identity,
            damage_candidate=execution_candidate,
            action_damage_evidence_provider=replay_provider,
        )

        combined_unresolved = tuple(
            dict.fromkeys(
                (
                    *resolution.unresolved,
                    *sequential_unresolved,
                    *result.unresolved,
                )
            )
        )
        if combined_unresolved == result.unresolved:
            return result
        return replace(result, unresolved=combined_unresolved)


__all__ = ["CombatSimulationSavedBuildDDService"]
