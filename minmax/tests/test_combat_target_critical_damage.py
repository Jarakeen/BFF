from minmax.combat_state import CombatState
from minmax.combat_target_critical_damage import (
    critical_damage_taken_percent_from_target_state,
)


def test_minor_and_major_brittle_are_additive_target_critical_damage_taken() -> None:
    state = CombatState(active_buffs=("Minor Brittle", "Major Brittle"))

    assert critical_damage_taken_percent_from_target_state(state) == 30.0


def test_unrelated_target_effects_do_not_change_critical_damage_taken() -> None:
    state = CombatState(active_buffs=("Major Vulnerability", "Major Breach"))

    assert critical_damage_taken_percent_from_target_state(state) == 0.0
