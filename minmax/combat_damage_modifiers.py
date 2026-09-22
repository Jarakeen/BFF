from __future__ import annotations

from .combat_state import CombatState
from .damage_done import DamageDoneModifiers
from .damage_taken import DamageTakenModifiers


# Source: math/buff.txt
_NAMED_GENERIC_DAMAGE_DONE = {
    "Minor Berserk": 0.05,
    "Major Berserk": 0.10,
}

# Reviewed scribed-result runtime semantics. These belong to the component-layer
# Damage Done router rather than standing stat math. Magical Banner is the verified
# Banner Bearer + Magic Damage result and affects only Magic-damage events.
_NAMED_MAGIC_DAMAGE_DONE = {
    "Magical Banner": 0.06,
}

# Sources: math/buff.txt and math/debuff.txt
# Protection is a target-side reduction; Vulnerability is a target-side increase.
_NAMED_GENERIC_DAMAGE_TAKEN = {
    "Minor Protection": -0.05,
    "Major Protection": -0.10,
    "Minor Vulnerability": 0.05,
    "Major Vulnerability": 0.10,
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
    magic = sum(
        value
        for name, value in _NAMED_MAGIC_DAMAGE_DONE.items()
        if combat_state.has_buff(name)
    )
    return DamageDoneModifiers(generic=generic, magic=magic)


def damage_taken_from_target_state(
    target_combat_state: CombatState | None,
) -> DamageTakenModifiers:
    """Resolve verified target-side Damage Taken effects from explicit state."""

    if target_combat_state is None:
        return DamageTakenModifiers()

    generic = float(target_combat_state.explicit_damage_taken) + sum(
        value
        for name, value in _NAMED_GENERIC_DAMAGE_TAKEN.items()
        if target_combat_state.has_buff(name)
    )
    return DamageTakenModifiers(generic=generic)
