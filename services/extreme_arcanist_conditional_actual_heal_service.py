from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation
from minmax.stat_ids import StatId
from services.extreme_arcanist_curative_surge_channel_service import (
    ExtremeArcanistCurativeSurgeChannelService,
)
from services.extreme_arcanist_fated_fortune_critical_healing_service import (
    ExtremeArcanistFatedFortuneCriticalHealingService,
)
from services.extreme_arcanist_harnessed_quintessence_context_service import (
    ExtremeArcanistHarnessedQuintessenceContextService,
)
from services.extreme_arcanist_harnessed_quintessence_service import (
    ExtremeArcanistHarnessedQuintessenceService,
)
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult


class ExtremeArcanistConditionalActualHealService(
    ExtremeConditionalActualHealOptimizationService
):
    """Apply reviewed Arcanist conditional heal boundaries.

    Curative Surge keeps its reviewed aggregate HEAL coefficient value, but the
    2.92x end-of-channel scale is never applied to the whole channel because tick
    timing is not yet represented.

    Reviewed U50 Fated Fortune may add 12% Critical Healing when the caller
    explicitly states that its seven-second buff window is already active. The
    bonus is injected into canonical ``CRITICAL_HEALING`` before the healing event
    is evaluated so mixed crit-eligible/non-crittable components retain their
    existing semantics. A Crux-consuming heal does not self-award a newly
    triggered Fated Fortune window on the same event until event ordering is
    proven.

    Reviewed U50 Harnessed Quintessence may add rank-aware flat Weapon and Spell
    Damage when the caller explicitly proves that its ten-second post-resource-
    restoration window is active. The flat power is inserted before canonical
    percentage multipliers so power-scaled healing coefficients preserve ESO
    stacking order.
    """

    def __init__(
        self,
        *,
        arcanist_curative_surge_channel: ExtremeArcanistCurativeSurgeChannelService | None = None,
        arcanist_fated_fortune_critical_healing: ExtremeArcanistFatedFortuneCriticalHealingService | None = None,
        arcanist_harnessed_quintessence: ExtremeArcanistHarnessedQuintessenceService | None = None,
        arcanist_harnessed_quintessence_context: ExtremeArcanistHarnessedQuintessenceContextService | None = None,
        fated_fortune_active: bool | None = None,
        harnessed_quintessence_active: bool | None = None,
        **kwargs,
    ) -> None:
        if fated_fortune_active is not None and not isinstance(fated_fortune_active, bool):
            raise ValueError("fated_fortune_active must be True, False, or None")
        if harnessed_quintessence_active is not None and not isinstance(
            harnessed_quintessence_active, bool
        ):
            raise ValueError(
                "harnessed_quintessence_active must be True, False, or None"
            )
        self.arcanist_curative_surge_channel = arcanist_curative_surge_channel
        self.arcanist_fated_fortune_critical_healing = arcanist_fated_fortune_critical_healing
        self.arcanist_harnessed_quintessence = arcanist_harnessed_quintessence
        self.arcanist_harnessed_quintessence_context = (
            arcanist_harnessed_quintessence_context
            or ExtremeArcanistHarnessedQuintessenceContextService()
        )
        self.fated_fortune_active = fated_fortune_active
        self.harnessed_quintessence_active = harnessed_quintessence_active
        super().__init__(**kwargs)

    def optimize(self, baseline_build, entity_id, **kwargs):
        result = super().optimize(baseline_build, entity_id, **kwargs)
        scenarios: list[str] = []
        if self.fated_fortune_active is not None:
            scenarios.append(
                "explicit Fated Fortune active buff-window state "
                f"{str(self.fated_fortune_active).casefold()}; "
                "Critical Healing requires canonical Herald of the Tome legality proof"
            )
        if self.harnessed_quintessence_active is not None:
            scenarios.append(
                "explicit Harnessed Quintessence active buff-window state "
                f"{str(self.harnessed_quintessence_active).casefold()}; "
                "Weapon/Spell Damage requires canonical Herald of the Tome legality proof"
            )
        if not scenarios:
            return result
        return replace(result, search_scope=(*scenarios, *result.search_scope))

    def _harnessed_quintessence_context(self, *, build, progression, context):
        if self.harnessed_quintessence_active is None:
            return context, ()

        service = self.arcanist_harnessed_quintessence
        if service is None:
            service = ExtremeArcanistHarnessedQuintessenceService(
                getattr(self.optimizer, "database_path", None)
            )
            self.arcanist_harnessed_quintessence = service
        resolved = service.resolve(
            build=build,
            progression=progression,
            harnessed_quintessence_active=self.harnessed_quintessence_active,
        )
        bonus = float(resolved.weapon_spell_damage_bonus)
        if not bonus:
            return context, resolved.unresolved

        adjusted = self.arcanist_harnessed_quintessence_context.apply(
            context,
            weapon_spell_damage_bonus=bonus,
        )
        return adjusted, resolved.unresolved

    def _fated_fortune_context(self, *, build, progression, context):
        if self.fated_fortune_active is None:
            return context, ()

        service = self.arcanist_fated_fortune_critical_healing
        if service is None:
            service = ExtremeArcanistFatedFortuneCriticalHealingService(
                getattr(self.optimizer, "database_path", None)
            )
            self.arcanist_fated_fortune_critical_healing = service
        fortune = service.resolve(
            build=build,
            progression=progression,
            fated_fortune_active=self.fated_fortune_active,
        )
        if not fortune.critical_healing_bonus:
            return context, fortune.unresolved

        core_state = getattr(context, "core_state", None)
        if core_state is None:
            return context, (*fortune.unresolved, "Fated Fortune requires canonical core_state")
        trace = core_state.derived.get(StatId.CRITICAL_HEALING)
        if trace is None:
            return context, (*fortune.unresolved, "Canonical Critical Healing stat is unavailable")

        bonus = float(fortune.critical_healing_bonus)
        final_value = float(trace.final_value) + bonus
        steps = list(trace.steps)
        steps.append(("Arcanist: Fated Fortune", "add", bonus, final_value))
        updated_trace = replace(
            trace,
            steps=steps,
            raw_value=float(trace.raw_value) + bonus,
            final_value=final_value,
        )
        updated_core = replace(
            core_state,
            derived={**core_state.derived, StatId.CRITICAL_HEALING: updated_trace},
        )
        return replace(context, core_state=updated_core), fortune.unresolved

    def _fated_fortune_same_event_boundary(self, event: ExtremeHealingEventResult) -> ExtremeHealingEventResult:
        if self.fated_fortune_active is not False or not self.active_crux:
            return event
        tooltip_result = getattr(event, "tooltip_result", None)
        skill = getattr(tooltip_result, "skill", None)
        skill_name = str(getattr(skill, "name", "") or "").strip().casefold()
        if skill_name not in self.CRUX_CONSUMING_REMEDY_CASCADE_FAMILY:
            return event
        unresolved = tuple(
            dict.fromkeys(
                (
                    *event.unresolved,
                    "Fated Fortune same-event timing is unresolved for a Crux-consuming "
                    "Remedy Cascade-family cast; the critical-healing window may begin "
                    "after the heal snapshots its critical magnitude",
                )
            )
        )
        return replace(event, unresolved=unresolved)

    def _curative_surge_channel_event(
        self,
        *,
        build,
        event: ExtremeHealingEventResult,
    ) -> ExtremeHealingEventResult:
        tooltip_result = getattr(event, "tooltip_result", None)
        skill = getattr(tooltip_result, "skill", None)
        skill_name = str(getattr(skill, "name", "") or "").strip()
        if not skill_name:
            return event

        service = self.arcanist_curative_surge_channel
        if service is None:
            service = ExtremeArcanistCurativeSurgeChannelService()
            self.arcanist_curative_surge_channel = service
        channel = service.resolve(build=build, ability_name=skill_name)
        if not channel.applies:
            return event

        unresolved = tuple(
            dict.fromkeys((*event.unresolved, *channel.unresolved))
        )
        return replace(event, unresolved=unresolved)

    def _evaluate(
        self,
        build,
        *,
        progression,
        character_id,
        build_id,
        entity_id,
        active_bar,
    ):
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
        context, harnessed_unresolved = self._harnessed_quintessence_context(
            build=build,
            progression=candidate_progression,
            context=context,
        )
        context, fortune_unresolved = self._fated_fortune_context(
            build=build,
            progression=candidate_progression,
            context=context,
        )
        event = self.healing_events.evaluate(
            build=build,
            context=context,
            entity_id=entity_id,
            target_health_fraction=self.target_health_fraction,
        )
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
        event = self._fated_fortune_same_event_boundary(event)
        event = self._curative_surge_channel_event(build=build, event=event)
        unresolved = (
            tuple(context.unresolved_gear_effects)
            + tuple(combat_unresolved)
            + tuple(harnessed_unresolved)
            + tuple(fortune_unresolved)
            + tuple(event.unresolved)
        )
        return event, tuple(dict.fromkeys(message for message in unresolved if message))
