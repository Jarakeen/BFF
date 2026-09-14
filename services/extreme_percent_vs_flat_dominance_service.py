from __future__ import annotations

"""Conservative dominance proof for percentage branches versus displaced flat value.

This service is objective-neutral. It answers one bounded question: given an upper
bound on the pre-percent subtotal, can a percentage branch possibly recover enough
value to beat a competing flat contribution? Shared non-negative percentage effects
can only make the displaced flat contribution harder to overcome, so omitting them
is conservative when proving the percentage branch dominated.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremePercentVsFlatDominanceResult:
    pre_percent_subtotal_upper_bound: float
    percent_ceiling: float
    percent_gain_upper_bound: float
    displaced_flat_value: float
    required_subtotal_to_match: float
    dominated: bool


class ExtremePercentVsFlatDominanceService:
    """Prove a percentage branch cannot catch a displaced flat contribution."""

    @staticmethod
    def assess(
        *,
        pre_percent_subtotal_upper_bound: float,
        percent_ceiling: float,
        displaced_flat_value: float,
    ) -> ExtremePercentVsFlatDominanceResult:
        subtotal = float(pre_percent_subtotal_upper_bound)
        percent = float(percent_ceiling)
        displaced = float(displaced_flat_value)
        if subtotal < 0.0:
            raise ValueError("pre-percent subtotal upper bound must be non-negative")
        if percent <= 0.0:
            raise ValueError("percent ceiling must be positive")
        if displaced < 0.0:
            raise ValueError("displaced flat value must be non-negative")

        fraction = percent / 100.0
        gain = subtotal * fraction
        required = displaced / fraction if fraction > 0.0 else float("inf")
        return ExtremePercentVsFlatDominanceResult(
            pre_percent_subtotal_upper_bound=subtotal,
            percent_ceiling=percent,
            percent_gain_upper_bound=gain,
            displaced_flat_value=displaced,
            required_subtotal_to_match=required,
            dominated=gain < displaced - 1e-9,
        )


__all__ = [
    "ExtremePercentVsFlatDominanceResult",
    "ExtremePercentVsFlatDominanceService",
]
