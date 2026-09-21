from __future__ import annotations

"""Plan-owned attacker runtime state for Combat Simulation.

This service composes only facts proven by the final RotationPlan and saved build:
active bar ordering, explicitly scheduled potion actions, and reviewed persistent
toggles. It intentionally does not manufacture external proc, group-buff, encounter,
or log-history state.
"""

from minmax.combat_state import CombatState
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from minmax.character_progression import CharacterProgression
from services.rotation_plan_persistent_toggle_combat_state_service import (
    RotationPlanPersistentToggleCombatStateService,
)
from services.rotation_plan_potion_combat_state_service import (
    RotationPlanPotionCombatStateService,
)
from services.rotation_plan_runtime_combat_state_service import (
    RotationPlanRuntimeCombatStateResult,
)


class CombatSimulationPlanAttackerStateService:
    """Resolve exact attacker CombatState from final-plan-owned evidence only."""

    def __init__(
        self,
        *,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
        potion_state_service: RotationPlanPotionCombatStateService | None = None,
        toggle_state_service: RotationPlanPersistentToggleCombatStateService | None = None,
    ) -> None:
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()
        self.potion_state_service = (
            potion_state_service or RotationPlanPotionCombatStateService()
        )
        self.toggle_state_service = (
            toggle_state_service or RotationPlanPersistentToggleCombatStateService()
        )

    def resolve(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        plan: RotationPlan,
        time_seconds: float,
        sequence: int | None = None,
        initial_bar: str = "front",
        base_combat_state: CombatState = CombatState(),
    ) -> RotationPlanRuntimeCombatStateResult:
        instant = float(time_seconds)
        if instant < 0.0:
            raise ValueError("combat simulation attacker runtime time cannot be negative")
        if instant > float(plan.duration_seconds) + 1e-12:
            raise ValueError(
                "combat simulation attacker runtime time cannot exceed plan duration"
            )
        boundary_sequence = None if sequence is None else int(sequence)
        if boundary_sequence is not None and boundary_sequence < 0:
            raise ValueError(
                "combat simulation attacker runtime sequence cannot be negative"
            )

        active_bar = self.active_bar_assessor.active_bar_at(
            plan,
            time_seconds=instant,
            sequence=boundary_sequence,
            initial_bar=initial_bar,
        )

        potion = self.potion_state_service.resolve(
            build,
            progression=progression,
            plan=plan,
            time_seconds=instant,
            sequence=boundary_sequence,
            base_combat_state=base_combat_state,
        )
        if not potion.resolved or potion.combat_state is None:
            return RotationPlanRuntimeCombatStateResult(
                time_seconds=instant,
                sequence=boundary_sequence,
                active_bar=active_bar,
                combat_state=None,
                unresolved=tuple(potion.unresolved),
            )

        toggles = self.toggle_state_service.resolve(
            build,
            plan=plan,
            time_seconds=instant,
            sequence=boundary_sequence,
            base_combat_state=potion.combat_state,
        )
        if not toggles.resolved or toggles.combat_state is None:
            return RotationPlanRuntimeCombatStateResult(
                time_seconds=instant,
                sequence=boundary_sequence,
                active_bar=active_bar,
                combat_state=None,
                unresolved=tuple(toggles.unresolved),
            )

        return RotationPlanRuntimeCombatStateResult(
            time_seconds=instant,
            sequence=boundary_sequence,
            active_bar=active_bar,
            combat_state=toggles.combat_state,
        )

    def resolver(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        plan: RotationPlan,
        initial_bar: str = "front",
        base_combat_state: CombatState = CombatState(),
    ):
        def resolve(time_seconds: float, sequence: int | None = None):
            return self.resolve(
                build,
                progression=progression,
                plan=plan,
                time_seconds=time_seconds,
                sequence=sequence,
                initial_bar=initial_bar,
                base_combat_state=base_combat_state,
            )

        return resolve


__all__ = ["CombatSimulationPlanAttackerStateService"]
