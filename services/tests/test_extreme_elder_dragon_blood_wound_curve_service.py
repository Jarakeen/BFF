from __future__ import annotations

import pytest

from services.extreme_elder_dragon_blood_wound_curve_service import (
    ElderDragonBloodWoundSample,
    ExtremeElderDragonBloodWoundCurveService,
)


def test_linear_half_missing_health_hypothesis_is_supported_by_matching_samples():
    service = ExtremeElderDragonBloodWoundCurveService()
    result = service.verify(
        (
            ElderDragonBloodWoundSample(current_health=10000, max_health=10000, observed_heal=1000),
            ElderDragonBloodWoundSample(current_health=5000, max_health=10000, observed_heal=1250),
            ElderDragonBloodWoundSample(current_health=1000, max_health=10000, observed_heal=1450),
        ),
        relative_tolerance=1e-9,
    )

    assert result.sample_count == 3
    assert result.fitted_base_heal == pytest.approx(1000.0)
    assert result.max_relative_error == pytest.approx(0.0)
    assert result.linear_half_missing_health_supported
    assert result.predicted_heals == pytest.approx((1000.0, 1250.0, 1450.0))


def test_linear_half_missing_health_hypothesis_fails_closed_when_observations_disagree():
    result = ExtremeElderDragonBloodWoundCurveService().verify(
        (
            ElderDragonBloodWoundSample(current_health=10000, max_health=10000, observed_heal=1000),
            ElderDragonBloodWoundSample(current_health=5000, max_health=10000, observed_heal=1400),
            ElderDragonBloodWoundSample(current_health=1000, max_health=10000, observed_heal=1600),
        ),
        relative_tolerance=0.01,
    )

    assert not result.linear_half_missing_health_supported
    assert result.max_relative_error > 0.01


def test_wound_curve_verifier_requires_multiple_valid_samples():
    service = ExtremeElderDragonBloodWoundCurveService()

    with pytest.raises(ValueError, match="At least two"):
        service.verify((ElderDragonBloodWoundSample(100, 100, 10),))
    with pytest.raises(ValueError, match="between zero and max_health"):
        service.verify(
            (
                ElderDragonBloodWoundSample(101, 100, 10),
                ElderDragonBloodWoundSample(50, 100, 12),
            )
        )
