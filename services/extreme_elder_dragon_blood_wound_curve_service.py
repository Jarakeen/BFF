from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class ElderDragonBloodWoundSample:
    current_health: float
    max_health: float
    observed_heal: float

    @property
    def missing_health_fraction(self) -> float:
        maximum = float(self.max_health)
        current = float(self.current_health)
        if maximum <= 0:
            raise ValueError("max_health must be greater than zero")
        if current < 0 or current > maximum:
            raise ValueError("current_health must be between zero and max_health")
        if float(self.observed_heal) <= 0:
            raise ValueError("observed_heal must be greater than zero")
        return (maximum - current) / maximum


@dataclass(frozen=True)
class ElderDragonBloodWoundCurveResult:
    sample_count: int
    fitted_base_heal: float
    max_relative_error: float
    root_mean_square_relative_error: float
    linear_half_missing_health_supported: bool
    predicted_heals: tuple[float, ...]


class ExtremeElderDragonBloodWoundCurveService:
    """Test observed Elder Dragon Blood casts against the historical 50% linear hypothesis.

    Official wording proves an increase of up to 50% based on missing Health, but
    current Update-49-era notes do not publish the interpolation curve. This helper
    therefore treats ``base * (1 + 0.5 * missing_health_fraction)`` as a hypothesis
    to verify from observations rather than as canonical combat math.

    ``base`` is fitted by least squares so a full-Health sample is not required.
    The result is evidence only; callers must not promote the hypothesis into the
    canonical healing evaluator unless the observed data supports it closely.
    """

    BONUS_AT_FULL_MISSING_HEALTH = 0.50

    def verify(
        self,
        samples,
        *,
        relative_tolerance: float = 0.01,
    ) -> ElderDragonBloodWoundCurveResult:
        normalized = tuple(samples or ())
        if len(normalized) < 2:
            raise ValueError("At least two wound-state samples are required")
        tolerance = float(relative_tolerance)
        if tolerance < 0:
            raise ValueError("relative_tolerance must be non-negative")

        factors: list[float] = []
        observed: list[float] = []
        for sample in normalized:
            if not isinstance(sample, ElderDragonBloodWoundSample):
                sample = ElderDragonBloodWoundSample(**dict(sample))
            missing = sample.missing_health_fraction
            factors.append(1.0 + self.BONUS_AT_FULL_MISSING_HEALTH * missing)
            observed.append(float(sample.observed_heal))

        denominator = sum(factor * factor for factor in factors)
        if denominator <= 0:
            raise ValueError("Unable to fit wound curve from supplied samples")
        base = sum(factor * value for factor, value in zip(factors, observed)) / denominator
        predicted = tuple(base * factor for factor in factors)

        relative_errors = tuple(
            abs(prediction - value) / value
            for prediction, value in zip(predicted, observed)
        )
        max_error = max(relative_errors)
        rms_error = sqrt(
            sum(error * error for error in relative_errors) / len(relative_errors)
        )
        return ElderDragonBloodWoundCurveResult(
            sample_count=len(normalized),
            fitted_base_heal=base,
            max_relative_error=max_error,
            root_mean_square_relative_error=rms_error,
            linear_half_missing_health_supported=max_error <= tolerance,
            predicted_heals=predicted,
        )
