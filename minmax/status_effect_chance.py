from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class StatusEffectChanceSource(str, Enum):
    """Reviewed ESO source families with distinct baseline status chances."""

    SINGLE_TARGET_DIRECT = "single_target_direct"
    AREA_DIRECT = "area_direct"
    SINGLE_TARGET_DOT = "single_target_dot"
    AREA_DOT = "area_dot"
    WEAPON_ENCHANTMENT = "weapon_enchantment"
    WEAPON_POISON = "weapon_poison"
    LIGHT_ATTACK = "light_attack"
    HEAVY_ATTACK = "heavy_attack"


_BASE_CHANCE = {
    StatusEffectChanceSource.SINGLE_TARGET_DIRECT: 0.10,
    StatusEffectChanceSource.AREA_DIRECT: 0.05,
    StatusEffectChanceSource.SINGLE_TARGET_DOT: 0.03,
    StatusEffectChanceSource.AREA_DOT: 0.01,
    StatusEffectChanceSource.WEAPON_ENCHANTMENT: 0.20,
    StatusEffectChanceSource.WEAPON_POISON: 0.20,
    StatusEffectChanceSource.LIGHT_ATTACK: 0.0,
    StatusEffectChanceSource.HEAVY_ATTACK: 0.0,
}


@dataclass(frozen=True)
class StatusEffectChanceResult:
    source: StatusEffectChanceSource
    base_chance: float
    increase_percent: float
    final_chance: float

    def __post_init__(self) -> None:
        for value, label in (
            (self.base_chance, "base_chance"),
            (self.increase_percent, "increase_percent"),
            (self.final_chance, "final_chance"),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{label} must be finite")
        if self.base_chance < 0.0 or self.base_chance > 1.0:
            raise ValueError("base_chance must be between 0 and 1")
        if self.increase_percent < 0.0:
            raise ValueError("increase_percent cannot be negative")
        if self.final_chance < 0.0 or self.final_chance > 1.0:
            raise ValueError("final_chance must be between 0 and 1")


def base_status_effect_chance(source: StatusEffectChanceSource) -> float:
    """Return the reviewed baseline probability for one ESO damage-source family.

    Source authority is the checked-in UESP Online:Combat reference snapshot. The
    values are deliberately centralized here so rotation, optimization and audit
    callers do not grow their own slightly-different status-proc tables.
    """

    return _BASE_CHANCE[source]


def classify_skill_status_effect_source(
    *,
    is_dot: bool,
    is_aoe: bool,
) -> StatusEffectChanceSource:
    if is_dot:
        return (
            StatusEffectChanceSource.AREA_DOT
            if is_aoe
            else StatusEffectChanceSource.SINGLE_TARGET_DOT
        )
    return (
        StatusEffectChanceSource.AREA_DIRECT
        if is_aoe
        else StatusEffectChanceSource.SINGLE_TARGET_DIRECT
    )


def calculate_status_effect_chance(
    source: StatusEffectChanceSource,
    *,
    increase_percent: float = 0.0,
) -> StatusEffectChanceResult:
    """Apply additive percent increases to the source baseline and clamp at 100%.

    ESO's reviewed relationship is ``base chance * (1 + percent increases)``.
    ``increase_percent`` is supplied in percentage points, e.g. ``365`` means
    +365%, not 3.65 percentage points.
    """

    increase = float(increase_percent)
    if not math.isfinite(increase) or increase < 0.0:
        raise ValueError("increase_percent must be finite and non-negative")
    base = base_status_effect_chance(source)
    final = min(1.0, base * (1.0 + (increase / 100.0)))
    return StatusEffectChanceResult(
        source=source,
        base_chance=base,
        increase_percent=increase,
        final_chance=final,
    )


__all__ = [
    "StatusEffectChanceResult",
    "StatusEffectChanceSource",
    "base_status_effect_chance",
    "calculate_status_effect_chance",
    "classify_skill_status_effect_source",
]
