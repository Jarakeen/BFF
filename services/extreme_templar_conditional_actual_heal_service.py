from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
    ExtremeActualHealOptimizationResult,
)
from services.extreme_templar_illuminate_combat_state_service import (
    ExtremeTemplarIlluminateCombatStateService,
)


class ExtremeTemplarConditionalActualHealService(
    ExtremeConditionalActualHealOptimizationService
):
    """Add reviewed Templar Illuminate power state to conditional heal search.

    Illuminate is intentionally modeled before coefficient evaluation. It grants
    the named U50 ``Minor Sorcery`` buff after a qualifying Dawn's Wrath cast,
    which increases Spell Damage rather than Healing Done. The generic conditional
    service still owns target-health, Mending, Sacred Ground, Restoration Staff,
    Necromancer, and Arcanist conditional behavior.
    """

    def __init__(
        self,
        *,
        illuminate_window_active: bool = False,
        templar_illuminate_state: ExtremeTemplarIlluminateCombatStateService | None = None,
        **kwargs,
    ) -> None:
        self.illuminate_window_active = bool(illuminate_window_active)
        self.templar_illuminate_state = templar_illuminate_state
        super().__init__(**kwargs)

    def optimize(
        self,
        baseline_build: PlayerBuild,
        entity_id: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        progression_override: CharacterProgression | None = None,
    ) -> ExtremeActualHealOptimizationResult:
        result = super().optimize(
            baseline_build,
            entity_id,
            active_bar=active_bar,
            max_passes=max_passes,
            progression_override=progression_override,
        )
        if not self.illuminate_window_active:
            return result
        return replace(
            result,
            search_scope=(
                result.search_scope[0],
                "explicit Illuminate active window after qualifying Dawn's Wrath cast; "
                "Minor Sorcery requires canonical legality proof and modifies Spell Damage "
                "before coefficient evaluation",
                *result.search_scope[1:],
            ),
        )

    def _restoration_combat_state(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        active_bar: str,
    ) -> tuple[CombatState, tuple[str, ...]]:
        base_state, base_unresolved = super()._restoration_combat_state(
            build=build,
            progression=progression,
            active_bar=active_bar,
        )
        if not self.illuminate_window_active:
            return base_state, base_unresolved

        service = self.templar_illuminate_state
        if service is None:
            service = ExtremeTemplarIlluminateCombatStateService(
                getattr(self.optimizer, "database_path", None)
            )
            self.templar_illuminate_state = service
        illuminate = service.resolve(
            build=build,
            progression=progression,
            illuminate_window_active=True,
        )
        combined = CombatState(
            in_combat=bool(base_state.in_combat or illuminate.combat_state.in_combat),
            active_buffs=(
                *base_state.active_buffs,
                *illuminate.combat_state.active_buffs,
            ),
            game_update=base_state.game_update,
        )
        unresolved = tuple(
            dict.fromkeys(
                message
                for message in (*base_unresolved, *illuminate.unresolved)
                if message
            )
        )
        return combined, unresolved
