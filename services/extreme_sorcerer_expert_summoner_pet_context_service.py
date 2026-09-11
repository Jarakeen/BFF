from __future__ import annotations

from dataclasses import dataclass, replace

from minmax.base_character_state import PercentContribution
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.sorcerer_passive_input_resolver import SorcererPassiveInputResolver
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeSorcererExpertSummonerPetContextResult:
    context: BuildCalculationContext
    max_health_bonus_active: bool
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved


class ExtremeSorcererExpertSummonerPetContextService:
    """Rebuild canonical context for Expert Summoner's permanent-pet branch.

    Live U50 Expert Summoner always contributes its reviewed Max Magicka and Max
    Stamina percentage through ``SorcererPassiveInputResolver``. The additional
    Max Health percentage is conditional on a *permanent* pet being active.

    This service deliberately adds that conditional branch to the same additive
    primary-resource percentage bucket used by the ordinary context factory and
    then reruns canonical base/core calculation. It never multiplies an already
    finished Max Health value, which would be wrong when other percentage sources
    are present.
    """

    EXPERT_SUMMONER = "Expert Summoner"
    MAX_HEALTH_PERCENT = 0.05
    SOURCE = "Sorcerer: Expert Summoner (permanent pet)"

    @staticmethod
    def _dedupe(messages: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(message for message in messages if message))

    def _eligibility(
        self,
        *,
        factory: BuildCalculationContextFactory,
        build: PlayerBuild,
        progression: CharacterProgression,
    ) -> tuple[bool, tuple[str, ...]]:
        lines = SorcererPassiveInputResolver.equipped_sorcerer_line_ids(build)
        if SorcererPassiveInputResolver.DAEDRIC_SUMMONING_ID not in lines:
            return False, (
                "Expert Summoner permanent-pet scenario requires an equipped Daedric Summoning class line",
            )

        if progression.passive_ranks is None:
            return False, ("Expert Summoner passive rank is not recorded",)

        rank = progression.passive_rank(self.EXPERT_SUMMONER)
        if rank is None:
            return False, (
                "Passive rank is not recorded for character: Expert Summoner",
            )
        if rank == 0:
            return False, ()

        repository = factory.skill_line_repository
        if repository is None:
            return False, (
                "Expert Summoner max rank cannot be verified without skill repository",
            )
        maximum = repository.passive_max_rank(self.EXPERT_SUMMONER)
        if maximum is None:
            return False, (
                "Passive max rank is not available in canonical data: Expert Summoner",
            )
        if rank != maximum:
            return False, (
                f"Partial passive rank is not yet modeled: Expert Summoner {rank}/{maximum}",
            )
        return True, ()

    @staticmethod
    def _base_context(
        factory,
        *,
        build_kwargs: dict,
        gear_condition_context: frozenset[str] | None,
    ) -> BuildCalculationContext:
        if (
            gear_condition_context is not None
            and hasattr(factory, "gear_inputs_with_condition")
        ):
            build_kwargs = dict(build_kwargs)
            build_kwargs["gear_condition_context"] = gear_condition_context
        return factory.build(**build_kwargs)

    @staticmethod
    def _gear_inputs(
        factory,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        active_bar: str,
        base_context: BuildCalculationContext,
        gear_condition_context: frozenset[str] | None,
    ):
        if hasattr(factory, "gear_inputs_with_condition"):
            return factory.gear_inputs_with_condition(
                build,
                progression=progression,
                active_bar=active_bar,
                combat_state=base_context.combat_state,
                incoming_attack=base_context.incoming_attack,
                condition_context=gear_condition_context,
            )
        return factory._gear_inputs(
            build,
            progression=progression,
            active_bar=active_bar,
            combat_state=base_context.combat_state,
            incoming_attack=base_context.incoming_attack,
        )

    def resolve(
        self,
        *,
        factory: BuildCalculationContextFactory,
        build: PlayerBuild,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        active_bar: str = "front",
        combat_state=None,
        permanent_pet_active: bool,
        gear_condition_context: frozenset[str] | None = None,
    ) -> ExtremeSorcererExpertSummonerPetContextResult:
        build_kwargs = dict(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=progression,
            active_bar=active_bar,
        )
        if combat_state is not None:
            build_kwargs["combat_state"] = combat_state
        base_context = self._base_context(
            factory,
            build_kwargs=build_kwargs,
            gear_condition_context=gear_condition_context,
        )

        if not permanent_pet_active:
            return ExtremeSorcererExpertSummonerPetContextResult(
                context=base_context,
                max_health_bonus_active=False,
                unresolved=(),
            )

        eligible, eligibility_unresolved = self._eligibility(
            factory=factory,
            build=build,
            progression=progression,
        )
        if not eligible:
            return ExtremeSorcererExpertSummonerPetContextResult(
                context=base_context,
                max_health_bonus_active=False,
                unresolved=self._dedupe(eligibility_unresolved),
            )

        gear = self._gear_inputs(
            factory,
            build=build,
            progression=progression,
            active_bar=active_bar,
            base_context=base_context,
            gear_condition_context=gear_condition_context,
        )
        pet_health = PercentContribution(self.SOURCE, self.MAX_HEALTH_PERCENT)
        gear = replace(
            gear,
            health=replace(
                gear.health,
                skill_percent_contributions=(
                    *gear.health.skill_percent_contributions,
                    pet_health,
                ),
            ),
            applied_effect_count=gear.applied_effect_count + 1,
        )

        race_stats = factory._race_stats(build.Race)
        state = factory.calculator.calculate(
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
            base_character=state,
            race_stats=race_stats,
            inputs=gear.core,
        )
        adjusted = replace(
            base_context,
            character_state=state,
            core_state=core_state,
            gear_effects_applied=gear.applied_effect_count,
            unresolved_gear_effects=gear.unresolved,
        )
        return ExtremeSorcererExpertSummonerPetContextResult(
            context=adjusted,
            max_health_bonus_active=True,
            unresolved=(),
        )
