from __future__ import annotations

"""Canonical target-side Critical Damage Taken from named CombatState effects."""

from .combat_state import CombatState


_NAMED_CRITICAL_DAMAGE_TAKEN_PERCENT = {
    "Minor Brittle": 10.0,
    "Major Brittle": 20.0,
}


def critical_damage_taken_percent_from_target_state(
    target_combat_state: CombatState | None,
) -> float:
    """Return additive target Critical Damage Taken percentage points."""

    if target_combat_state is None:
        return 0.0
    return sum(
        value
        for name, value in _NAMED_CRITICAL_DAMAGE_TAKEN_PERCENT.items()
        if target_combat_state.has_buff(name)
    )


__all__ = ["critical_damage_taken_percent_from_target_state"]
