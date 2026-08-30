from minmax.dd_mitigation import calculate_dd_mitigation
from minmax.dd_stat_evaluation import DDStatEvaluation
from minmax.skill_damage import SkillDamageResult
from minmax.skill_combat_damage import (
    SkillCombatDamageResult,
    calculate_skill_combat_damage,
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


def make_skill_damage(
    total_raw_damage: float,
    *,
    skill_rank_id: int = 4410,
) -> SkillDamageResult:
    return SkillDamageResult(
        skill_rank_id=skill_rank_id,
        components=(),
        total_raw_damage=total_raw_damage,
    )


def test_raw_skill_damage_is_not_rescaled_by_offensive_power():
    result = calculate_skill_combat_damage(
        make_skill_damage(5000),
        make_stats(
            weapon_damage=3000,
            spell_damage=3000,
        ),
    )

    assert isinstance(result, SkillCombatDamageResult)
    assert result.raw_skill_damage == 5000
    assert result.damage.scaled_damage == 5000
    assert result.damage.expected_damage == 5000


def test_damage_type_selects_penetration_and_offensive_stat():
    result = calculate_skill_combat_damage(
        make_skill_damage(1000),
        make_stats(
            weapon_damage=2000,
            spell_damage=9000,
            physical_penetration=12000,
            spell_penetration=5000,
        ),
        damage_type="physical",
    )

    assert result.damage_type == "physical"
    assert result.damage.offensive_stat == "weapon_damage"
    assert result.damage.penetration_stat == "physical_penetration"
    assert result.damage.penetration == 12000


def test_critical_chance_and_damage_flow_through():
    result = calculate_skill_combat_damage(
        make_skill_damage(1000),
        make_stats(
            critical_chance=50,
            critical_damage=100,
        ),
    )

    assert result.damage.expected_damage == 1500


def test_can_crit_false_ignores_crit_stats():
    result = calculate_skill_combat_damage(
        make_skill_damage(1000),
        make_stats(
            critical_chance=100,
            critical_damage=125,
        ),
        can_crit=False,
    )

    assert result.damage.expected_damage == 1000
    assert result.damage.critical_chance == 0.0


def test_mitigation_reduces_final_damage():
    mitigation = calculate_dd_mitigation(
        target_resistance=18200,
        penetration=0,
    )

    result = calculate_skill_combat_damage(
        make_skill_damage(1000),
        make_stats(),
        mitigation=mitigation,
    )

    assert result.damage.mitigation_multiplier == 0.636
    assert result.damage.mitigated_damage == 636


def test_negative_raw_skill_damage_is_rejected():
    try:
        calculate_skill_combat_damage(
            make_skill_damage(-1),
            make_stats(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Negative raw skill damage should be rejected."
        )


def test_skill_rank_id_is_preserved_for_explainability():
    result = calculate_skill_combat_damage(
        make_skill_damage(1000, skill_rank_id=99123),
        make_stats(),
    )

    assert result.skill_rank_id == 99123
