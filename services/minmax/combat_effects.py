from dataclasses import dataclass

from .effects import EffectUnit


@dataclass(frozen=True)
class CombatEffect:
    effect_type: str
    value: float
    source: str
    unit: EffectUnit

    damage_type: str | None = None
    target: str | None = None

    duration_value: float | None = None
    duration_unit: str | None = None

    scaling_type: str | None = None
    condition: str | None = None