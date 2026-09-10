from __future__ import annotations

from dataclasses import replace

from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_dragonknight_dragon_blood_healing_service import (
    ExtremeDragonknightDragonBloodHealingService,
)
from services.extreme_dragonknight_earthen_heart_mending_service import (
    ExtremeDragonknightEarthenHeartMendingService,
)
from services.extreme_dragonknight_elder_dragon_combat_state_service import (
    ExtremeDragonknightElderDragonCombatStateService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult


class ExtremeDragonknightConditionalActualHealService(
    ExtremeConditionalActualHealOptimizationService
):
    """Add reviewed Dragonknight conditional healing state.

    Earthen Heart shield-family sources may contribute canonical ``Major Mending``
    during an explicit reviewed window. Elder Dragon may likewise contribute
    canonical ``Minor Brutality`` during an explicitly proven post-Draconic-Power
    activation window. Duplicate named buffs remain deduplicated by CombatState.

    Unmorphed ``Dragon Blood`` may also use an explicit caster-Health fraction to
    resolve its reviewed missing-Health self-heal modifier. Blood of the Green
    Dragon is intentionally not multiplied here because its immediate heal and
    later HoT are guarded by the Extreme temporal-scope boundary. Blood of the
    Elder Dragon remains behind the separate recipient-scope boundary until self
    versus nearby-ally coefficient identity is canonical.
    """

    def __init__(
        self,
        *,
        dragonknight_major_mending_window_active: bool = False,
        dragonknight_major_mending_source_ability: str | None = None,
        elder_dragon_window_active: bool = False,
        caster_health_fraction: float | None = None,
        dragonknight_earthen_heart_mending: ExtremeDragonknightEarthenHeartMendingService | None = None,
        dragonknight_elder_dragon_state: ExtremeDragonknightElderDragonCombatStateService | None = None,
        dragonknight_dragon_blood_healing: ExtremeDragonknightDragonBloodHealingService | None = None,
        **kwargs,
    ) -> None:
        if caster_health_fraction is not None:
            caster_health_fraction = float(caster_health_fraction)
            if not 0.0 <= caster_health_fraction <= 1.0:
                raise ValueError("caster_health_fraction must be between 0 and 1")
        self.dragonknight_major_mending_window_active = bool(
            dragonknight_major_mending_window_active
        )
        self.dragonknight_major_mending_source_ability = (
            str(dragonknight_major_mending_source_ability or "").strip() or None
        )
        self.elder_dragon_window_active = bool(elder_dragon_window_active)
        self.caster_health_fraction = caster_health_fraction
        self.dragonknight_earthen_heart_mending = dragonknight_earthen_heart_mending
        self.dragonknight_elder_dragon_state = dragonknight_elder_dragon_state
        self.dragonknight_dragon_blood_healing = dragonknight_dragon_blood_healing
        super().__init__(**kwargs)

    def optimize(self, *args, **kwargs):
        result = super().optimize(*args, **kwargs)
        scenarios: list[str] = []
        if self.caster_health_fraction is not None:
            scenarios.append(
                "explicit Dragon Blood caster Health fraction "
                f"{self.caster_health_fraction:.6f}; missing-Health self-heal scaling "
                "requires canonical Draconic Power legality proof"
            )
        if self.dragonknight_major_mending_window_active:
            source = self.dragonknight_major_mending_source_ability or "unspecified source"
            scenarios.append(
                "explicit Dragonknight Major Mending window from "
                f"{source}; Earthen Heart source requires canonical legality proof"
            )
        if self.elder_dragon_window_active:
            scenarios.append(
                "explicit Elder Dragon post-activation window; Minor Brutality "
                "requires canonical Draconic Power and passive-rank proof"
            )
        if not scenarios:
            return result
        return replace(
            result,
            search_scope=(*scenarios, *result.search_scope),
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
        states = [base_state]
        unresolved_messages = list(base_unresolved)

        if self.dragonknight_major_mending_window_active:
            service = self.dragonknight_earthen_heart_mending
            if service is None:
                service = ExtremeDragonknightEarthenHeartMendingService()
                self.dragonknight_earthen_heart_mending = service
            result = service.resolve(
                build=build,
                source_ability_name=self.dragonknight_major_mending_source_ability,
                major_mending_window_active=True,
            )
            states.append(result.combat_state)
            unresolved_messages.extend(result.unresolved)

        if self.elder_dragon_window_active:
            service = self.dragonknight_elder_dragon_state
            if service is None:
                service = ExtremeDragonknightElderDragonCombatStateService()
                self.dragonknight_elder_dragon_state = service
            result = service.resolve(
                build=build,
                progression=progression,
                elder_dragon_window_active=True,
            )
            states.append(result.combat_state)
            unresolved_messages.extend(result.unresolved)

        merged = CombatState(
            in_combat=any(bool(state.in_combat) for state in states),
            active_buffs=tuple(
                buff
                for state in states
                for buff in state.active_buffs
            ),
            game_update=base_state.game_update,
        )
        unresolved = tuple(
            dict.fromkeys(
                message
                for message in unresolved_messages
                if message
            )
        )
        return merged, unresolved

    def _dragon_blood_self_heal_event(
        self,
        *,
        build: PlayerBuild,
        event: ExtremeHealingEventResult,
    ) -> ExtremeHealingEventResult:
        tooltip_result = getattr(event, "tooltip_result", None)
        skill = getattr(tooltip_result, "skill", None)
        skill_name = str(getattr(skill, "name", "") or "").strip()
        if skill_name.casefold() != "dragon blood":
            return event

        service = self.dragonknight_dragon_blood_healing
        if service is None:
            service = ExtremeDragonknightDragonBloodHealingService()
            self.dragonknight_dragon_blood_healing = service
        dragon_blood = service.resolve(
            build=build,
            ability_name=skill_name,
            caster_health_fraction=self.caster_health_fraction,
        )
        multiplier = float(dragon_blood.multiplier)
        normal_heal = (
            None if event.normal_heal is None else float(event.normal_heal) * multiplier
        )
        critical_heal = (
            None
            if event.critical_heal is None
            else float(event.critical_heal) * multiplier
        )
        unresolved = tuple(
            dict.fromkeys((*event.unresolved, *dragon_blood.unresolved))
        )
        return replace(
            event,
            normal_heal=normal_heal,
            critical_heal=critical_heal,
            unresolved=unresolved,
        )

    def _evaluate(self, build, **kwargs):
        event, unresolved = super()._evaluate(build, **kwargs)
        event = self._dragon_blood_self_heal_event(build=build, event=event)
        combined = tuple(
            dict.fromkeys((*unresolved, *event.unresolved))
        )
        return event, combined
