from dataclasses import dataclass


@dataclass(frozen=True)
class CooldownResult:
    base_cooldown: float
    cooldown_reduction: float
    final_cooldown: float


def calculate_cooldown(
    *,
    base_cooldown: float,
    cooldown_reduction: float = 0.0,
) -> CooldownResult:
    """Calculate cooldown after percentage-based reduction."""

    if base_cooldown < 0:
        raise ValueError("Cooldown cannot be negative.")

    if not 0.0 <= cooldown_reduction <= 100.0:
        raise ValueError(
            "Cooldown reduction must be between 0 and 100 percent."
        )

    final_cooldown = base_cooldown * (
        1.0 - cooldown_reduction / 100.0
    )

    return CooldownResult(
        base_cooldown=base_cooldown,
        cooldown_reduction=cooldown_reduction,
        final_cooldown=final_cooldown,
    )