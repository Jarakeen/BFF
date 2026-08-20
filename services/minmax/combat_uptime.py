from dataclasses import dataclass


@dataclass(frozen=True)
class CombatUptimeResult:
    duration: float
    cooldown: float
    maximum_uptime: float
    activation_chance: float
    expected_uptime: float


def calculate_combat_uptime(
    *,
    duration: float,
    cooldown: float,
    activation_chance: float = 1.0,
) -> CombatUptimeResult:
    """Calculate theoretical and expected uptime for a repeating effect."""

    if duration < 0:
        raise ValueError("Duration cannot be negative.")

    if cooldown < 0:
        raise ValueError("Cooldown cannot be negative.")

    if not 0.0 <= activation_chance <= 1.0:
        raise ValueError(
            "Activation chance must be between 0 and 1."
        )

    if duration == 0:
        maximum_uptime = 0.0

    elif cooldown == 0:
        maximum_uptime = 1.0

    else:
        maximum_uptime = min(
            duration / cooldown,
            1.0,
        )

    expected_uptime = (
        maximum_uptime * activation_chance
    )

    return CombatUptimeResult(
        duration=duration,
        cooldown=cooldown,
        maximum_uptime=maximum_uptime,
        activation_chance=activation_chance,
        expected_uptime=expected_uptime,
    )