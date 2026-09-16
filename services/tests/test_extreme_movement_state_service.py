from __future__ import annotations

import pytest

from services.extreme_movement_state_service import (
    ExtremeMovementStateInputs,
    ExtremeMovementStateService,
)


def test_movement_state_reuses_run_speed_formula_and_reports_cap() -> None:
    result = ExtremeMovementStateService.evaluate(
        "movement_speed",
        ExtremeMovementStateInputs(
            base_walk_speed=3.0,
            buff_movement_speed=0.30,
            item_movement_speed=0.10,
        ),
    )

    assert result.raw_speed == pytest.approx(4.2)
    assert result.raw_multiplier == pytest.approx(1.4)
    assert result.effective_speed == pytest.approx(4.2)
    assert result.effective_multiplier == pytest.approx(1.4)


def test_sprint_state_uses_shared_channels_and_effective_200_percent_cap() -> None:
    result = ExtremeMovementStateService.evaluate(
        "sprint_speed",
        ExtremeMovementStateInputs(
            base_walk_speed=3.0,
            buff_movement_speed=0.30,
            item_movement_speed=0.20,
            skill_sprint_speed=0.30,
        ),
    )

    assert result.raw_speed == pytest.approx(6.0)
    assert result.raw_multiplier == pytest.approx(2.0)
    assert result.effective_speed == pytest.approx(6.0)
    assert result.effective_multiplier == pytest.approx(2.0)


def test_stealthed_movement_uses_existing_sneak_formula() -> None:
    result = ExtremeMovementStateService.evaluate(
        "stealthed_movement_speed",
        ExtremeMovementStateInputs(
            base_walk_speed=3.0,
            skill_normal_sneak_speed=1.0,
            buff_movement_speed=0.30,
        ),
    )

    assert result.raw_speed == pytest.approx(3.9)
    assert result.raw_multiplier == pytest.approx(1.3)
    assert result.effective_speed == pytest.approx(3.9)


def test_effective_output_caps_raw_run_speed_without_erasing_raw_record() -> None:
    result = ExtremeMovementStateService.evaluate(
        "movement_speed",
        ExtremeMovementStateInputs(
            base_walk_speed=3.0,
            buff_movement_speed=0.80,
            item_movement_speed=0.50,
        ),
    )

    assert result.raw_multiplier == pytest.approx(2.3)
    assert result.effective_multiplier == pytest.approx(2.0)


def test_unknown_movement_objective_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported Extreme movement objective"):
        ExtremeMovementStateService.evaluate(
            "teleport_speed",
            ExtremeMovementStateInputs(),
        )
