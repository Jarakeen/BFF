from __future__ import annotations

from dataclasses import replace

from services.extreme_arcanist_curative_surge_channel_service import (
    ExtremeArcanistCurativeSurgeChannelService,
)
from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult


class ExtremeArcanistConditionalActualHealService(
    ExtremeConditionalActualHealOptimizationService
):
    """Preserve Curative Surge's unresolved whole-channel boundary.

    The base conditional optimizer can still evaluate the reviewed aggregate HEAL
    coefficient value, but Curative Surge must remain mechanically incomplete
    until tick cadence and per-tick channel scaling are represented. The reviewed
    2.92x value belongs only to the end of the channel and is therefore never
    applied to the aggregate event here.
    """

    def __init__(
        self,
        *,
        arcanist_curative_surge_channel: ExtremeArcanistCurativeSurgeChannelService | None = None,
        **kwargs,
    ) -> None:
        self.arcanist_curative_surge_channel = arcanist_curative_surge_channel
        super().__init__(**kwargs)

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

    def _evaluate(self, build, **kwargs):
        event, unresolved = super()._evaluate(build, **kwargs)
        event = self._curative_surge_channel_event(build=build, event=event)
        combined = tuple(
            dict.fromkeys((*unresolved, *event.unresolved))
        )
        return event, combined
