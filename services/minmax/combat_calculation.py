from dataclasses import dataclass

from .combat_effects import CombatEffect
from .combat_duration import calculate_duration
from .combat_uptime import calculate_combat_uptime


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

    uptime: float = 1.0
    cooldown: float | None = None
    maximum_uptime: float = 1.0
    expected_uptime: float = 1.0


def calculate_combat_effect(
    effect: CombatEffect,
    *,
    fight_duration: float | None = None,
    cooldown: float | None = None,
    activation_chance: float = 1.0,
) -> CombatEffectResult:
    """Resolve a combat effect without inventing proc frequency."""

    duration = calculate_duration(
        duration=effect.duration_value,
        fight_duration=fight_duration,
    )

    maximum_uptime = duration.uptime
    expected_uptime = duration.uptime

    if cooldown is not None:
        if effect.duration_value is None:
            raise ValueError(
                "Cooldown cannot be evaluated without an effect duration."
            )

        uptime = calculate_combat_uptime(
            duration=effect.duration_value,
            cooldown=cooldown,
            activation_chance=activation_chance,
        )

        maximum_uptime = uptime.maximum_uptime
        expected_uptime = uptime.expected_uptime

    return CombatEffectResult(
        effect_type=effect.effect_type,
        value=effect.value,
        source=effect.source,
        damage_type=effect.damage_type,
        target=effect.target,
        duration_value=effect.duration_value,
        duration_unit=effect.duration_unit,
        scaling_type=effect.scaling_type,
        uptime=expected_uptime,
        cooldown=cooldown,
        maximum_uptime=maximum_uptime,
        expected_uptime=expected_uptime,
    )