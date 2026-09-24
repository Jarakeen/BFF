from minmax.weapon_poison_runtime_cadence import (
    WeaponPoisonCadenceAuthority,
    authoritative_weapon_poison_cadence,
)


def test_authoritative_poison_cadence_is_runtime_ready() -> None:
    cadence = authoritative_weapon_poison_cadence()

    assert cadence.proc_chance == 0.20
    assert cadence.cooldown_seconds == 10.0
    assert cadence.cooldown_scope == "global_player_poison"
    assert cadence.activation_causes == (
        "light_attack_damage",
        "heavy_attack_damage",
        "weapon_ability_damage",
    )
    assert cadence.single_target_dot_ticks_eligible is False
    assert cadence.poison_suppresses_weapon_enchantment is True
    assert cadence.runtime_blockers == ()
    assert cadence.runtime_ready is True


def test_authoritative_poison_cadence_tracks_each_proof_dimension() -> None:
    cadence = authoritative_weapon_poison_cadence()
    authority = WeaponPoisonCadenceAuthority.AUTHORITATIVE

    assert cadence.proc_chance_authority is authority
    assert cadence.cooldown_authority is authority
    assert cadence.cooldown_scope_authority is authority
    assert cadence.activation_authority is authority
    assert cadence.single_target_dot_authority is authority
    assert cadence.suppression_authority is authority
