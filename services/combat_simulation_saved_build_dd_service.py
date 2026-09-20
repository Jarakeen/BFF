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
from services.combat_simulation_saved_build_dd_provider_service import (
    CombatSimulationSavedBuildDDProviderService,
    TargetCombatStateResolver,
    TargetResistanceResolver,
    TargetSnapshotResolver,
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
    ) -> None:
        self.provider_service = (
            provider_service or CombatSimulationSavedBuildDDProviderService()
        )
        self.simulation_service = simulation_service or CombatSimulationService()

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
        resolution = self.provider_service.resolve(
            player_build=build,
            plan=plan,
            target_resistance=float(target_resistance),
            initial_bar=initial_bar,
            target_combat_state_resolver=target_combat_state_resolver,
            target_resistance_resolver=target_resistance_resolver,
            target_snapshot_resolver=target_snapshot_resolver,
            execute_target_identity=damage_target_identity,
        )

        result = self.simulation_service.simulate(
            build_snapshot=build_snapshot,
            plan=plan,
            initial_bar=initial_bar,
            target_state=target_state,
            incoming_damage=incoming_damage,
            damage_target_identity=damage_target_identity,
            damage_candidate=damage_candidate,
            action_damage_evidence_provider=resolution.provider,
        )

        if not resolution.unresolved:
            return result
        return replace(
            result,
            unresolved=tuple(
                dict.fromkeys((*resolution.unresolved, *result.unresolved))
            ),
        )


__all__ = ["CombatSimulationSavedBuildDDService"]
