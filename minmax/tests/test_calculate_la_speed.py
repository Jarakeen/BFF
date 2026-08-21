import pytest

from old_pages.old_calculate_la_speed import (
    calculate_la_melee_speed,
    calculate_la_speed,
)


def test_calculate_la_speed():
    assert calculate_la_speed() == pytest.approx(1.0)


def test_calculate_la_speed_with_set_bonus():
    assert calculate_la_speed(
        set_la_speed=0.10,
    ) == pytest.approx(1.10)


def test_calculate_la_melee_speed():
    assert calculate_la_melee_speed() == pytest.approx(1.0)


def test_calculate_la_melee_speed_with_set_bonus():
    assert calculate_la_melee_speed(
        set_la_speed=0.10,
    ) == pytest.approx(1.10)


def test_calculate_la_melee_speed_with_melee_bonus():
    assert calculate_la_melee_speed(
        set_la_melee_speed=0.15,
    ) == pytest.approx(1.15)


def test_calculate_la_melee_speed_combines_both_set_bonuses():
    assert calculate_la_melee_speed(
        set_la_speed=0.10,
        set_la_melee_speed=0.15,
    ) == pytest.approx(1.25)


def test_calculate_la_speed_all_zero_inputs():
    assert calculate_la_speed(
        set_la_speed=0.0,
    ) == pytest.approx(1.0)


def test_calculate_la_melee_speed_all_zero_inputs():
    assert calculate_la_melee_speed(
        set_la_speed=0.0,
        set_la_melee_speed=0.0,
    ) == pytest.approx(1.0)