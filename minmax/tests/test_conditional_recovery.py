from minmax.conditional_recovery import (
    ENLIVENING_OVERFLOW_DURATION_SECONDS,
    ENLIVENING_OVERFLOW_TARGET_COOLDOWN_SECONDS,
    additive_recovery_bonus_at,
    create_enlivening_overflow_modifier,
    enlivening_overflow_recovery_bonus,
)
from minmax.resource_costs import ResourceType


def test_enlivening_overflow_uses_half_percent_max_magicka_up_to_150() -> None:
    assert enlivening_overflow_recovery_bonus(20000) == 100
    assert enlivening_overflow_recovery_bonus(30000) == 150
    assert enlivening_overflow_recovery_bonus(40000) == 150


def test_enlivening_overflow_affects_all_primary_recoveries_for_six_seconds() -> None:
    modifier = create_enlivening_overflow_modifier(
        max_magicka=30000,
        triggered_at_seconds=4.0,
    )

    assert modifier.amount == 150
    assert modifier.duration_seconds == ENLIVENING_OVERFLOW_DURATION_SECONDS == 6.0
    assert modifier.cooldown_seconds == ENLIVENING_OVERFLOW_TARGET_COOLDOWN_SECONDS == 12.0
    assert modifier.resources == (
        ResourceType.HEALTH,
        ResourceType.MAGICKA,
        ResourceType.STAMINA,
    )
    assert modifier.active_at(4.0)
    assert modifier.active_at(9.999)
    assert not modifier.active_at(10.0)


def test_conditional_recovery_bonus_only_applies_inside_active_window() -> None:
    modifier = create_enlivening_overflow_modifier(
        max_magicka=20000,
        triggered_at_seconds=2.0,
    )
    modifiers = (modifier,)

    assert additive_recovery_bonus_at(
        modifiers,
        resource=ResourceType.MAGICKA,
        time_seconds=4.0,
    ) == 100
    assert additive_recovery_bonus_at(
        modifiers,
        resource=ResourceType.STAMINA,
        time_seconds=8.0,
    ) == 0
