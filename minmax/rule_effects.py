from dataclasses import dataclass

from .effects import EffectUnit


@dataclass(frozen=True)
class RuleEffect:
    rule_type: str
    value: float
    source: str
    unit: EffectUnit

    target_system: str | None = None
    condition: str | None = None

    material_name: str | None = None
    gear_type: str | None = None
    quality: str | None = None
    item_level: int | None = None