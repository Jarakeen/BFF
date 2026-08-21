import pytest

from minmax.formulas.movement_speed import (
    calculate_block_speed,
    calculate_mount_walk_speed,
    calculate_sneak_speed,
    calculate_sprint_speed,
    calculate_swim_speed,
)


def test_calculate_sprint_speed():
    result = calculate_sprint_speed(
        base_walk_speed=5.0,
    )

    assert result == pytest.approx(7.0)


def test_calculate_sprint_speed_applies_modifiers():
    result = calculate_sprint_speed(
        base_walk_speed=5.0,
        set_sprint_speed=0.10,
        buff_movement_speed=0.05,
        item_movement_speed=0.05,
        set_movement_speed=0.05,
        buff_sprint_speed=0.10,
        skill_movement_speed=0.05,
        skill_sprint_speed=0.05,
        cp_sprint_speed=0.05,
        mundus_movement_speed=0.05,
        cp_movement_speed=0.10,
    )

    expected = (
        5.0
        * min(
            2,
            1
            + 0.40
            + 0.10
            + 0.05
            + 0.05
            + 0.05
            + 0.10
            + 0.05
            + 0.05
            + 0.05
            + 0.05,
        )
        * 1.10
    )

    assert result == pytest.approx(expected)


def test_calculate_sprint_speed_caps_at_two():
    result = calculate_sprint_speed(
        base_walk_speed=5.0,
        set_sprint_speed=1.0,
        buff_movement_speed=1.0,
        item_movement_speed=1.0,
        set_movement_speed=1.0,
        buff_sprint_speed=1.0,
        skill_movement_speed=1.0,
        skill_sprint_speed=1.0,
        cp_sprint_speed=1.0,
        mundus_movement_speed=1.0,
    )

    assert result == pytest.approx(10.0)


def test_calculate_swim_speed():
    result = calculate_swim_speed(
        base_walk_speed=5.0,
    )

    assert result == pytest.approx(3.0)


def test_calculate_swim_speed_applies_modifiers():
    result = calculate_swim_speed(
        base_walk_speed=5.0,
        skill_swim_speed=0.10,
        buff_movement_speed=0.05,
        mundus_movement_speed=0.05,
        item_movement_speed=0.05,
        set_movement_speed=0.05,
        cp_movement_speed=0.10,
    )

    expected = (
        (5.0 * 0.60 * 1.10)
        * (1 + 0.05 + 0.05 + 0.05 + 0.05 + 0.10)
    )

    assert result == pytest.approx(expected)


def test_calculate_sneak_speed():
    result = calculate_sneak_speed(
        base_walk_speed=5.0,
    )

    expected = 5.0 * (1 - 0.40)

    assert result == pytest.approx(expected)


def test_calculate_sneak_speed_applies_modifiers():
    result = calculate_sneak_speed(
        base_walk_speed=5.0,
        skill_normal_sneak_speed=0.10,
        cp_sneak_speed=0.05,
        skill_sneak_speed=0.10,
        buff_movement_speed=0.05,
        skill_movement_speed=0.05,
        mundus_movement_speed=0.05,
        item_movement_speed=0.05,
        set_movement_speed=0.05,
        skill2_sneak_speed=0.10,
        cp_movement_speed=0.10,
    )

    sneak_penalty = (
        1
        - (0.10)
        - (0.05)
    ) * (1 - 0.10)

    expected = (
        5.0
        * (1 - 0.40 * sneak_penalty + 0.05 + 0.05 + 0.05 + 0.05 + 0.05)
        * 1.20
    )

    assert result == pytest.approx(expected)


def test_calculate_sneak_speed_floors_inner_sneak_penalty_at_zero():
    result = calculate_sneak_speed(
        base_walk_speed=5.0,
        skill_normal_sneak_speed=2.0,
        cp_sneak_speed=0.0,
        skill_sneak_speed=0.0,
    )

    # (1 - 2 - 0) * (1 - 0) = -1
    # max(0, -1) = 0
    # Therefore the sneak penalty contributes nothing.
    expected = 5.0

    assert result == pytest.approx(expected)


def test_calculate_block_speed():
    result = calculate_block_speed(
        base_walk_speed=5.0,
    )

    assert result == pytest.approx(5.0)


def test_calculate_block_speed_applies_modifiers():
    result = calculate_block_speed(
        base_walk_speed=5.0,
        skill_block_speed_penalty=0.20,
        skill_block_speed=0.10,
        cp_block_speed=0.05,
    )

    expected = 5.0 * 0.80 * 1.10 * 1.05

    assert result == pytest.approx(expected)


def test_calculate_mount_walk_speed():
    result = calculate_mount_walk_speed(
        base_walk_speed=5.0,
    )

    expected = 5.0 * 1.15

    assert result == pytest.approx(expected)


def test_calculate_mount_walk_speed_applies_modifiers():
    result = calculate_mount_walk_speed(
        base_walk_speed=5.0,
        mount_speed_bonus=0.10,
        skill_mount_speed=0.05,
        cp_mount_speed=0.05,
        set_mount_speed=0.10,
        buff_mount_speed=0.10,
    )

    expected = (
        5.0
        * (1 + 0.15 + 0.10 + 0.05 + 0.05)
        * (1 + 0.10 + 0.10)
    )

    assert result == pytest.approx(expected)