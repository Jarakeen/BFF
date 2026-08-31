from minmax.conditional_recovery import create_enlivening_overflow_modifier
from minmax.recovery_timing import (
    RecoveryActivityState,
    resolve_in_combat_recovery_tick,
    schedule_in_combat_recovery_ticks,
)
from minmax.resource_costs import ResourceType
from minmax.resource_state import StaticResourcePool


def _pool(resource: ResourceType, recovery: int = 1000) -> StaticResourcePool:
    return StaticResourcePool(
        resource=resource,
        maximum=30000,
        displayed_recovery=recovery,
    )


def test_enlivening_overflow_applies_only_to_ticks_inside_active_window() -> None:
    modifier = create_enlivening_overflow_modifier(
        max_magicka=30000,
        triggered_at_seconds=1.0,
    )

    scheduled = schedule_in_combat_recovery_ticks(
        _pool(ResourceType.MAGICKA),
        duration_seconds=8.0,
        recovery_modifiers=(modifier,),
    )

    assert [event.time_seconds for event in scheduled] == [2.0, 4.0, 6.0, 8.0]
    assert [event.tick.additive_recovery_bonus for event in scheduled] == [150, 150, 150, 0]
    assert [event.tick.effective_recovery for event in scheduled] == [1150, 1150, 1150, 1000]
    assert [event.tick.restored_amount for event in scheduled] == [1150, 1150, 1150, 1000]


def test_enlivening_overflow_affects_all_three_primary_recovery_types() -> None:
    modifier = create_enlivening_overflow_modifier(
        max_magicka=30000,
        triggered_at_seconds=0.0,
    )

    for resource in (ResourceType.HEALTH, ResourceType.MAGICKA, ResourceType.STAMINA):
        event = schedule_in_combat_recovery_ticks(
            _pool(resource, recovery=900),
            duration_seconds=2.0,
            recovery_modifiers=(modifier,),
        )[0]
        assert event.tick.additive_recovery_bonus == 150
        assert event.tick.effective_recovery == 1050


def test_stamina_suppression_happens_after_temporary_recovery_bonus() -> None:
    modifier = create_enlivening_overflow_modifier(
        max_magicka=30000,
        triggered_at_seconds=0.0,
    )
    event = schedule_in_combat_recovery_ticks(
        _pool(ResourceType.STAMINA, recovery=1000),
        duration_seconds=2.0,
        activity_at=lambda _time: RecoveryActivityState(blocking=True),
        recovery_modifiers=(modifier,),
    )[0]

    assert event.tick.additive_recovery_bonus == 150
    assert event.tick.effective_recovery == 1150
    assert event.tick.suppressed
    assert event.tick.restored_amount == 0


def test_direct_recovery_tick_rejects_negative_temporary_bonus() -> None:
    try:
        resolve_in_combat_recovery_tick(
            _pool(ResourceType.MAGICKA),
            additive_recovery_bonus=-1,
        )
    except ValueError as exc:
        assert "cannot be negative" in str(exc)
    else:
        raise AssertionError("Expected negative temporary recovery bonus to be rejected")
