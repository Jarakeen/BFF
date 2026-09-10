from __future__ import annotations

from dataclasses import dataclass, replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult
from services.extreme_sorcerer_blood_magic_healing_event_service import (
    ExtremeSorcererBloodMagicHealingEventResult,
    ExtremeSorcererBloodMagicHealingEventService,
)
from services.extreme_sorcerer_blood_magic_service import ExtremeSorcererBloodMagicService


@dataclass(frozen=True)
class ExtremeConditionalHealingObjectiveEventResult(ExtremeHealingEventResult):
    """Selected heal plus any distinct runtime heal competing for MOST Actual Heal.

    ``critical_heal`` remains the critical value of the explicitly selected heal.
    The objective fields identify the largest eligible healing event instead of
    rewriting the selected event or summing heals that have different recipients.
    """

    blood_magic_event: ExtremeSorcererBloodMagicHealingEventResult | None = None
    objective_source: str = "selected_heal"
    objective_target: str = "selected_heal_recipient"
    objective_critical_heal: float | None = None


class ExtremeConditionalActualHealObjectiveOptimizationService(
    ExtremeConditionalActualHealOptimizationService
):
    """Rank distinct conditional healing events without collapsing recipients.

    The legacy conditional optimizer remains responsible for selected-skill math,
    transient combat-state rebuilding, and ordinary candidate generation. This
    specialization adds passive/proc healing events that are separate from the
    selected heal and compares their critical event sizes under the same rebuilt
    candidate context.

    Blood Magic's injured-caster branch is the first such alternate event. It is
    always caster-owned (``target='self'``), never added to the selected target
    heal, and may independently become the MOST Actual Heal objective winner.
    """

    BLOOD_MAGIC_PENDING_MESSAGE = (
        "Blood Magic Max-Health-scaled self-heal is resolved as a separate caster "
        "event but is not yet ranked against the selected target heal"
    )

    def __init__(
        self,
        *,
        blood_magic_healing_events: ExtremeSorcererBloodMagicHealingEventService | None = None,
        **kwargs,
    ) -> None:
        self.blood_magic_healing_events = (
            blood_magic_healing_events or ExtremeSorcererBloodMagicHealingEventService()
        )
        super().__init__(**kwargs)

    @staticmethod
    def _wrap_selected_event(
        selected: ExtremeHealingEventResult,
        *,
        blood_magic_event: ExtremeSorcererBloodMagicHealingEventResult | None = None,
    ) -> ExtremeConditionalHealingObjectiveEventResult:
        selected_score = selected.critical_heal
        objective_source = selected.entity_id
        objective_target = "selected_heal_recipient"
        objective_score = selected_score

        if (
            blood_magic_event is not None
            and blood_magic_event.critical_heal is not None
            and (
                objective_score is None
                or float(blood_magic_event.critical_heal) > float(objective_score) + 1e-9
            )
        ):
            objective_source = "Sorcerer: Blood Magic"
            objective_target = "self"
            objective_score = float(blood_magic_event.critical_heal)

        return ExtremeConditionalHealingObjectiveEventResult(
            entity_id=selected.entity_id,
            normal_heal=selected.normal_heal,
            critical_heal=selected.critical_heal,
            critical_healing_bonus=selected.critical_healing_bonus,
            critical_multiplier=selected.critical_multiplier,
            heal_coefficient_numbers=selected.heal_coefficient_numbers,
            crit_eligible_coefficient_numbers=selected.crit_eligible_coefficient_numbers,
            noncrit_coefficient_numbers=selected.noncrit_coefficient_numbers,
            tooltip_result=selected.tooltip_result,
            unresolved=selected.unresolved,
            blood_magic_event=blood_magic_event,
            objective_source=objective_source,
            objective_target=objective_target,
            objective_critical_heal=objective_score,
        )

    @staticmethod
    def _score(event: ExtremeHealingEventResult) -> float:
        if isinstance(event, ExtremeConditionalHealingObjectiveEventResult):
            if event.objective_critical_heal is None:
                raise ValueError(
                    f"Cannot optimize {event.entity_id!r}: conditional healing objective is unresolved"
                )
            return float(event.objective_critical_heal)
        return ExtremeConditionalActualHealOptimizationService._score(event)

    def _blood_magic_self_heal_event(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        active_bar: str,
    ) -> tuple[ExtremeSorcererBloodMagicHealingEventResult | None, tuple[str, ...]]:
        if self.blood_magic_caster_health_fraction is None:
            return None, ()
        if self.blood_magic_caster_health_fraction >= 1.0:
            return None, ()
        if self.blood_magic_trigger_ability_has_cost is None:
            return None, (
                "Blood Magic requires explicit proof that the triggering Dark Magic ability has a cost",
            )

        trigger_event, _snapshot_time = self._blood_magic_trigger_event()
        if trigger_event is None:
            return None, (
                "Blood Magic requires a runtime skill-cast event at or before the heal snapshot",
            )

        combat_state, combat_unresolved = self._restoration_combat_state(
            build=build,
            progression=progression,
            active_bar=active_bar,
        )
        context = self.optimizer.context_factory.build(
            character_id=character_id,
            build_id=f"{build_id}:blood-magic-self-heal",
            build=build,
            progression=progression,
            combat_state=combat_state,
            active_bar=active_bar,
        )

        branch_service = self.sorcerer_blood_magic
        if branch_service is None:
            branch_service = ExtremeSorcererBloodMagicService(
                getattr(self.optimizer, "database_path", None)
            )
            self.sorcerer_blood_magic = branch_service
        branch = branch_service.resolve(
            build=build,
            progression=progression,
            context=context,
            trigger_ability_name=trigger_event.source,
            trigger_ability_has_cost=self.blood_magic_trigger_ability_has_cost,
            caster_health_fraction=self.blood_magic_caster_health_fraction,
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *tuple(context.unresolved_gear_effects),
                    *tuple(combat_unresolved),
                    *tuple(branch.unresolved),
                )
            )
        )
        if unresolved or branch.branch != "self_heal" or branch.self_heal is None:
            return None, unresolved

        healing_event = self.blood_magic_healing_events.resolve(
            context=context,
            trigger_event=trigger_event,
            base_self_heal=float(branch.self_heal),
        )
        return healing_event, healing_event.unresolved

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
        selected, unresolved = super()._evaluate(
            build,
            progression=progression,
            character_id=character_id,
            build_id=build_id,
            entity_id=entity_id,
            active_bar=active_bar,
        )

        candidate_progression = replace(
            progression,
            attributes=AttributeAllocation(
                health=int(build.AttributeHealth or 0),
                magicka=int(build.AttributeMagicka or 0),
                stamina=int(build.AttributeStamina or 0),
            ),
        )
        blood_magic_event, blood_magic_unresolved = self._blood_magic_self_heal_event(
            build=build,
            progression=candidate_progression,
            character_id=character_id,
            build_id=build_id,
            active_bar=active_bar,
        )

        filtered = tuple(
            message
            for message in unresolved
            if message != self.BLOOD_MAGIC_PENDING_MESSAGE
        )
        combined = tuple(
            dict.fromkeys(
                message
                for message in (*filtered, *blood_magic_unresolved)
                if message
            )
        )
        wrapped = self._wrap_selected_event(
            replace(selected, unresolved=combined),
            blood_magic_event=blood_magic_event,
        )
        return wrapped, combined
