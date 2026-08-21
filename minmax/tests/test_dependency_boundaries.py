import pytest

from minmax.formulas.damage_done import calculate_damage_done
from minmax.formulas.light_attack_damage import calculate_la_flame_staff


def test_damage_done_is_its_own_bucket():
    """Consumer formulas must receive the resolved DamageDone bucket, not rebuild it."""
    assert calculate_damage_done(
        cp_damage_done=0.10,
        skill_damage_done=0.20,
        set_damage_done=0.30,
        buff_damage_done=0.40,
        item_damage_done=0.50,
    ) == pytest.approx(1.50)


def test_la_flame_consumes_damage_buckets_independently():
    """UESP adds the four damage buckets; they must not be pre-combined or multiplied."""
    result = calculate_la_flame_staff(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=5000,
        la_flame_weapon_damage=4000,
        flame_damage_done=0.20,
        direct_damage_done=0.30,
        single_target_damage_done=0.40,
        damage_done=0.10,
    )

    base = min(
        int(0.045 * 30000) + int(0.4725 * 5000),
        3465,
    )
    expected = base * (1 + 0.20 + 0.30 + 0.40 + 0.10)

    assert result == pytest.approx(expected)


def test_zero_damage_buckets_are_neutral():
    """Each optional damage bucket must be neutral when absent."""
    base = min(
        int(0.045 * 30000) + int(0.4725 * 5000),
        3465,
    )

    result = calculate_la_flame_staff(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=5000,
        la_flame_weapon_damage=4000,
    )

    assert result == pytest.approx(base)


def test_damage_done_does_not_absorb_elemental_damage_done():
    """A resolved DamageDone value must remain distinct from FlameDamageDone."""
    damage_done = calculate_damage_done(
        cp_damage_done=0.10,
        skill_damage_done=0.20,
    )

    result = calculate_la_flame_staff(
        magicka=30000,
        stamina=15000,
        la_flame_spell_damage=5000,
        la_flame_weapon_damage=4000,
        flame_damage_done=0.30,
        damage_done=damage_done,
    )

    base = min(
        int(0.045 * 30000) + int(0.4725 * 5000),
        3465,
    )
    expected = base * (1 + 0.30 + 0.30)

    assert result == pytest.approx(expected)
