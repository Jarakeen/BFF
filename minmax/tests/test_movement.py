import pytest

from minmax.formulas.movement import (
    calculate_run_speed,
    calculate_sneak_detect_range,
    calculate_sneak_range,
    calculate_sprint_cost,
    calculate_walk_speed,
)


def test_calculate_sneak_range():
    result = calculate_sneak_range()

    assert result == pytest.approx(6.5)


def test_calculate_sneak_range_applies_modifiers():
    result = calculate_sneak_range(
        skill2_sneak_range=1.0,
        cp_sneak_range=0.5,
        skill_sneak_range=0.10,
        set_sneak_range=0.20,
    )

    expected = (6.5 + 1.0 + 0.5) * (1 + 0.10 + 0.20)

    assert result == pytest.approx(expected)


def test_calculate_sneak_range_floor_at_zero():
    result = calculate_sneak_range(
        skill2_sneak_range=-10.0,
        cp_sneak_range=0.0,
    )

    assert result == pytest.approx(0.0)


def test_calculate_sneak_detect_range():
    result = calculate_sneak_detect_range()

    assert result == pytest.approx(6.5)


def test_calculate_sneak_detect_range_applies_modifiers():
    result = calculate_sneak_detect_range(
        skill2_sneak_detect_range=1.0,
        cp_sneak_detect_range=0.5,
        item_sneak_detect_range=0.10,
        skill_sneak_detect_range=0.20,
        set_sneak_detect_range=0.30,
    )

    expected = (6.5 + 1.0 + 0.5) * (1 + 0.10 + 0.20 + 0.30)

    assert result == pytest.approx(expected)


def test_calculate_sneak_detect_range_floor_at_zero():
    result = calculate_sneak_detect_range(
        skill2_sneak_detect_range=-10.0,
        cp_sneak_detect_range=0.0,
    )

    assert result == pytest.approx(0.0)


def test_calculate_sprint_cost():
    result = calculate_sprint_cost()

    assert result == pytest.approx(500)


def test_calculate_sprint_cost_applies_all_modifiers():
    result = calculate_sprint_cost(
        skill2_sprint_cost=100,
        cp_sprint_cost=0.10,
        buff_sprint_cost=0.20,
        set_sprint_cost=0.30,
        skill_sprint_cost=0.40,
        item_sprint_cost=0.50,
    )

    expected = (
        600
        * 1.10
        * 1.20
        * 1.30
        * 1.40
        * 1.50
    )

    assert result == pytest.approx(expected)


def test_calculate_walk_speed():
    result = calculate_walk_speed(
        base_walk_speed=5.0,
    )

    assert result == pytest.approx(1.5)


def test_calculate_walk_speed_applies_modifiers():
    result = calculate_walk_speed(
        base_walk_speed=5.0,
        buff_movement_speed=0.10,
        skill_movement_speed=0.05,
        item_movement_speed=0.05,
        set_movement_speed=0.10,
        mundus_movement_speed=0.05,
        cp_movement_speed=0.20,
    )

    expected = (
        5.0 * 0.3
        * (1 + 0.10 + 0.05 + 0.05 + 0.10 + 0.05)
        * 1.20
    )

    assert result == pytest.approx(expected)


def test_calculate_run_speed():
    result = calculate_run_speed(
        base_walk_speed=5.0,
    )

    assert result == pytest.approx(5.0)


def test_calculate_run_speed_applies_modifiers():
    result = calculate_run_speed(
        base_walk_speed=5.0,
        buff_movement_speed=0.10,
        skill_movement_speed=0.05,
        item_movement_speed=0.05,
        set_movement_speed=0.10,
        mundus_movement_speed=0.05,
        cp_movement_speed=0.20,
    )

    expected = (
        5.0
        * (1 + 0.10 + 0.05 + 0.05 + 0.10 + 0.05)
        * 1.20
    )

    assert result == pytest.approx(expected)