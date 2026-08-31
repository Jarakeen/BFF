import pytest

from minmax.skill_coefficient import (
    SkillCoefficient,
    evaluate_skill_coefficient,
)


def test_type_8_uses_max_stat_and_power():
    coefficient = SkillCoefficient(
        coefficient_number=1,
        type="8",
        a=0.175015,
        b=1.83764,
        c=-1.73373,
        r=1.0,
    )

    result = evaluate_skill_coefficient(
        coefficient,
        max_stat=30000,
        power=6000,
    )

    expected = (
        0.175015 * 30000
        + 1.83764 * 6000
        - 1.73373
    )

    assert result.raw_value == pytest.approx(
        expected
    )

    assert result.scaled_value == pytest.approx(
        expected
    )


def test_r_is_fit_metadata_not_a_coefficient_multiplier():
    coefficient = SkillCoefficient(
        coefficient_number=1,
        type="8",
        a=0.1,
        b=1.0,
        c=5.0,
        r=0.5,
    )

    result = evaluate_skill_coefficient(
        coefficient,
        max_stat=1000,
        power=1000,
    )

    assert result.raw_value == pytest.approx(
        1105.0
    )

    assert result.scaled_value == pytest.approx(
        1105.0
    )


def test_negative_max_stat_is_rejected():
    coefficient = SkillCoefficient(
        coefficient_number=1,
        type="8",
        a=0.1,
        b=1.0,
        c=0.0,
    )

    with pytest.raises(ValueError):
        evaluate_skill_coefficient(
            coefficient,
            max_stat=-1,
            power=1000,
        )


def test_negative_power_is_rejected():
    coefficient = SkillCoefficient(
        coefficient_number=1,
        type="8",
        a=0.1,
        b=1.0,
        c=0.0,
    )

    with pytest.raises(ValueError):
        evaluate_skill_coefficient(
            coefficient,
            max_stat=1000,
            power=-1,
        )


def test_unsupported_coefficient_type_is_rejected():
    coefficient = SkillCoefficient(
        coefficient_number=1,
        type="32",
        a=0.1,
        b=1.0,
        c=0.0,
    )

    with pytest.raises(ValueError):
        evaluate_skill_coefficient(
            coefficient,
            max_stat=1000,
            power=1000,
        )
