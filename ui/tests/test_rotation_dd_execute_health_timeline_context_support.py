from services.rotation_target_health_timeline_service import (
    RotationTargetHealthObservation,
    RotationTargetHealthTimeline,
)
from ui.rotation_dd_execute_health_timeline_context_support import (
    RotationDDExecuteHealthTimelineContextSupport,
)


class _DamageProvider:
    def evaluate_action(self, *args, **kwargs):
        raise AssertionError("not called by context adapter")


def test_context_adapter_preserves_target_and_damage_provider() -> None:
    provider = _DamageProvider()
    timeline = RotationTargetHealthTimeline(
        target_identity="boss",
        observations=(
            RotationTargetHealthObservation(
                time_seconds=42.0,
                target_identity="boss",
                current_health=240.0,
                maximum_health=1000.0,
            ),
        ),
    )
    support = RotationDDExecuteHealthTimelineContextSupport(
        timeline=timeline,
        action_damage_provider=provider,
    )

    context = support(
        build=object(),
        request=object(),
        generated=object(),
        routed_plan=object(),
    )

    assert context.target_identity == "boss"
    assert context.action_damage_provider is provider
    snapshot = context.snapshot_resolver(42.0)
    assert snapshot is not None
    assert snapshot.target("boss").health_fraction() == 0.24
    assert context.snapshot_resolver(43.0) is None
