from __future__ import annotations

import pytest

from minmax.skill_coefficients import (
    SkillCoefficient,
    evaluate_skill_coefficient,
    power_equivalent_for_observed_value,
)


def test_power_equivalent_solver_recovers_target_power_for_one_component():
    coefficient = SkillCoefficient(
        coefficient_number=1,
        type="8",
        a=0.116163,
        b=1.22023,
        c=-0.138672,
        r=1.0,
    )
    component = evaluate_skill_coefficient(
        coefficient,
        max_stat=31022,
        power=1464,
    )

    diagnostic = power_equivalent_for_observed_value((component,), 9436)

    assert diagnostic is not None
    assert diagnostic.current_power == pytest.approx(1464)
    assert diagnostic.equivalent_power == pytest.approx(4779.861244191668)
    assert diagnostic.power_delta == pytest.approx(3315.861244191668)
    assert diagnostic.raw_value_at_current_power == pytest.approx(5389.886634)
    assert diagnostic.observed_to_raw_ratio == pytest.approx(9436 / 5389.886634)


def test_power_equivalent_solver_handles_multiple_type8_components():
    first = evaluate_skill_coefficient(
        SkillCoefficient(1, "8", 0.1, 1.0, 5.0),
        max_stat=20000,
        power=3000,
    )
    second = evaluate_skill_coefficient(
        SkillCoefficient(2, "8", 0.05, 0.5, -2.0),
        max_stat=20000,
        power=3000,
    )
    target_power = 4200.0
    target = (
        (0.1 * 20000) + (1.0 * target_power) + 5.0
        + (0.05 * 20000) + (0.5 * target_power) - 2.0
    )

    diagnostic = power_equivalent_for_observed_value((first, second), target)

    assert diagnostic is not None
    assert diagnostic.equivalent_power == pytest.approx(target_power)


def test_power_equivalent_solver_returns_none_when_power_coefficient_is_zero():
    component = evaluate_skill_coefficient(
        SkillCoefficient(1, "8", 0.1, 0.0, 5.0),
        max_stat=20000,
        power=3000,
    )

    assert power_equivalent_for_observed_value((component,), 5000) is None
