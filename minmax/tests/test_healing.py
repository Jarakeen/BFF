import pytest

from minmax.formulas.healing import (
    calculate_aoe_healing_done,
    calculate_dot_healing_done,
    calculate_health_restore,
    calculate_healing_done,
    calculate_healing_received,
    calculate_healing_reduction,
    calculate_healing_taken,
    calculate_healing_total,
    calculate_resurrect_time,
    calculate_single_target_healing_done,
)


def test_calculate_healing_done():
    result = calculate_healing_done(
        item_healing_done=0.05,
        set_healing_done=0.05,
        skill_healing_done=0.10,
        cp_healing_done=0.05,
        buff_healing_done=0.10,
        mundus_healing_done=0.05,
    )

    assert result == pytest.approx(0.40)


def test_calculate_aoe_healing_done():
    assert calculate_aoe_healing_done(
        skill_aoe_healing_done=0.10,
        set_aoe_healing_done=0.05,
        cp_aoe_healing_done=0.05,
    ) == pytest.approx(0.20)


def test_calculate_dot_healing_done():
    assert calculate_dot_healing_done(
        skill_dot_healing_done=0.10,
        set_dot_healing_done=0.05,
        cp_dot_healing_done=0.05,
    ) == pytest.approx(0.20)


def test_calculate_single_target_healing_done():
    assert calculate_single_target_healing_done(
        skill_single_target_healing_done=0.10,
        set_single_target_healing_done=0.05,
        cp_single_target_healing_done=0.05,
    ) == pytest.approx(0.20)


def test_calculate_healing_taken():
    assert calculate_healing_taken(
        item_healing_taken=0.05,
        set_healing_taken=0.05,
        skill_healing_taken=0.10,
        cp_healing_taken=0.05,
        buff_healing_taken=0.05,
    ) == pytest.approx(0.30)


def test_calculate_healing_received():
    result = calculate_healing_received(
        item_healing_received=0.10,
        set_healing_received=0.05,
        skill_healing_received=0.05,
        cp_healing_received=0.05,
        buff_healing_received=0.05,
        skill2_healing_received=0.10,
    )

    expected = (
        (1 + 0.10 + 0.05 + 0.05 + 0.05 + 0.05)
        * 1.10
        - 1
    )

    assert result == pytest.approx(expected)


def test_calculate_healing_total():
    result = calculate_healing_total(
        healing_done=0.20,
        healing_taken=0.10,
        healing_received=0.15,
    )

    expected = (
        1.20
        * 1.10
        * 1.15
    )

    assert result == pytest.approx(expected)


def test_calculate_resurrect_time():
    assert calculate_resurrect_time() == pytest.approx(7.0)


def test_calculate_resurrect_time_applies_all_modifiers():
    result = calculate_resurrect_time(
        set_resurrect_speed=0.10,
        skill_resurrect_speed=0.10,
        buff_resurrect_speed=0.05,
        cp_resurrect_speed=0.05,
        item_resurrect_speed=0.10,
    )

    expected = (
        7
        * 0.90
        * 0.90
        * 0.95
        * 0.95
        * 0.90
    )

    assert result == pytest.approx(expected)


def test_calculate_healing_reduction():
    assert calculate_healing_reduction(
        cp_healing_reduction=0.25,
    ) == pytest.approx(0.25)


def test_calculate_health_restore():
    assert calculate_health_restore(
        item_health_restore=100,
        skill_health_restore=200,
        buff_health_restore=50,
        set_health_restore=150,
    ) == pytest.approx(500)


def test_zero_inputs_produce_expected_baselines():
    assert calculate_healing_done() == pytest.approx(0.0)
    assert calculate_aoe_healing_done() == pytest.approx(0.0)
    assert calculate_dot_healing_done() == pytest.approx(0.0)
    assert calculate_single_target_healing_done() == pytest.approx(0.0)
    assert calculate_healing_taken() == pytest.approx(0.0)
    assert calculate_healing_received() == pytest.approx(0.0)
    assert calculate_healing_total(
        healing_done=0.0,
        healing_taken=0.0,
        healing_received=0.0,
    ) == pytest.approx(1.0)
    assert calculate_healing_reduction() == pytest.approx(0.0)
    assert calculate_health_restore() == pytest.approx(0.0)