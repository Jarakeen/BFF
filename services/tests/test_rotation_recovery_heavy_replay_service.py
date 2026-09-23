from dataclasses import dataclass
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


class _PotionRuntimeService:
    def __init__(self, events=(), unresolved=()):
        self.events = tuple(events)
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve_restoration_events(self, build, *, plan):
        self.calls.append((build, plan))
        return SimpleNamespace(events=self.events, unresolved=self.unresolved)


@dataclass(frozen=True)
class _Projection:
    run: object
    unresolved: tuple[str, ...] = ()


class _FakeSustainService:
    def __init__(self) -> None:
        self.calls = []

    def evaluate(
        self,
        *,
        build,
        plan,
        resource,
        restoration_events=(),
        maximum_events=(),
        calculation_context=None,
        displayed_recovery_at=None,
    ):
        self.calls.append(
            {
                "restoration_events": tuple(restoration_events),
                "maximum_events": tuple(maximum_events),
                "calculation_context": calculation_context,
                "displayed_recovery_at": displayed_recovery_at,
            }
        )
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
        return _Projection(run=SimpleNamespace(timeline=timeline))


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
    assert [call["restoration_events"] for call in sustain.calls] == [
        (),
        (replay.restoration_events[0],),
    ]


def test_replay_forwards_time_aware_recovery_to_every_sustain_pass() -> None:
    sustain = _FakeSustainService()
    service = RotationRecoveryHeavyReplayService(sustain_service=sustain)
    recovery_at = lambda time_seconds: 1800 if time_seconds < 4.0 else 2050
    context = object()

    service.replay(
        build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        plan=_plan(),
        resource=ResourceType.MAGICKA,
        restoration_resolver=_restore_for_first_heavy,
        calculation_context=context,
        displayed_recovery_at=recovery_at,
    )

    assert len(sustain.calls) == 2
    assert all(call["calculation_context"] is context for call in sustain.calls)
    assert all(call["displayed_recovery_at"] is recovery_at for call in sustain.calls)


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


def test_anticipatory_pressure_uses_earlier_legal_window_before_later_shortfall() -> None:
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=10000,
        ending_amount=0,
        starting_maximum=10000,
        ending_maximum=10000,
        events=(
            AppliedResourceTimelineEvent(
                time_seconds=4.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="early heal",
                before=10000,
                attempted_change=-1000,
                applied_change=-1000,
                after=9000,
                maximum_before=10000,
                maximum_after=10000,
            ),
            AppliedResourceTimelineEvent(
                time_seconds=12.0,
                kind=ResourceTimelineEventKind.ACTION_COST,
                source="later burst heal",
                before=9000,
                attempted_change=-10000,
                applied_change=-9000,
                after=0,
                shortfall=1000,
                maximum_before=10000,
                maximum_after=10000,
            ),
        ),
    )
    replay = SimpleNamespace(
        final_projection=SimpleNamespace(run=SimpleNamespace(timeline=timeline))
    )

    resolver = RotationRecoveryHeavyReplayService.pressure_resolver(
        replay=replay,
        maximum_amount=10000,
        trigger_fraction=0.20,
        anticipate_future_shortfall=True,
    )
    pressure = resolver(_context(4.0))

    assert pressure.current_amount == 10000
    assert pressure.resource_fraction == 1.0
    assert pressure.reserve_shortfall == 1000
    assert pressure.recommended is True
    assert "later shortfall of 1000" in pressure.reason


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


def test_recovery_heavy_replay_preserves_scheduled_potion_restoration() -> None:
    sustain = _FakeSustainService()
    potion = ResourceRestorationEvent(
        time_seconds=1.0,
        resource=ResourceType.MAGICKA,
        amount=1000,
        source="Scheduled potion",
    )
    potion_runtime = _PotionRuntimeService((potion,))
    service = RotationRecoveryHeavyReplayService(
        sustain_service=sustain,
        potion_runtime_service=potion_runtime,
    )
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")

    replay = service.replay(
        build=build,
        plan=_plan(),
        resource=ResourceType.MAGICKA,
        restoration_resolver=_restore_for_first_heavy,
    )

    assert sustain.calls[0]["restoration_events"] == (potion,)
    assert sustain.calls[1]["restoration_events"] == (potion, replay.restoration_events[0])
    assert potion_runtime.calls == [(build, _plan())]



def test_unresolved_potion_restore_evidence_survives_heavy_replay() -> None:
    sustain = _FakeSustainService()
    potion = _PotionRuntimeService(
        unresolved=("scheduled potion restoration magnitude unresolved",)
    )
    service = RotationRecoveryHeavyReplayService(
        sustain_service=sustain,
        potion_runtime_service=potion,
    )

    replay = service.replay(
        build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        plan=_plan(),
        resource=ResourceType.MAGICKA,
        restoration_resolver=_restore_for_first_heavy,
    )

    assert "scheduled potion restoration magnitude unresolved" in replay.initial_projection.unresolved
    assert "scheduled potion restoration magnitude unresolved" in replay.final_projection.unresolved
