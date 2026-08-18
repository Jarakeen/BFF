from dataclasses import dataclass

from .effect_kinds import EffectKind
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