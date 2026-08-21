import pytest

from old_pages.old_item_traits import (
    calculate_bloodthirsty,
    calculate_divines,
    calculate_sturdy,
    calculate_training,
)


def test_calculate_divines():
    assert calculate_divines(
        item_divines=0.15,
    ) == pytest.approx(0.15)


def test_calculate_sturdy():
    assert calculate_sturdy(
        item_sturdy=0.10,
    ) == pytest.approx(0.10)


def test_calculate_training():
    assert calculate_training(
        item_training=0.20,
    ) == pytest.approx(0.20)


def test_calculate_bloodthirsty():
    assert calculate_bloodthirsty(
        item_bloodthirsty=0.25,
    ) == pytest.approx(0.25)


def test_calculate_divines_zero():
    assert calculate_divines() == pytest.approx(0.0)


def test_calculate_sturdy_zero():
    assert calculate_sturdy() == pytest.approx(0.0)


def test_calculate_training_zero():
    assert calculate_training() == pytest.approx(0.0)


def test_calculate_bloodthirsty_zero():
    assert calculate_bloodthirsty() == pytest.approx(0.0)