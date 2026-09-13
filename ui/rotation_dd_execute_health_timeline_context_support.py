from __future__ import annotations

"""Adapt an explicit target-Health timeline into the DD execute Generate context."""

from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageEvidenceProvider,
)
from services.rotation_target_health_timeline_service import (
    RotationTargetHealthTimeline,
    RotationTargetHealthTimelineService,
)
from ui.rotation_dd_execute_generation_context import RotationDDExecuteGenerationContext


class RotationDDExecuteHealthTimelineContextSupport:
    def __init__(
        self,
        *,
        timeline: RotationTargetHealthTimeline,
        action_damage_provider: RotationActionDamageEvidenceProvider,
        timeline_service: RotationTargetHealthTimelineService | None = None,
    ) -> None:
        self.timeline = timeline
        self.action_damage_provider = action_damage_provider
        self.timeline_service = timeline_service or RotationTargetHealthTimelineService()

    def resolve(self, *, build, request, generated, routed_plan) -> RotationDDExecuteGenerationContext:
        del build, request, generated, routed_plan
        return RotationDDExecuteGenerationContext(
            snapshot_resolver=self.timeline_service.snapshot_resolver(self.timeline),
            target_identity=self.timeline.target_identity,
            action_damage_provider=self.action_damage_provider,
        )

    def __call__(self, *, build, request, generated, routed_plan) -> RotationDDExecuteGenerationContext:
        return self.resolve(
            build=build,
            request=request,
            generated=generated,
            routed_plan=routed_plan,
        )


__all__ = ["RotationDDExecuteHealthTimelineContextSupport"]
