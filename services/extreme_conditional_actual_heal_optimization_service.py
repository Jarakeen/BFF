from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult


class ExtremeConditionalActualHealOptimizationService(ExtremeActualHealOptimizationService):
    """Optimize one heal under one explicit target-health condition.

    The ordinary ``ExtremeActualHealOptimizationService`` remains the standing
    result and does not activate target-health conditionals. This service is the
    deliberately separate emergency/conditional path. It uses the same whole-
    build candidate search but forwards one explicit target-health fraction to
    the healing-event evaluator on every context rebuild.

    Keeping the paths separate prevents mechanics such as Restoration Expert
    from contaminating the ordinary standing maximum merely because they are
    useful in a deliberately constructed low-health scenario.
    """

    def __init__(self, *, target_health_fraction: float, **kwargs) -> None:
        value = float(target_health_fraction)
        if not 0.0 <= value <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")
        self.target_health_fraction = value
        super().__init__(**kwargs)

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
        context = self.optimizer.context_factory.build(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=candidate_progression,
            active_bar=active_bar,
        )
        event = self.healing_events.evaluate(
            build=build,
            context=context,
            entity_id=entity_id,
            target_health_fraction=self.target_health_fraction,
        )
        unresolved = tuple(context.unresolved_gear_effects) + tuple(event.unresolved)
        return event, tuple(
            dict.fromkeys(message for message in unresolved if message)
        )
