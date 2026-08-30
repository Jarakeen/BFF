from __future__ import annotations

from .combat_state import CombatState
from .damage_done import DamageDoneModifiers


# Source: math/buff.txt
_NAMED_GENERIC_DAMAGE_DONE = {
    "Minor Berserk": 0.05,
    "Major Berserk": 0.10,
}


def damage_done_from_combat_state(
    combat_state: CombatState | None,
) -> DamageDoneModifiers:
    """Resolve verified named Damage Done buffs from one explicit combat state."""

    if combat_state is None:
        return DamageDoneModifiers()

    generic = sum(
        value
        for name, value in _NAMED_GENERIC_DAMAGE_DONE.items()
        if combat_state.has_buff(name)
    )
    return DamageDoneModifiers(generic=generic)
