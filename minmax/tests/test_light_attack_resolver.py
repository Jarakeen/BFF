from minmax.combat_state import LightAttackState
from minmax.resolvers.light_attack_resolver import resolve_light_attack_state


def test_resolver_preserves_resolved_values():
    state = resolve_light_attack_state(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=5000,
        la_flame_weapon_damage=4000,
        skill2_la_damage=100,
        cp_la_damage=0.05,
        skill_la_damage=0.10,
        set_la_damage=0.05,
        flame_damage_done=0.05,
        direct_damage_done=0.08,
        single_target_damage_done=0.10,
        damage_done=0.05,
    )

    assert isinstance(state, LightAttackState)

    assert state.magicka == 30000
    assert state.stamina == 15000
    assert state.la_flame_spell_damage == 5000
    assert state.la_flame_weapon_damage == 4000

    assert state.skill2_la_damage == 100
    assert state.cp_la_damage == 0.05
    assert state.skill_la_damage == 0.10
    assert state.set_la_damage == 0.05

    assert state.flame_damage_done == 0.05
    assert state.direct_damage_done == 0.08
    assert state.single_target_damage_done == 0.10
    assert state.damage_done == 0.05


def test_resolver_does_not_calculate_or_modify_values():
    state = resolve_light_attack_state(
        magicka=12345,
        stamina=6789,
        skill2_la_damage=0.123,
        damage_done=-0.04,
    )

    assert state.magicka == 12345
    assert state.stamina == 6789
    assert state.skill2_la_damage == 0.123
    assert state.damage_done == -0.04
    