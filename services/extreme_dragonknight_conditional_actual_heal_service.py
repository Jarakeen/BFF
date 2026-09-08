from __future__ import annotations

from dataclasses import replace

from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_dragonknight_earthen_heart_mending_service import (
    ExtremeDragonknightEarthenHeartMendingService,
)


class ExtremeDragonknightConditionalActualHealService(
    ExtremeConditionalActualHealOptimizationService
):
    """Add an explicit Earthen Heart Major Mending window to conditional heals.

    This adapter keeps the shared conditional optimizer stable while the Extreme
    healer mechanics are still being reviewed independently. The Dragonknight
    source contributes only the canonical ``Major Mending`` named buff, which is
    deduplicated by ``CombatState`` when another reviewed source such as Essence
    Drain is active at the same time.
    """

    def __init__(
        self,
        *,
        dragonknight_major_mending_window_active: bool = False,
        dragonknight_major_mending_source_ability: str | None = None,
        dragonknight_earthen_heart_mending: ExtremeDragonknightEarthenHeartMendingService | None = None,
        **kwargs,
    ) -> None:
        self.dragonknight_major_mending_window_active = bool(
            dragonknight_major_mending_window_active
        )
        self.dragonknight_major_mending_source_ability = (
            str(dragonknight_major_mending_source_ability or "").strip() or None
        )
        self.dragonknight_earthen_heart_mending = dragonknight_earthen_heart_mending
        super().__init__(**kwargs)

    def optimize(self, *args, **kwargs):
        result = super().optimize(*args, **kwargs)
        if not self.dragonknight_major_mending_window_active:
            return result
        source = self.dragonknight_major_mending_source_ability or "unspecified source"
        return replace(
            result,
            search_scope=(
                "explicit Dragonknight Major Mending window from "
                f"{source}; Earthen Heart source requires canonical legality proof",
                *result.search_scope,
            ),
        )

    def _restoration_combat_state(
        self,
        *,
        build: PlayerBuild,
        progression,
        active_bar: str,
    ) -> tuple[CombatState, tuple[str, ...]]:
        base_state, base_unresolved = super()._restoration_combat_state(
            build=build,
            progression=progression,
            active_bar=active_bar,
        )
        if not self.dragonknight_major_mending_window_active:
            return base_state, base_unresolved

        service = self.dragonknight_earthen_heart_mending
        if service is None:
            service = ExtremeDragonknightEarthenHeartMendingService()
            self.dragonknight_earthen_heart_mending = service
        result = service.resolve(
            build=build,
            source_ability_name=self.dragonknight_major_mending_source_ability,
            major_mending_window_active=True,
        )
        merged = CombatState(
            in_combat=(
                bool(base_state.in_combat) or bool(result.combat_state.in_combat)
            ),
            active_buffs=(
                *base_state.active_buffs,
                *result.combat_state.active_buffs,
            ),
            game_update=base_state.game_update,
        )
        unresolved = tuple(
            dict.fromkeys(
                message
                for message in (*base_unresolved, *result.unresolved)
                if message
            )
        )
        return merged, unresolved
