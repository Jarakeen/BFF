from __future__ import annotations

"""Canonical target-side resistance reductions from named CombatState effects."""

from .combat_state import CombatState


_NAMED_RESISTANCE_REDUCTION = {
    "Minor Breach": 2974.0,
    "Major Breach": 5948.0,
}


def resistance_reduction_from_target_state(
    target_combat_state: CombatState | None,
) -> float:
    """Return additive named target resistance reduction for one exact state."""

    if target_combat_state is None:
        return 0.0
    return sum(
        value
        for name, value in _NAMED_RESISTANCE_REDUCTION.items()
        if target_combat_state.has_buff(name)
    )


def target_resistance_from_combat_state(
    base_resistance: float,
    target_combat_state: CombatState | None,
) -> float:
    """Apply target-side resistance reductions without allowing negative armor."""

    base = float(base_resistance)
    if base < 0.0:
        raise ValueError("Target resistance cannot be negative.")
    return max(
        0.0,
        base - resistance_reduction_from_target_state(target_combat_state),
    )


__all__ = [
    "resistance_reduction_from_target_state",
    "target_resistance_from_combat_state",
]
