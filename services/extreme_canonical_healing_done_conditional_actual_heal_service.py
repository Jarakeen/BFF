from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult
from services.extreme_necromancer_living_death_healing_service import (
    ExtremeNecromancerLivingDeathHealingService,
)
from services.extreme_arcanist_curative_runeforms_healing_service import (
    ExtremeArcanistCurativeRuneformsHealingService,
)


class ExtremeCanonicalHealingDoneConditionalActualHealService(
    ExtremeConditionalActualHealOptimizationService
):
    """Route conditional generic Healing Done into the canonical additive bucket.

    The legacy conditional service still exposes its focused helper methods for
    compatibility tests, but production evaluation must not multiply generic
    Healing Done sources onto an already evaluated event. Curative Curse and
    Healing Tides therefore resolve before ``ExtremeHealingEventService`` and are
    passed as additional Healing Done into the same component bucket that already
    contains sheet/combat-state Healing Done, healing CP, Soul Siphoner, and the
    Restoring Tether family.
    """

    def _conditional_healing_done_inputs(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        entity_id: str,
    ) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
        bonus = 0.0
        sources: list[str] = []
        unresolved: list[str] = []

        if self.healer_has_negative_effect is not None:
            service = self.necromancer_living_death_healing
            if service is None:
                service = ExtremeNecromancerLivingDeathHealingService(
                    getattr(self.optimizer, "database_path", None)
                )
                self.necromancer_living_death_healing = service

            curse = service.resolve(
                build=build,
                progression=progression,
                has_negative_effect=self.healer_has_negative_effect,
            )
            curse_bonus = float(curse.multiplier) - 1.0
            bonus += curse_bonus
            unresolved.extend(curse.unresolved)
            if abs(curse_bonus) > 1e-12:
                sources.append("Necromancer: Curative Curse")

        if self.active_crux is not None:
            normalized_entity = str(entity_id or "").strip().replace("_", " ").casefold()
            if (
                self.active_crux > 0
                and normalized_entity in self.CRUX_CONSUMING_REMEDY_CASCADE_FAMILY
            ):
                unresolved.append(
                    "Healing Tides timing is unresolved for a Crux-consuming "
                    "Remedy Cascade-family cast; active Crux may be consumed "
                    "before the heal snapshots Healing Done"
                )
            else:
                service = self.arcanist_curative_runeforms_healing
                if service is None:
                    service = ExtremeArcanistCurativeRuneformsHealingService(
                        getattr(self.optimizer, "database_path", None)
                    )
                    self.arcanist_curative_runeforms_healing = service

                tides = service.resolve(
                    build=build,
                    progression=progression,
                    active_crux=self.active_crux,
                )
                tides_bonus = float(tides.multiplier) - 1.0
                bonus += tides_bonus
                unresolved.extend(tides.unresolved)
                if abs(tides_bonus) > 1e-12:
                    sources.append("Arcanist: Healing Tides")

        return (
            bonus,
            tuple(dict.fromkeys(source for source in sources if source)),
            tuple(dict.fromkeys(message for message in unresolved if message)),
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
        context = self.optimizer.context_factory.build(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=candidate_progression,
            combat_state=combat_state,
            active_bar=active_bar,
        )
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
            + tuple(event.unresolved)
        )
        return event, tuple(dict.fromkeys(message for message in unresolved if message))
