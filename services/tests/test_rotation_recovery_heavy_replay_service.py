from types import SimpleNamespace

from minmax.healer_recovery_heavy_pressure import evaluate_healer_recovery_heavy_pressure
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import (
    AppliedResourceTimelineEvent,
    ResourceTimelineEventKind,
    ResourceTimelineResult,
)
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from minmax.rotation_wait_decision import PrematureRecastDecisionContext
from models.build_model import PlayerBuild
from services.rotation_recovery_heavy_replay_service import (
    RotationRecoveryHeavyReplayService,
)


class _FakeSustainService:
    def __init__(self) -> None:
        self.calls = []

    def evaluate(self, *, build, plan, resource, restoration_events=()):
        self.calls.append(tuple(restoration_events))
        current = 2500
        applied = []
        for event in sorted(restoration_events, key=lambda item: item.time_seconds):
            before = current
            current = min(10000, current + int(event.amount))
            applied.append(
                AppliedResourceTimelineEvent(
                    time_seconds=event.time_seconds,
                    kind=ResourceTimelineEventKind.RESTORATION,
                    source=event.source,
                    before=before,
                    attempted_change=int(event.amount),
                    applied_change=current - before,
                    after=current,
                )
            )
        timeline = ResourceTimelineResult(
            resource=resource,
            starting_amount=2500,
            ending_amount=current,
            events=tuple(applied),
        )
        return SimpleNamespace(run=SimpleNamespace(timeline=timeline))


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="Heavy Attack",
                bar="front",
            ),
            RotationAction(
                time_seconds=10.0,
                sequence=0,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="Heavy Attack",
                bar="front",
            ),
        ),
    )


def _context(time_seconds: float) -> PrematureRecastDecisionContext:
    slot = RotationAction(
        time_seconds=time_seconds,
        sequence=1,
        kind=RotationActionKind.SKILL,
        name="Long Buff",
        bar="front",
    )
    return PrematureRecastDecisionContext(
        time_seconds=time_seconds,
        bar="front",
        candidate=slot,
        slot=slot,
        next_due=(),
        rules=(RotationRecastRule("Long Buff", 20.0, bar="front"),),
        plan_end_seconds=20.0,
    )


def _restore_for_first_heavy(heavy):
    if heavy.time_seconds != 2.0:
        return None
    return ResourceRestorationEvent(
        time_seconds=3.8,
        resource=ResourceType.MAGICKA,
        amount=4000,
        source="Verified Restoration Staff heavy",
    )


def test_verified_heavy_restore_is_replayed_before_later_recovery_pressure() -> None:
    sustain = _FakeSustainService()
    service = RotationRecoveryHeavyReplayService(sustain_service=sustain)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")

    replay = service.replay(
        build=build,
        plan=_plan(),
        resource=ResourceType.MAGICKA,
        restoration_resolver=_restore_for_first_heavy,
    )

    initial_pressure = evaluate_healer_recovery_heavy_pressure(
        timeline=replay.initial_projection.run.timeline,
        time_seconds=10.0,
        maximum_amount=10000,
        trigger_fraction=0.30,
    )
    replayed_pressure = evaluate_healer_recovery_heavy_pressure(
        timeline=replay.final_projection.run.timeline,
        time_seconds=10.0,
        maximum_amount=10000,
        trigger_fraction=0.30,
    )

    assert initial_pressure.recommended is True
    assert initial_pressure.current_amount == 2500
    assert replayed_pressure.recommended is False
    assert replayed_pressure.current_amount == 6500
    assert replay.restoration_events[0].time_seconds == 3.8
    assert len(replay.steps) == 1
    assert sustain.calls == [(), (replay.restoration_events[0],)]


def test_replayed_pressure_resolver_feeds_updated_resource_state_back_to_generation() -> None:
    service = RotationRecoveryHeavyReplayService(sustain_service=_FakeSustainService())
    replay = service.replay(
        build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        plan=_plan(),
        resource=ResourceType.MAGICKA,
        restoration_resolver=_restore_for_first_heavy,
    )

    resolver = service.pressure_resolver(
        replay=replay,
        maximum_amount=10000,
        trigger_fraction=0.30,
    )
    pressure = resolver(_context(10.0))

    assert pressure.current_amount == 6500
    assert pressure.resource_fraction == 0.65
    assert pressure.recommended is False
    assert "above the 30.0% recovery trigger" in pressure.reason


def test_replay_rejects_restore_before_scheduled_heavy_starts() -> None:
    sustain = _FakeSustainService()
    service = RotationRecoveryHeavyReplayService(sustain_service=sustain)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")

    def invalid_restore(heavy):
        return ResourceRestorationEvent(
            time_seconds=1.0,
            resource=ResourceType.MAGICKA,
            amount=4000,
            source="Invalid early restore",
        )

    try:
        service.replay(
            build=build,
            plan=_plan(),
            resource=ResourceType.MAGICKA,
            restoration_resolver=invalid_restore,
        )
    except ValueError as exc:
        assert "before the scheduled heavy starts" in str(exc)
    else:
        raise AssertionError("Expected invalid recovery-heavy restore timing to fail")
