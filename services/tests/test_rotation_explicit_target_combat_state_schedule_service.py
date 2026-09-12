import pytest

from services.rotation_explicit_target_combat_state_schedule_service import (
    RotationExplicitTargetCombatStateScheduleService,
    RotationTargetCombatStateWindow,
)


def test_explicit_target_schedule_resolves_half_open_off_balance_window() -> None:
    service = RotationExplicitTargetCombatStateScheduleService(
        (
            RotationTargetCombatStateWindow(
                5.0,
                12.0,
                ("Off Balance",),
            ),
        )
    )

    assert service(4.999).has_buff("Off Balance") is False
    assert service(5.0).has_buff("Off Balance") is True
    assert service(11.999).has_buff("Off Balance") is True
    assert service(12.0).has_buff("Off Balance") is False


def test_explicit_target_schedule_empty_windows_are_authoritative_known_empty_state() -> None:
    state = RotationExplicitTargetCombatStateScheduleService()(8.0, 1)

    assert state.in_combat is True
    assert state.active_buffs == ()


def test_explicit_target_schedule_unions_overlapping_named_buffs() -> None:
    service = RotationExplicitTargetCombatStateScheduleService(
        (
            RotationTargetCombatStateWindow(1.0, 4.0, ("Off Balance",)),
            RotationTargetCombatStateWindow(2.0, 3.0, ("Major Vulnerability",)),
        )
    )

    state = service(2.5)

    assert state.has_buff("Off Balance") is True
    assert state.has_buff("Major Vulnerability") is True


def test_target_window_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="end must be greater"):
        RotationTargetCombatStateWindow(4.0, 4.0, ("Off Balance",))

    with pytest.raises(ValueError, match="start cannot be negative"):
        RotationTargetCombatStateWindow(-1.0, 2.0, ("Off Balance",))


def test_target_schedule_rejects_invalid_runtime_time() -> None:
    service = RotationExplicitTargetCombatStateScheduleService()

    with pytest.raises(ValueError, match="finite and non-negative"):
        service(-0.1)
