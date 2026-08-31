from minmax.recovery_timing import (
    IN_COMBAT_RECOVERY_INTERVAL_SECONDS,
    RecoveryActivityState,
    resolve_in_combat_recovery_tick,
    schedule_in_combat_recovery_ticks,
)
from minmax.resource_costs import ResourceType
from minmax.resource_state import StaticResourcePool


def _pool(resource: ResourceType, recovery: int = 1800) -> StaticResourcePool:
    return StaticResourcePool(
        resource=resource,
        maximum=30000,
        displayed_recovery=recovery,
    )


def test_in_combat_recovery_tick_uses_character_sheet_amount_every_two_seconds() -> None:
    tick = resolve_in_combat_recovery_tick(_pool(ResourceType.MAGICKA, 1842))

    assert IN_COMBAT_RECOVERY_INTERVAL_SECONDS == 2.0
    assert tick.interval_seconds == 2.0
    assert tick.displayed_recovery == 1842
    assert tick.restored_amount == 1842
    assert not tick.suppressed


def test_blocking_suppresses_stamina_recovery_tick_only() -> None:
    activity = RecoveryActivityState(blocking=True)

    stamina = resolve_in_combat_recovery_tick(_pool(ResourceType.STAMINA), activity)
    magicka = resolve_in_combat_recovery_tick(_pool(ResourceType.MAGICKA), activity)
    health = resolve_in_combat_recovery_tick(_pool(ResourceType.HEALTH), activity)

    assert stamina.suppressed
    assert stamina.restored_amount == 0
    assert magicka.restored_amount == 1800
    assert health.restored_amount == 1800


def test_sprinting_suppresses_stamina_recovery_tick() -> None:
    tick = resolve_in_combat_recovery_tick(
        _pool(ResourceType.STAMINA, 1600),
        RecoveryActivityState(sprinting=True),
    )

    assert tick.suppressed
    assert tick.restored_amount == 0


def test_sneaking_suppresses_stamina_recovery_tick() -> None:
    tick = resolve_in_combat_recovery_tick(
        _pool(ResourceType.STAMINA, 1600),
        RecoveryActivityState(sneaking=True),
    )

    assert tick.suppressed
    assert tick.restored_amount == 0


def test_unsuppressed_stamina_recovers_full_displayed_value() -> None:
    tick = resolve_in_combat_recovery_tick(_pool(ResourceType.STAMINA, 1574))

    assert not tick.suppressed
    assert tick.restored_amount == 1574


def test_recovery_schedule_starts_at_two_seconds_and_includes_window_boundary() -> None:
    scheduled = schedule_in_combat_recovery_ticks(
        _pool(ResourceType.MAGICKA, 1200),
        duration_seconds=6.0,
    )

    assert [event.time_seconds for event in scheduled] == [2.0, 4.0, 6.0]
    assert [event.tick.restored_amount for event in scheduled] == [1200, 1200, 1200]


def test_recovery_schedule_evaluates_stamina_suppression_at_each_tick() -> None:
    def activity_at(time_seconds: float) -> RecoveryActivityState:
        if time_seconds == 4.0:
            return RecoveryActivityState(blocking=True)
        if time_seconds == 6.0:
            return RecoveryActivityState(sprinting=True)
        return RecoveryActivityState()

    scheduled = schedule_in_combat_recovery_ticks(
        _pool(ResourceType.STAMINA, 1500),
        duration_seconds=8.0,
        activity_at=activity_at,
    )

    assert [event.time_seconds for event in scheduled] == [2.0, 4.0, 6.0, 8.0]
    assert [event.tick.suppressed for event in scheduled] == [False, True, True, False]
    assert [event.tick.restored_amount for event in scheduled] == [1500, 0, 0, 1500]


def test_recovery_schedule_accepts_explicit_first_tick_phase() -> None:
    scheduled = schedule_in_combat_recovery_ticks(
        _pool(ResourceType.HEALTH, 900),
        duration_seconds=5.5,
        first_tick_seconds=1.5,
    )

    assert [event.time_seconds for event in scheduled] == [1.5, 3.5, 5.5]


def test_recovery_schedule_rejects_invalid_time_window() -> None:
    pool = _pool(ResourceType.MAGICKA)

    try:
        schedule_in_combat_recovery_ticks(pool, duration_seconds=-1.0)
    except ValueError as exc:
        assert "duration cannot be negative" in str(exc)
    else:
        raise AssertionError("Expected negative duration to be rejected")

    try:
        schedule_in_combat_recovery_ticks(pool, duration_seconds=4.0, first_tick_seconds=0.0)
    except ValueError as exc:
        assert "First recovery tick must be after time zero" in str(exc)
    else:
        raise AssertionError("Expected non-positive first tick to be rejected")
