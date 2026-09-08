from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.combat_state import CombatState
from models.build_model import PlayerBuild
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult
from services.extreme_restoration_heavy_combat_state_service import (
    ExtremeRestorationHeavyCombatStateService,
)


class ExtremeConditionalActualHealOptimizationService(ExtremeActualHealOptimizationService):
    """Optimize one heal under explicit emergency/combat-state conditions.

    The ordinary ``ExtremeActualHealOptimizationService`` remains the standing
    result and does not activate target-health or trigger-dependent conditionals.
    This service forwards one explicit target-health fraction through every
    whole-build candidate rebuild.

    A caller may also state that a fully charged Restoration Staff heavy attack
    has just completed. When that trigger is requested, the reviewed Essence
    Drain resolver proves weapon/passive legality and routes Major Mending through
    canonical ``CombatState``. The +16% therefore remains owned by the named-buff
    Healing Done layer rather than becoming an ad-hoc event multiplier.
    """

    def __init__(
        self,
        *,
        target_health_fraction: float,
        fully_charged_restoration_heavy_attack_completed: bool = False,
        restoration_heavy_state: ExtremeRestorationHeavyCombatStateService | None = None,
        **kwargs,
    ) -> None:
        value = float(target_health_fraction)
        if not 0.0 <= value <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")
        self.target_health_fraction = value
        self.fully_charged_restoration_heavy_attack_completed = bool(
            fully_charged_restoration_heavy_attack_completed
        )
        self.restoration_heavy_state = restoration_heavy_state
        super().__init__(**kwargs)

    def _restoration_combat_state(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        active_bar: str,
    ) -> tuple[CombatState, tuple[str, ...]]:
        if not self.fully_charged_restoration_heavy_attack_completed:
            return CombatState(), ()

        service = self.restoration_heavy_state
        if service is None:
            service = ExtremeRestorationHeavyCombatStateService(
                getattr(self.optimizer, "database_path", None)
            )
            self.restoration_heavy_state = service
        result = service.resolve(
            build=build,
            progression=progression,
            active_bar=active_bar,
            fully_charged_heavy_attack_completed=True,
        )
        return result.combat_state, tuple(result.unresolved)

    def _evaluate(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        entity_id: str,
        active_bar: str,
    ) -> tuple[ExtremeHealingEventResult, tuple[str, ...]]:
        candidate_progression = replace(
            progression,
            attributes=AttributeAllocation(
                health=int(build.AttributeHealth or 0),
                magicka=int(build.AttributeMagicka or 0),
                stamina=int(build.AttributeStamina or 0),
            ),
        )
        combat_state, combat_unresolved = self._restoration_combat_state(
            build=build,
            progression=candidate_progression,
            active_bar=active_bar,
        )
        context = self.optimizer.context_factory.build(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=candidate_progression,
            combat_state=combat_state,
            active_bar=active_bar,
        )
        event = self.healing_events.evaluate(
            build=build,
            context=context,
            entity_id=entity_id,
            target_health_fraction=self.target_health_fraction,
        )
        unresolved = (
            tuple(context.unresolved_gear_effects)
            + tuple(combat_unresolved)
            + tuple(event.unresolved)
        )
        return event, tuple(
            dict.fromkeys(message for message in unresolved if message)
        )
