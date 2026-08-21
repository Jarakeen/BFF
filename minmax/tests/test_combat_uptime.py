import pytest

from minmax.combat_uptime import (
    calculate_combat_uptime,
)


def test_duration_equal_to_cooldown_has_full_uptime():
    result = calculate_combat_uptime(
        duration=10,
        cooldown=10,
    )

    assert result.maximum_uptime == 1.0
    assert result.expected_uptime == 1.0


def test_duration_half_of_cooldown_has_fifty_percent_uptime():
    result = calculate_combat_uptime(
        duration=5,
        cooldown=10,
    )

    assert result.maximum_uptime == 0.5
    assert result.expected_uptime == 0.5


def test_duration_longer_than_cooldown_is_capped():
    result = calculate_combat_uptime(
        duration=15,
        cooldown=10,
    )

    assert result.maximum_uptime == 1.0
    assert result.expected_uptime == 1.0


def test_activation_chance_reduces_expected_uptime():
    result = calculate_combat_uptime(
        duration=5,
        cooldown=10,
        activation_chance=0.5,
    )

    assert result.maximum_uptime == 0.5
    assert result.expected_uptime == 0.25


def test_zero_activation_chance_has_zero_expected_uptime():
    result = calculate_combat_uptime(
        duration=5,
        cooldown=10,
        activation_chance=0.0,
    )

    assert result.maximum_uptime == 0.5
    assert result.expected_uptime == 0.0


def test_zero_duration_has_zero_uptime():
    result = calculate_combat_uptime(
        duration=0,
        cooldown=10,
    )

    assert result.maximum_uptime == 0.0
    assert result.expected_uptime == 0.0


def test_zero_cooldown_has_full_uptime():
    result = calculate_combat_uptime(
        duration=5,
        cooldown=0,
    )

    assert result.maximum_uptime == 1.0
    assert result.expected_uptime == 1.0


def test_negative_duration_is_rejected():
    with pytest.raises(ValueError):
        calculate_combat_uptime(
            duration=-1,
            cooldown=10,
        )


def test_negative_cooldown_is_rejected():
    with pytest.raises(ValueError):
        calculate_combat_uptime(
            duration=5,
            cooldown=-1,
        )


def test_activation_chance_above_one_is_rejected():
    with pytest.raises(ValueError):
        calculate_combat_uptime(
            duration=5,
            cooldown=10,
            activation_chance=1.1,
        )


def test_activation_chance_below_zero_is_rejected():
    with pytest.raises(ValueError):
        calculate_combat_uptime(
            duration=5,
            cooldown=10,
            activation_chance=-0.1,
        )


def test_fractional_uptime():
    result = calculate_combat_uptime(
        duration=3,
        cooldown=7,
        activation_chance=0.75,
    )

    assert result.maximum_uptime == pytest.approx(3 / 7)
    assert result.expected_uptime == pytest.approx(
        (3 / 7) * 0.75
    )