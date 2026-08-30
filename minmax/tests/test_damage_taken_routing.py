from __future__ import annotations

import pytest

from minmax.combat_damage_modifiers import damage_taken_from_target_state
from minmax.combat_state import CombatState
from minmax.dd_mitigation import DDMitigationResult
from minmax.dd_stat_evaluation import DDStatEvaluation
from minmax.skill_combat_damage import calculate_skill_combat_damage
from minmax.skill_damage import SkillDamageResult


def _stats() -> DDStatEvaluation:
    return DDStatEvaluation(
        weapon_damage=3000.0,
        spell_damage=3000.0,
        physical_penetration=0.0,
        spell_penetration=0.0,
        effective_physical_penetration=0.0,
        effective_spell_penetration=0.0,
        physical_overpenetration=0.0,
        spell_overpenetration=0.0,
        critical_chance=0.0,
        effective_critical_chance=0.0,
        critical_chance_excess=0.0,
        critical_damage=50.0,
        effective_critical_damage=50.0,
        critical_damage_excess=0.0,
    )


def _skill(value: float = 1000.0) -> SkillDamageResult:
    return SkillDamageResult(skill_rank_id=123, components=(), total_raw_damage=value)


def test_target_state_maps_vulnerability_and_protection_to_damage_taken():
    vulnerable = damage_taken_from_target_state(
        CombatState(active_buffs=("Major Vulnerability",))
    )
    protected = damage_taken_from_target_state(
        CombatState(active_buffs=("Major Protection",))
    )

    assert vulnerable.generic == pytest.approx(0.10)
    assert protected.generic == pytest.approx(-0.10)


def test_target_damage_taken_is_applied_after_resistance_mitigation():
    mitigation = DDMitigationResult(
        target_resistance=25000.0,
        penetration=0.0,
        remaining_resistance=25000.0,
        mitigation_fraction=0.50,
        damage_multiplier=0.50,
    )

    result = calculate_skill_combat_damage(
        _skill(),
        _stats(),
        damage_type="flame",
        can_crit=False,
        mitigation=mitigation,
        target_combat_state=CombatState(active_buffs=("Major Vulnerability",)),
    ).damage

    assert result.expected_damage == pytest.approx(1000.0)
    assert result.mitigated_damage == pytest.approx(500.0)
    assert result.damage_taken_multiplier == pytest.approx(1.10)
    assert result.final_damage == pytest.approx(550.0)


def test_attacker_damage_done_and_target_damage_taken_remain_separate_stages():
    result = calculate_skill_combat_damage(
        _skill(),
        _stats(),
        damage_type="magical",
        can_crit=False,
        combat_state=CombatState(active_buffs=("Major Berserk",)),
        target_combat_state=CombatState(active_buffs=("Major Vulnerability",)),
    ).damage

    assert result.damage_done_multiplier == pytest.approx(1.10)
    assert result.damage_done_damage == pytest.approx(1100.0)
    assert result.damage_taken_multiplier == pytest.approx(1.10)
    assert result.final_damage == pytest.approx(1210.0)


def test_attacker_protection_does_not_reduce_outgoing_damage():
    result = calculate_skill_combat_damage(
        _skill(),
        _stats(),
        damage_type="physical",
        can_crit=False,
        combat_state=CombatState(active_buffs=("Major Protection",)),
    ).damage

    assert result.damage_done_multiplier == pytest.approx(1.0)
    assert result.damage_taken_multiplier == pytest.approx(1.0)
    assert result.final_damage == pytest.approx(1000.0)


def test_target_protection_reduces_final_damage_without_changing_attacker_stage():
    result = calculate_skill_combat_damage(
        _skill(),
        _stats(),
        damage_type="physical",
        can_crit=False,
        target_combat_state=CombatState(active_buffs=("Minor Protection",)),
    ).damage

    assert result.damage_done_multiplier == pytest.approx(1.0)
    assert result.mitigated_damage == pytest.approx(1000.0)
    assert result.damage_taken_multiplier == pytest.approx(0.95)
    assert result.final_damage == pytest.approx(950.0)
