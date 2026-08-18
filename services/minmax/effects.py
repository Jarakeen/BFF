from dataclasses import dataclass
from enum import Enum

from .effect_kinds import EffectKind
from .stat_ids import StatId


class EffectOperation(str, Enum):
    ADD = "add"
    ADD_PERCENT = "add_percent"
    MULTIPLY = "multiply"
    SET = "set"


class EffectUnit(str, Enum):
    FLAT = "flat"
    PERCENT = "percent"


@dataclass(frozen=True)
class Effect:
    operation: EffectOperation
    value: float
    source: str

    stat: StatId | None = None

    kind: EffectKind = EffectKind.STAT
    unit: EffectUnit = EffectUnit.FLAT

    damage_type: str | None = None
    target: str | None = None

    duration_value: float | None = None
    duration_unit: str | None = None

    condition: str | None = None