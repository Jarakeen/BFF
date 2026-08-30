import pytest

from minmax.combat_state import CombatState
from minmax.damage_done import DamageDoneModifiers, resolve_damage_done
from minmax.dd_damage import DDDamageEvent, calculate_dd_damage
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


def test_damage_done_selects_dot_aoe_and_type_without_direct_or_single_target():
    modifiers = DamageDoneModifiers(
        generic=0.05,
        direct=0.50,
        dot=0.10,
        area=0.07,
        single_target=0.40,
        flame=0.06,
        frost=0.30,
    )

    result = resolve_damage_done(
        modifiers,
        damage_type="flame",
        is_dot=True,
        is_aoe=True,
    )

    assert result.generic == pytest.approx(0.05)
    assert result.delivery == pytest.approx(0.10)
    assert result.target_shape == pytest.approx(0.07)
    assert result.damage_type == pytest.approx(0.06)
    assert result.total == pytest.approx(0.28)
    assert result.multiplier == pytest.approx(1.28)


def test_damage_done_categories_share_one_additive_event_bucket():
    event = DDDamageEvent(
        base_value=1000.0,
        damage_type="flame",
        can_crit=False,
        is_dot=True,
        is_aoe=False,
    )
    modifiers = DamageDoneModifiers(
        generic=0.05,
        dot=0.10,
        flame=0.06,
    )

    result = calculate_dd_damage(event, _stats(), damage_done=modifiers)

    assert result.scaled_damage == pytest.approx(1000.0)
    assert result.damage_done.total == pytest.approx(0.21)
    assert result.damage_done_multiplier == pytest.approx(1.21)
    assert result.damage_done_damage == pytest.approx(1210.0)
    assert result.expected_damage == pytest.approx(1210.0)
    assert result.mitigated_damage == pytest.approx(1210.0)


def test_magical_event_uses_magic_damage_done_category():
    result = resolve_damage_done(
        DamageDoneModifiers(magic=0.08),
        damage_type="magical",
    )
    assert result.damage_type == pytest.approx(0.08)


def test_major_berserk_reaches_skill_damage_only_when_explicitly_active():
    skill = SkillDamageResult(
        skill_rank_id=123,
        components=(),
        total_raw_damage=1000.0,
    )

    standing = calculate_skill_combat_damage(
        skill,
        _stats(),
        damage_type="magical",
        can_crit=False,
        combat_state=CombatState(),
    )
    active = calculate_skill_combat_damage(
        skill,
        _stats(),
        damage_type="magical",
        can_crit=False,
        combat_state=CombatState(active_buffs=("major berserk",)),
    )

    assert standing.damage.damage_done_multiplier == pytest.approx(1.0)
    assert standing.damage.mitigated_damage == pytest.approx(1000.0)
    assert active.damage.damage_done.generic == pytest.approx(0.10)
    assert active.damage.damage_done_multiplier == pytest.approx(1.10)
    assert active.damage.mitigated_damage == pytest.approx(1100.0)
