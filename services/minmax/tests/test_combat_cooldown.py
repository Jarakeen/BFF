import pytest

from services.minmax.combat_cooldown import calculate_cooldown


def test_no_cooldown_reduction():
    result = calculate_cooldown(
        base_cooldown=10,
    )

    assert result.base_cooldown == 10
    assert result.cooldown_reduction == 0.0
    assert result.final_cooldown == 10


def test_fifty_percent_cooldown_reduction():
    result = calculate_cooldown(
        base_cooldown=10,
        cooldown_reduction=50,
    )

    assert result.final_cooldown == 5


def test_full_cooldown_reduction():
    result = calculate_cooldown(
        base_cooldown=10,
        cooldown_reduction=100,
    )

    assert result.final_cooldown == 0


def test_fractional_cooldown():
    result = calculate_cooldown(
        base_cooldown=10,
        cooldown_reduction=25,
    )

    assert result.final_cooldown == pytest.approx(7.5)


def test_negative_cooldown_is_rejected():
    with pytest.raises(ValueError):
        calculate_cooldown(
            base_cooldown=-1,
        )


def test_negative_reduction_is_rejected():
    with pytest.raises(ValueError):
        calculate_cooldown(
            base_cooldown=10,
            cooldown_reduction=-1,
        )


def test_reduction_over_one_hundred_percent_is_rejected():
    with pytest.raises(ValueError):
        calculate_cooldown(
            base_cooldown=10,
            cooldown_reduction=101,
        )