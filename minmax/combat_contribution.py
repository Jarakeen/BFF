from dataclasses import dataclass

from .combat_calculation import CombatEffectResult


@dataclass(frozen=True)
class CombatContribution:
    source: str
    effect_type: str
    raw_value: float
    uptime: float
    effective_value: float


def calculate_combat_contribution(
    result: CombatEffectResult,
) -> CombatContribution:
    """Calculate the effective contribution of an evaluated effect."""

    effective_value = result.value * result.uptime

    return CombatContribution(
        source=result.source,
        effect_type=result.effect_type,
        raw_value=result.value,
        uptime=result.uptime,
        effective_value=effective_value,
    )