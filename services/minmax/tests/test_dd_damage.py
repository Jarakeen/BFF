from services.minmax.dd_damage import (
    DDDamageEvent,
    DDDamageResult,
    calculate_dd_damage,
)
from services.minmax.dd_mitigation import (
    calculate_dd_mitigation,
)
from services.minmax.dd_stat_evaluation import (
    DDStatEvaluation,
)


def make_stats(
    *,
    weapon_damage: float = 0.0,
    spell_damage: float = 0.0,
    physical_penetration: float = 0.0,
    spell_penetration: float = 0.0,
    critical_chance: float = 0.0,
    critical_damage: float = 0.0,
) -> DDStatEvaluation:
    return DDStatEvaluation(
        weapon_damage=weapon_damage,
        spell_damage=spell_damage,
        physical_penetration=physical_penetration,
        spell_penetration=spell_penetration,
        effective_physical_penetration=physical_penetration,
        effective_spell_penetration=spell_penetration,
        physical_overpenetration=0.0,
        spell_overpenetration=0.0,
        critical_chance=critical_chance,
        effective_critical_chance=critical_chance,
        critical_chance_excess=0.0,
        critical_damage=critical_damage,
        effective_critical_damage=critical_damage,
        critical_damage_excess=0.0,
    )


def test_damage_event_can_be_calculated():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
        ),
        make_stats(),
    )

    assert isinstance(result, DDDamageResult)
    assert result.expected_damage == 1000
    assert result.mitigated_damage == 1000


def test_scaling_uses_combined_offensive_stats_without_damage_type():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
        ),
        make_stats(
            weapon_damage=1000,
            spell_damage=1000,
        ),
    )

    assert result.offensive_stat == "combined_offensive_power"
    assert result.offensive_power == 2000
    assert result.scaled_damage == 2000


def test_physical_damage_uses_weapon_damage():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="physical",
        ),
        make_stats(
            weapon_damage=2000,
            spell_damage=5000,
        ),
    )

    assert result.offensive_stat == "weapon_damage"
    assert result.offensive_power == 2000
    assert result.penetration_stat == "physical_penetration"
    assert result.scaled_damage == 2000


def test_poison_damage_uses_weapon_damage():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="poison",
        ),
        make_stats(
            weapon_damage=2000,
            spell_damage=5000,
        ),
    )

    assert result.offensive_stat == "weapon_damage"
    assert result.offensive_power == 2000
    assert result.penetration_stat == "physical_penetration"


def test_magical_damage_uses_spell_damage():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="magical",
        ),
        make_stats(
            weapon_damage=5000,
            spell_damage=2000,
        ),
    )

    assert result.offensive_stat == "spell_damage"
    assert result.offensive_power == 2000
    assert result.penetration_stat == "spell_penetration"
    assert result.scaled_damage == 2000


def test_flame_damage_uses_spell_damage():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="flame",
        ),
        make_stats(
            weapon_damage=5000,
            spell_damage=2000,
        ),
    )

    assert result.offensive_stat == "spell_damage"
    assert result.offensive_power == 2000
    assert result.penetration_stat == "spell_penetration"


def test_physical_damage_uses_physical_penetration():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
            damage_type="physical",
        ),
        make_stats(
            physical_penetration=12000,
            spell_penetration=5000,
        ),
    )

    assert result.penetration_stat == "physical_penetration"
    assert result.penetration == 12000


def test_magical_damage_uses_spell_penetration():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
            damage_type="flame",
        ),
        make_stats(
            physical_penetration=12000,
            spell_penetration=5000,
        ),
    )

    assert result.penetration_stat == "spell_penetration"
    assert result.penetration == 5000


def test_non_critical_event_ignores_crit_stats():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
            can_crit=False,
        ),
        make_stats(
            critical_chance=100,
            critical_damage=125,
        ),
    )

    assert result.expected_damage == 1000
    assert result.critical_chance == 0.0
    assert result.mitigated_damage == 1000


def test_critical_chance_and_damage_affect_expected_damage():
    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
        ),
        make_stats(
            critical_chance=50,
            critical_damage=100,
        ),
    )

    assert result.expected_damage == 1500
    assert result.mitigated_damage == 1500


def test_damage_can_be_mitigated_by_target_resistance():
    mitigation = calculate_dd_mitigation(
        target_resistance=18200,
        penetration=0,
    )

    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
        ),
        make_stats(),
        mitigation=mitigation,
    )

    assert result.expected_damage == 1000
    assert result.mitigation_multiplier == 0.636
    assert result.mitigated_damage == 636


def test_penetration_can_remove_target_mitigation():
    mitigation = calculate_dd_mitigation(
        target_resistance=18200,
        penetration=18200,
    )

    result = calculate_dd_damage(
        DDDamageEvent(
            base_value=1000,
        ),
        make_stats(),
        mitigation=mitigation,
    )

    assert result.expected_damage == 1000
    assert result.mitigation_multiplier == 1.0
    assert result.mitigated_damage == 1000


def test_negative_base_damage_is_rejected():
    try:
        calculate_dd_damage(
            DDDamageEvent(
                base_value=-1,
            ),
            make_stats(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Negative base damage should be rejected."
        )


def test_unsupported_damage_type_is_rejected():
    try:
        calculate_dd_damage(
            DDDamageEvent(
                base_value=1000,
                damage_type="not_real",
            ),
            make_stats(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Unsupported damage type should be rejected."
        )