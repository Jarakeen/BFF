from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult
from services.extreme_nightblade_class_mastery_healing_service import (
    ExtremeNightbladeClassMasteryHealingService,
)
from services.extreme_nightblade_eye_for_exploitation_context_service import (
    ExtremeNightbladeEyeForExploitationContextService,
)


class ExtremeNightbladeConditionalActualHealService(
    ExtremeConditionalActualHealOptimizationService
):
    """Evaluate conditional Nightblade heals with target-health Class Mastery.

    ``An Eye for Exploitation`` is target-health dependent and therefore cannot
    live in the standing context. This adapter resolves the selected Nightblade
    Class Mastery choices for the explicit heal-target Health fraction, inserts
    Eye's flat Weapon/Spell Damage into the canonical power traces, and only then
    asks ``ExtremeHealingEventService`` to calculate the heal coefficient.

    ``Above and Beyond`` remains owned by ``ExtremeHealingEventService`` because
    that service already applies the selected mastery to crit-eligible HEAL
    components and enforces the raised Critical Healing cap. A pure Nightblade may
    therefore combine both reviewed mastery choices in one conditional event
    without either contribution being applied after the finished heal.
    """

    EYE_PENDING_BLOCKER = (
        "An Eye for Exploitation Weapon/Spell Damage contribution is not yet "
        "applied to the canonical heal coefficient context"
    )

    def __init__(
        self,
        *,
        nightblade_class_mastery_healing: (
            ExtremeNightbladeClassMasteryHealingService | None
        ) = None,
        eye_for_exploitation_context: (
            ExtremeNightbladeEyeForExploitationContextService | None
        ) = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.nightblade_class_mastery_healing = nightblade_class_mastery_healing
        self.eye_for_exploitation_context = (
            eye_for_exploitation_context
            or ExtremeNightbladeEyeForExploitationContextService()
        )

    def _mastery_context(
        self,
        *,
        build: PlayerBuild,
        context,
    ):
        service = self.nightblade_class_mastery_healing
        if service is None:
            service = ExtremeNightbladeClassMasteryHealingService(
                getattr(self.optimizer, "database_path", None)
            )
            self.nightblade_class_mastery_healing = service

        mastery = service.resolve(
            build=build,
            target_health_fraction=self.target_health_fraction,
            battle_spirit_active=False,
        )
        power_bonus = float(mastery.weapon_spell_damage_bonus)
        adjusted = self.eye_for_exploitation_context.apply(
            context,
            weapon_spell_damage_bonus=power_bonus,
        )
        return adjusted, tuple(mastery.unresolved), bool(power_bonus)

    @classmethod
    def _clear_proven_eye_blocker(
        cls,
        event: ExtremeHealingEventResult,
        *,
        eye_applied: bool,
    ) -> ExtremeHealingEventResult:
        if not eye_applied:
            return event
        unresolved = tuple(
            message
            for message in event.unresolved
            if cls.EYE_PENDING_BLOCKER not in str(message)
        )
        return replace(event, unresolved=unresolved)

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
        context, mastery_unresolved, eye_applied = self._mastery_context(
            build=build,
            context=context,
        )

        event = self.healing_events.evaluate(
            build=build,
            context=context,
            entity_id=entity_id,
            target_health_fraction=self.target_health_fraction,
        )
        event = self._clear_proven_eye_blocker(event, eye_applied=eye_applied)
        event = self._templar_mending_event(
            build=build,
            progression=candidate_progression,
            event=event,
        )
        event = self._necromancer_curative_curse_event(
            build=build,
            progression=candidate_progression,
            event=event,
        )
        event = self._arcanist_healing_tides_event(
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
            + tuple(mastery_unresolved)
            + tuple(event.unresolved)
        )
        return event, tuple(dict.fromkeys(message for message in unresolved if message))
