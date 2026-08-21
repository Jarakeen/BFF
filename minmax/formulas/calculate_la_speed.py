import math
import pytest

def calculate_la_speed(
    *,
    set_la_speed: float = 0.0,
) -> float:
    """
    Calculate light attack speed multiplier.

    UESP:

    LASpeed =
        1 + Set.LASpeed
    """
    return 1 + set_la_speed


def calculate_la_melee_speed(
    *,
    set_la_speed: float = 0.0,
    set_la_melee_speed: float = 0.0,
) -> float:
    """
    Calculate melee light attack speed multiplier.

    UESP:

    LAMeleeSpeed =
        1 + Set.LASpeed + Set.LAMeleeSpeed
    """
    return (
        1
        + set_la_speed
        + set_la_melee_speed
    )