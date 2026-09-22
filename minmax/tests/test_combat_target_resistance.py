from minmax.combat_state import CombatState
from minmax.combat_target_resistance import (
    resistance_reduction_from_target_state,
    target_resistance_from_combat_state,
)


def test_breach_reductions_are_additive_on_target_state() -> None:
    state = CombatState(
        active_buffs=("Minor Breach", "Major Breach"),
    )

    assert resistance_reduction_from_target_state(state) == 8922.0
    assert target_resistance_from_combat_state(18200.0, state) == 9278.0


def test_target_resistance_never_goes_below_zero() -> None:
    state = CombatState(
        active_buffs=("Major Breach",),
    )

    assert target_resistance_from_combat_state(3000.0, state) == 0.0


def test_unrelated_target_buffs_do_not_change_resistance() -> None:
    state = CombatState(
        active_buffs=("Major Vulnerability",),
    )

    assert target_resistance_from_combat_state(18200.0, state) == 18200.0
