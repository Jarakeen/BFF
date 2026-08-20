from dataclasses import dataclass

from .combat_effects import CombatEffect



@dataclass(frozen=True)
class CombatEffectResult:
    effect_type: str
    value: float
    source: str

    damage_type: str | None = None
    target: str | None = None

    duration_value: float | None = None
    duration_unit: str | None = None

    scaling_type: str | None = None


def calculate_combat_effect(
    effect: CombatEffect,
) -> CombatEffectResult:
    """Resolve a combat effect without applying timing or uptime."""

    return CombatEffectResult(
    effect_type=effect.effect_type,
    value=effect.value,
    source=effect.source,
    damage_type=effect.damage_type,
    target=effect.target,
    duration_value=effect.duration_value,
    duration_unit=effect.duration_unit,
    scaling_type=effect.scaling_type,
)