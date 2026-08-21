import pytest

from old_pages.old_elemental_resistances import (
    calculate_disease_resist,
    calculate_flame_resist,
    calculate_frost_resist,
    calculate_poison_resist,
    calculate_shock_resist,
)


def test_calculate_frost_resist():
    assert calculate_frost_resist(
        item_frost_resist=100,
        skill_frost_resist=50,
    ) == pytest.approx(150)


def test_calculate_flame_resist():
    assert calculate_flame_resist(
        item_flame_resist=100,
        skill_flame_resist=50,
    ) == pytest.approx(150)


def test_calculate_shock_resist():
    assert calculate_shock_resist(
        item_shock_resist=100,
        skill_shock_resist=50,
    ) == pytest.approx(150)


def test_calculate_poison_resist():
    assert calculate_poison_resist(
        item_poison_resist=100,
        skill_poison_resist=50,
    ) == pytest.approx(150)


def test_calculate_disease_resist():
    assert calculate_disease_resist(
        item_disease_resist=100,
        skill_disease_resist=50,
    ) == pytest.approx(150)


def test_frost_resist_zero_inputs():
    assert calculate_frost_resist() == pytest.approx(0)


def test_flame_resist_zero_inputs():
    assert calculate_flame_resist() == pytest.approx(0)


def test_shock_resist_zero_inputs():
    assert calculate_shock_resist() == pytest.approx(0)


def test_poison_resist_zero_inputs():
    assert calculate_poison_resist() == pytest.approx(0)


def test_disease_resist_zero_inputs():
    assert calculate_disease_resist() == pytest.approx(0)