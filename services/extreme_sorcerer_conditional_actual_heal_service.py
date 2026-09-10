from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationResult,
)
from services.extreme_canonical_healing_done_conditional_actual_heal_service import (
    ExtremeCanonicalHealingDoneConditionalActualHealService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult
from services.extreme_sorcerer_expert_summoner_pet_context_service import (
    ExtremeSorcererExpertSummonerPetContextService,
)


class ExtremeSorcererConditionalActualHealService(
    ExtremeCanonicalHealingDoneConditionalActualHealService
):
    """Evaluate conditional Sorcerer heals with explicit permanent-pet state.

    Expert Summoner's permanent-pet Max Health branch is resolved before healing
    coefficient evaluation. The branch is never inferred merely because a pet
    ability is slotted; the caller must explicitly prove that a permanent pet is
    active for the evaluated snapshot.
    """

    def __init__(
        self,
        *,
        permanent_pet_active: bool = False,
        expert_summoner_pet_context: (
            ExtremeSorcererExpertSummonerPetContextService | None
        ) = None,
        **kwargs,
    ) -> None:
        self.permanent_pet_active = bool(permanent_pet_active)
        self.expert_summoner_pet_context = (
            expert_summoner_pet_context
            or ExtremeSorcererExpertSummonerPetContextService()
        )
        super().__init__(**kwargs)

    def optimize(
        self,
        baseline_build: PlayerBuild,
        entity_id: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        progression_override: CharacterProgression | None = None,
        evaluation_cache=None,
    ) -> ExtremeActualHealOptimizationResult:
        result = super().optimize(
            baseline_build,
            entity_id,
            active_bar=active_bar,
            max_passes=max_passes,
            progression_override=progression_override,
            evaluation_cache=evaluation_cache,
        )
        if not self.permanent_pet_active:
            return result
        return replace(
            result,
            search_scope=(
                result.search_scope[0],
                "explicit permanent pet active for Sorcerer Expert Summoner; "
                "conditional Max Health is applied before healing coefficient evaluation",
                *result.search_scope[1:],
            ),
        )

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
        pet_context = self.expert_summoner_pet_context.resolve(
            factory=self.optimizer.context_factory,
            build=build,
            progression=candidate_progression,
            character_id=character_id,
            build_id=build_id,
            active_bar=active_bar,
            combat_state=combat_state,
            permanent_pet_active=self.permanent_pet_active,
        )
        context = pet_context.context

        healing_done_bonus, healing_done_sources, conditional_unresolved = (
            self._conditional_healing_done_inputs(
                build=build,
                progression=candidate_progression,
                entity_id=entity_id,
            )
        )
        event = self.healing_events.evaluate(
            build=build,
            context=context,
            entity_id=entity_id,
            target_health_fraction=self.target_health_fraction,
            additional_healing_done_bonus=healing_done_bonus,
            additional_healing_done_sources=healing_done_sources,
        )
        if conditional_unresolved:
            event = replace(
                event,
                unresolved=tuple(
                    dict.fromkeys((*event.unresolved, *conditional_unresolved))
                ),
            )
        event = self._templar_mending_event(
            build=build,
            progression=candidate_progression,
            event=event,
        )
        event = self._arcanist_cascading_fortune_event(
            build=build,
            event=event,
        )
        unresolved = (
            tuple(context.unresolved_gear_effects)
            + tuple(combat_unresolved)
            + tuple(pet_context.unresolved)
            + tuple(event.unresolved)
        )
        return event, tuple(dict.fromkeys(message for message in unresolved if message))
