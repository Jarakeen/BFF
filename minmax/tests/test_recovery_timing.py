from minmax.recovery_timing import (
    IN_COMBAT_RECOVERY_INTERVAL_SECONDS,
    RecoveryActivityState,
    resolve_in_combat_recovery_tick,
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
