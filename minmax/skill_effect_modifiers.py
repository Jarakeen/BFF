from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModifierVisibility(str, Enum):
    """Where one verified modifier is allowed to affect a skill value."""

    TOOLTIP_ONLY = "tooltip_only"
    ACTUAL_ONLY = "actual_only"
    TOOLTIP_AND_ACTUAL = "tooltip_and_actual"


@dataclass(frozen=True)
class SkillEffectModifier:
    """One explicit, auditable modifier applied above raw coefficient math.

    This object intentionally does not encode ESO-specific stacking rules.
    Callers must provide modifiers in the verified application order. Until a
    modifier's stacking position is proven, it should remain unresolved rather
    than being added here speculatively.
    """

    name: str
    visibility: ModifierVisibility
    multiplier: float = 1.0
    flat_addend: float = 0.0
    source: str = ""
    condition: str = ""

    def __post_init__(self) -> None:
        if self.multiplier < 0:
            raise ValueError("modifier multiplier cannot be negative")

    @property
    def affects_tooltip(self) -> bool:
        return self.visibility in {
            ModifierVisibility.TOOLTIP_ONLY,
            ModifierVisibility.TOOLTIP_AND_ACTUAL,
        }

    @property
    def affects_actual_effect(self) -> bool:
        return self.visibility in {
            ModifierVisibility.ACTUAL_ONLY,
            ModifierVisibility.TOOLTIP_AND_ACTUAL,
        }


@dataclass(frozen=True)
class SkillEffectModifierTrace:
    name: str
    visibility: ModifierVisibility
    multiplier: float
    flat_addend: float
    input_value: float
    output_value: float
    source: str = ""
    condition: str = ""


def apply_skill_effect_modifier(
    value: float,
    modifier: SkillEffectModifier,
) -> SkillEffectModifierTrace:
    """Apply one already-verified modifier in an explicitly supplied order."""

    input_value = float(value)
    output_value = (input_value + float(modifier.flat_addend)) * float(
        modifier.multiplier
    )
    return SkillEffectModifierTrace(
        name=modifier.name,
        visibility=modifier.visibility,
        multiplier=float(modifier.multiplier),
        flat_addend=float(modifier.flat_addend),
        input_value=input_value,
        output_value=output_value,
        source=modifier.source,
        condition=modifier.condition,
    )
