from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillComponentActualEffectModifier:
    """Verified actual-effect-only changes for one coefficient component.

    ``power_bonus`` changes the coefficient's power input before evaluation.
    ``additive_percent`` is applied to that component after coefficient
    evaluation. These values deliberately do not alter tooltip candidates.
    """

    coefficient_number: int
    power_bonus: float = 0.0
    additive_percent: float = 0.0
    sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.coefficient_number < 1:
            raise ValueError("coefficient_number must be positive")


@dataclass(frozen=True)
class SkillComponentActualEffectTrace:
    coefficient_number: int
    base_power: float
    power_bonus: float
    effective_power: float
    coefficient_value: float
    additive_percent: float
    output_value: float
    sources: tuple[str, ...] = ()
