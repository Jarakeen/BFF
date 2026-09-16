from __future__ import annotations

import pytest

from services.extreme_stealth_state_service import (
    ExtremeStealthDetectionInputs,
    ExtremeStealthStateService,
)


def test_detection_radius_reduction_maps_positive_record_inputs_into_canonical_formula() -> None:
    result = ExtremeStealthStateService.evaluate_detection_radius(
        ExtremeStealthDetectionInputs(
            flat_skill_reduction_meters=2.0,
            set_reduction_ratio=0.20,
        )
    )

    assert result.detection_radius_meters == pytest.approx((6.5 - 2.0) * 0.80)
    assert result.reduction_meters == pytest.approx(6.5 - ((6.5 - 2.0) * 0.80))
    assert result.reduction_ratio == pytest.approx(result.reduction_meters / 6.5)


def test_detection_radius_never_goes_below_zero_from_flat_reduction() -> None:
    result = ExtremeStealthStateService.evaluate_detection_radius(
        ExtremeStealthDetectionInputs(flat_skill_reduction_meters=99.0)
    )

    assert result.detection_radius_meters == 0.0
    assert result.reduction_meters == pytest.approx(6.5)
    assert result.reduction_ratio == pytest.approx(1.0)


def test_detection_radius_never_goes_below_zero_from_ratio_over_reduction() -> None:
    result = ExtremeStealthStateService.evaluate_detection_radius(
        ExtremeStealthDetectionInputs(
            set_reduction_ratio=0.80,
            item_reduction_ratio=0.50,
        )
    )

    assert result.detection_radius_meters == 0.0
    assert result.reduction_meters == pytest.approx(6.5)
    assert result.reduction_ratio == pytest.approx(1.0)


def test_negative_reduction_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be non-negative"):
        ExtremeStealthStateService.evaluate_detection_radius(
            ExtremeStealthDetectionInputs(set_reduction_ratio=-0.10)
        )
