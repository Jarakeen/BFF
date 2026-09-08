from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from engine.config import get_data_dir
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)
from services.extreme_healing_event_group_scoring_service import (
    ExtremeHealingEventGroupScoringService,
)
from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
    ExtremeHealingEventRecipientScopeResult,
)
from services.extreme_healing_event_service import (
    ExtremeHealingEventResult,
    ExtremeHealingEventService,
)
from services.extreme_healing_event_temporal_scope_service import (
    ExtremeHealingEventTemporalScopeResult,
    ExtremeHealingEventTemporalScopeService,
)


class _CanonicalIdentityRecipientScope:
    """Let canonical component identity own recipient separation during base math."""

    def resolve(self, *, ability_name: str) -> ExtremeHealingEventRecipientScopeResult:
        return ExtremeHealingEventRecipientScopeResult(
            single_recipient_safe=True,
            recipient_selection_required=False,
            unresolved=(),
        )


class _CanonicalIdentityTemporalScope:
    """Let canonical component identity own event-time separation during base math."""

    def resolve(self, *, ability_name: str) -> ExtremeHealingEventTemporalScopeResult:
        return ExtremeHealingEventTemporalScopeResult(
            single_instant_safe=True,
            component_time_selection_required=False,
            unresolved=(),
        )


class ExtremeCanonicalHealingEventService(ExtremeHealingEventService):
    """Score proven one-recipient, one-time HEAL events independently.

    The mature ``ExtremeHealingEventService`` remains authoritative for coefficient
    math, Healing Done, family/situational modifiers, Critical Healing, class
    passives, and the critical-healing cap. This adapter changes only the final
    event aggregation boundary.

    When every HEAL coefficient has reviewed recipient and event identity, the
    adapter reconstructs the already-calculated per-coefficient values and lets
    ``ExtremeHealingEventGroupScoringService`` select the largest legitimate
    event. Coefficients delivered to another recipient or at another time are not
    added together.

    The default tooltip path overlays reviewed U50 Dragon Blood-family component
    identity in memory. The persistent ``eso.db`` remains untouched. The existing
    reviewed ability-name recipient/time guards remain a compatibility fallback
    for skills whose canonical component identity has not yet been enriched or
    whose periodic tick identity is still unresolved.
    """

    def __init__(
        self,
        *,
        event_group_scoring: ExtremeHealingEventGroupScoringService | None = None,
        recipient_scope: ExtremeHealingEventRecipientScopeService | None = None,
        temporal_scope: ExtremeHealingEventTemporalScopeService | None = None,
        **kwargs,
    ) -> None:
        self.legacy_recipient_scope = (
            recipient_scope or ExtremeHealingEventRecipientScopeService()
        )
        self.legacy_temporal_scope = (
            temporal_scope or ExtremeHealingEventTemporalScopeService()
        )
        self.event_group_scoring = (
            event_group_scoring or ExtremeHealingEventGroupScoringService()
        )

        if kwargs.get("tooltip_service") is None:
            database_path = Path(
                kwargs.get("database_path") or get_data_dir() / "eso.db"
            )
            component_repository = ExtremeDragonBloodSkillComponentRepository(
                database_path
            )
            kwargs["tooltip_service"] = SavedBuildSkillTooltipService(
                database_path,
                component_repository=component_repository,
            )

        super().__init__(
            recipient_scope=_CanonicalIdentityRecipientScope(),
            temporal_scope=_CanonicalIdentityTemporalScope(),
            **kwargs,
        )

    @staticmethod
    def _component_values(event: ExtremeHealingEventResult) -> dict[int, float]:
        result = event.tooltip_result
        actual_by_number = {
            int(trace.coefficient_number): float(trace.output_value)
            for trace in tuple(getattr(result, "component_actual_effect_trace", ()) or ())
        }
        base_by_number = {
            int(trace.coefficient_number): float(trace.final_value)
            for trace in tuple(getattr(result, "components", ()) or ())
        }
        values: dict[int, float] = {}
        for number in event.heal_coefficient_numbers:
            if number in actual_by_number:
                values[number] = actual_by_number[number]
            elif number in base_by_number:
                values[number] = base_by_number[number]

        if not values or event.normal_heal is None:
            return values

        base_total = sum(float(value) for value in values.values())
        if abs(base_total) <= 1e-12:
            return values
        multiplier = float(event.normal_heal) / base_total
        return {
            number: float(value) * multiplier
            for number, value in values.items()
        }

    def _legacy_scope_fallback(
        self,
        *,
        event: ExtremeHealingEventResult,
        ability_name: str,
    ) -> ExtremeHealingEventResult:
        recipient = self.legacy_recipient_scope.resolve(ability_name=ability_name)
        temporal = self.legacy_temporal_scope.resolve(ability_name=ability_name)
        unresolved = tuple(
            dict.fromkeys(
                message
                for message in (
                    *event.unresolved,
                    *recipient.unresolved,
                    *temporal.unresolved,
                )
                if message
            )
        )
        if recipient.single_recipient_safe and temporal.single_instant_safe:
            return replace(event, unresolved=unresolved)
        return replace(
            event,
            normal_heal=None,
            critical_heal=None,
            unresolved=unresolved,
        )

    def evaluate(self, **kwargs) -> ExtremeHealingEventResult:
        event = super().evaluate(**kwargs)
        result = event.tooltip_result
        skill = getattr(result, "skill", None)
        ability_name = str(getattr(skill, "name", "") or "").strip()
        if skill is None:
            return event

        components = tuple(
            self.tooltip_service.components.get_for_skill_rank(skill.skill_rank_id)
        )
        identity = self.event_group_scoring.identity_service.resolve(components)
        if not identity.complete:
            return self._legacy_scope_fallback(
                event=event,
                ability_name=ability_name,
            )
        if not identity.groups:
            return event

        critical_multiplier = event.critical_multiplier
        if critical_multiplier is None:
            return replace(
                event,
                unresolved=tuple(
                    dict.fromkeys(
                        (*event.unresolved, "Canonical event grouping requires Critical Healing multiplier")
                    )
                ),
            )

        scoring = self.event_group_scoring.score(
            components=components,
            value_by_coefficient=self._component_values(event),
            critical_multiplier=float(critical_multiplier),
        )
        unresolved = tuple(
            dict.fromkeys((*event.unresolved, *scoring.unresolved))
        )
        return replace(
            event,
            normal_heal=scoring.largest_normal_heal,
            critical_heal=scoring.largest_critical_heal,
            unresolved=unresolved,
        )
