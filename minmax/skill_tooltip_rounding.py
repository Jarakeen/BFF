from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillTooltipRoundingCandidates:
    """Diagnostic integer results while ESO's final policy is unresolved."""

    raw_value: float
    floor_value: int
    nearest_half_up_value: int
    ceiling_value: int

    @property
    def distinct_values(self) -> tuple[int, ...]:
        return tuple(
            dict.fromkeys(
                (
                    self.floor_value,
                    self.nearest_half_up_value,
                    self.ceiling_value,
                )
            )
        )


def tooltip_rounding_candidates(value: float) -> SkillTooltipRoundingCandidates:
    """Return named hypotheses without choosing an unverified ESO rule."""

    raw_value = float(value)
    if not math.isfinite(raw_value):
        raise ValueError("tooltip value must be finite")
    return SkillTooltipRoundingCandidates(
        raw_value=raw_value,
        floor_value=math.floor(raw_value),
        nearest_half_up_value=math.floor(raw_value + 0.5),
        ceiling_value=math.ceil(raw_value),
    )


def matching_rounding_policies(
    candidates: SkillTooltipRoundingCandidates,
    observed_value: int,
) -> tuple[str, ...]:
    """Identify which named raw-rounding hypotheses match a game observation."""

    observed = int(observed_value)
    policies = (
        ("floor", candidates.floor_value),
        ("nearest-half-up", candidates.nearest_half_up_value),
        ("ceiling", candidates.ceiling_value),
    )
    return tuple(name for name, value in policies if value == observed)
