from __future__ import annotations

from dataclasses import dataclass

from minmax.formulas.final_calculations import calculate_sneak_detect_range


@dataclass(frozen=True)
class ExtremeStealthDetectionInputs:
    """Positive detection-radius reductions in Extreme record units."""

    flat_skill_reduction_meters: float = 0.0
    flat_cp_reduction_meters: float = 0.0
    item_reduction_ratio: float = 0.0
    skill_reduction_ratio: float = 0.0
    set_reduction_ratio: float = 0.0


@dataclass(frozen=True)
class ExtremeStealthDetectionResult:
    detection_radius_meters: float
    base_detection_radius_meters: float
    reduction_meters: float
    reduction_ratio: float


class ExtremeStealthStateService:
    """Project MOST Stealthy through the canonical sneak-detect equation.

    ``calculate_sneak_detect_range`` owns the UESP stacking equation.  Its source
    channels are signed changes to range; this adapter exposes the Extreme record
    contract in the more natural positive-reduction direction and converts signs
    exactly once at the formula boundary.
    """

    BASE_DETECTION_RADIUS_METERS = 6.5

    @classmethod
    def evaluate_detection_radius(
        cls,
        inputs: ExtremeStealthDetectionInputs,
    ) -> ExtremeStealthDetectionResult:
        for name, value in (
            ("flat_skill_reduction_meters", inputs.flat_skill_reduction_meters),
            ("flat_cp_reduction_meters", inputs.flat_cp_reduction_meters),
            ("item_reduction_ratio", inputs.item_reduction_ratio),
            ("skill_reduction_ratio", inputs.skill_reduction_ratio),
            ("set_reduction_ratio", inputs.set_reduction_ratio),
        ):
            if float(value) < 0:
                raise ValueError(f"{name} must be non-negative")

        radius = calculate_sneak_detect_range(
            skill2_sneak_detect_range=-float(inputs.flat_skill_reduction_meters),
            cp_sneak_detect_range=-float(inputs.flat_cp_reduction_meters),
            item_sneak_detect_range=-float(inputs.item_reduction_ratio),
            skill_sneak_detect_range=-float(inputs.skill_reduction_ratio),
            set_sneak_detect_range=-float(inputs.set_reduction_ratio),
        )
        base = float(cls.BASE_DETECTION_RADIUS_METERS)
        reduction = max(0.0, base - float(radius))
        return ExtremeStealthDetectionResult(
            detection_radius_meters=float(radius),
            base_detection_radius_meters=base,
            reduction_meters=reduction,
            reduction_ratio=(reduction / base if base else 0.0),
        )


__all__ = [
    "ExtremeStealthDetectionInputs",
    "ExtremeStealthDetectionResult",
    "ExtremeStealthStateService",
]
