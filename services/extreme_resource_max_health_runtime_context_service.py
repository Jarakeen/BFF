from __future__ import annotations

"""Canonical context bridge for reviewed Extreme Max Health runtime states.

This service owns no independent ESO percentages. Expert Summoner delegates to the
existing permanent-pet context service. Nothing Wasted consumes the reviewed
ClassMasteryExtremeEffectService contribution and inserts it into the same additive
primary-resource percentage bucket before canonical resource/core recalculation.
"""

from dataclasses import replace

from minmax.base_character_state import PercentContribution
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from models.build_model import PlayerBuild
from services.class_mastery_extreme_effect_service import ClassMasteryExtremeEffectService
from services.class_mastery_repository import ClassMasteryRepository
from services.extreme_resource_max_health_runtime_state_service import (
    ExtremeResourceMaxHealthRuntimeState,
)
from services.extreme_sorcerer_expert_summoner_pet_context_service import (
    ExtremeSorcererExpertSummonerPetContextService,
)


class ExtremeResourceMaxHealthRuntimeContextService:
    """Rebuild canonical Max Health context for one reviewed runtime witness."""

    NOTHING_WASTED_SOURCE = "Class Mastery: Nothing Wasted (10 stacks)"

    def __init__(
        self,
        *,
        mastery_repository: ClassMasteryRepository,
        expert_summoner_service: ExtremeSorcererExpertSummonerPetContextService | None = None,
    ) -> None:
        self.mastery_repository = mastery_repository
        self.expert_summoner_service = (
            expert_summoner_service or ExtremeSorcererExpertSummonerPetContextService()
        )

    @staticmethod
    def _base_context(
        *,
        factory: BuildCalculationContextFactory,
        build: PlayerBuild,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        active_bar: str,
        combat_state,
    ) -> BuildCalculationContext:
        kwargs = dict(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=progression,
            active_bar=active_bar,
        )
        if combat_state is not None:
            kwargs["combat_state"] = combat_state
        return factory.build(**kwargs)

    def _nothing_wasted_percent(self, state: ExtremeResourceMaxHealthRuntimeState) -> float:
        if state.nothing_wasted_stacks <= 0:
            return 0.0
        if state.nothing_wasted_stacks != 10:
            raise ValueError("Only the reviewed 10-stack Nothing Wasted runtime state is supported")
        ids = set(int(value) for value in state.class_mastery_ability_ids if int(value) > 0)
        rows = tuple(
            row
            for row in self.mastery_repository.for_class("Necromancer")
            if row.name.strip().casefold() == "nothing wasted"
            and int(row.base_ability_id) in ids
        )
        if len(rows) != 1:
            raise ValueError("Nothing Wasted runtime state lacks unique canonical mastery evidence")
        contributions = tuple(
            row
            for row in ClassMasteryExtremeEffectService.contributions(rows[0])
            if row.objective_key == "max_health"
        )
        if len(contributions) != 1 or contributions[0].percent <= 0.0:
            raise ValueError("Nothing Wasted Max Health contribution is not reviewed")
        return float(contributions[0].percent)

    def resolve(
        self,
        *,
        factory: BuildCalculationContextFactory,
        build: PlayerBuild,
        progression: CharacterProgression,
        state: ExtremeResourceMaxHealthRuntimeState,
        character_id: str,
        build_id: str,
        active_bar: str = "front",
        combat_state=None,
    ) -> BuildCalculationContext:
        if state.permanent_pet_active:
            result = self.expert_summoner_service.resolve(
                factory=factory,
                build=build,
                progression=progression,
                character_id=character_id,
                build_id=build_id,
                active_bar=active_bar,
                combat_state=combat_state,
                permanent_pet_active=True,
            )
            if result.unresolved:
                raise ValueError("; ".join(result.unresolved))
            return result.context

        percent = self._nothing_wasted_percent(state)
        if percent <= 0.0:
            return self._base_context(
                factory=factory,
                build=build,
                progression=progression,
                character_id=character_id,
                build_id=build_id,
                active_bar=active_bar,
                combat_state=combat_state,
            )

        base_context = self._base_context(
            factory=factory,
            build=build,
            progression=progression,
            character_id=character_id,
            build_id=build_id,
            active_bar=active_bar,
            combat_state=combat_state,
        )
        gear = factory._gear_inputs(
            build,
            progression=progression,
            active_bar=active_bar,
            combat_state=base_context.combat_state,
            incoming_attack=base_context.incoming_attack,
        )
        source = PercentContribution(self.NOTHING_WASTED_SOURCE, percent)
        gear = replace(
            gear,
            health=replace(
                gear.health,
                skill_percent_contributions=(
                    *gear.health.skill_percent_contributions,
                    source,
                ),
            ),
            applied_effect_count=gear.applied_effect_count + 1,
        )

        race_stats = factory._race_stats(build.Race)
        character_state = factory.calculator.calculate(
            attributes=progression.attributes,
            race_stats=race_stats,
            health=gear.health,
            magicka=gear.magicka,
            stamina=gear.stamina,
            health_recovery=gear.health_recovery,
            magicka_recovery=gear.magicka_recovery,
            stamina_recovery=gear.stamina_recovery,
        )
        core_state = factory.core_calculator.calculate(
            character_progression=progression,
            base_character=character_state,
            race_stats=race_stats,
            inputs=gear.core,
        )
        return replace(
            base_context,
            character_state=character_state,
            core_state=core_state,
            gear_effects_applied=gear.applied_effect_count,
            unresolved_gear_effects=gear.unresolved,
        )
