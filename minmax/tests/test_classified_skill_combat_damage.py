import pytest

from minmax.damage_done import DamageDoneModifiers
from minmax.dd_stat_evaluation import DDStatEvaluation
from minmax.skill_coefficient import SkillCoefficientResult
from minmax.skill_combat_damage import calculate_classified_skill_combat_damage
from minmax.skill_component_classification import SkillComponentClassification, SkillEffectKind
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


def _component(number: int, value: float) -> SkillCoefficientResult:
    return SkillCoefficientResult(
        coefficient_number=number,
        coefficient_type="8",
        a=0.0,
        b=0.0,
        c=value,
        r=1.0,
        max_stat=0.0,
        power=0.0,
        scaled_value=value,
    )


def _skill(*components: SkillCoefficientResult) -> SkillDamageResult:
    return SkillDamageResult(
        skill_rank_id=777,
        components=tuple(components),
        total_raw_damage=sum(component.scaled_value for component in components),
    )


def test_classified_components_receive_only_their_own_damage_done_categories():
    skill = _skill(_component(1, 1000.0), _component(2, 500.0))
    classifications = (
        SkillComponentClassification(
            skill_rank_id=777,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="flame",
            is_dot=False,
            is_aoe=False,
            can_crit=False,
            source="verified fixture",
        ),
        SkillComponentClassification(
            skill_rank_id=777,
            coefficient_number=2,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="flame",
            is_dot=True,
            is_aoe=True,
            can_crit=False,
            source="verified fixture",
        ),
    )
    modifiers = DamageDoneModifiers(
        generic=0.05,
        direct=0.10,
        dot=0.20,
        area=0.03,
        single_target=0.04,
        flame=0.06,
    )

    result = calculate_classified_skill_combat_damage(
        skill,
        _stats(),
        classifications,
        damage_done=modifiers,
    )

    assert result.unresolved == ()
    assert len(result.components) == 2
    assert result.components[0].damage.damage_done.total == pytest.approx(0.25)
    assert result.components[0].damage.final_damage == pytest.approx(1250.0)
    assert result.components[1].damage.damage_done.total == pytest.approx(0.34)
    assert result.components[1].damage.final_damage == pytest.approx(670.0)
    assert result.raw_damage == pytest.approx(1500.0)
    assert result.final_damage == pytest.approx(1920.0)


def test_missing_component_classification_is_reported_not_guessed():
    skill = _skill(_component(1, 1000.0), _component(2, 500.0))
    classifications = (
        SkillComponentClassification(
            skill_rank_id=777,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="physical",
            is_dot=False,
            is_aoe=False,
            can_crit=False,
        ),
    )

    result = calculate_classified_skill_combat_damage(skill, _stats(), classifications)

    assert len(result.components) == 1
    assert result.final_damage == pytest.approx(1000.0)
    assert result.unresolved == (
        "Skill rank 777 coefficient 2: component classification unavailable",
    )


def test_non_damage_component_is_left_for_its_own_evaluator():
    skill = _skill(_component(1, 1000.0), _component(2, 500.0))
    classifications = (
        SkillComponentClassification(
            skill_rank_id=777,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="shock",
            is_dot=False,
            is_aoe=False,
            can_crit=False,
        ),
        SkillComponentClassification(
            skill_rank_id=777,
            coefficient_number=2,
            effect_kind=SkillEffectKind.HEAL,
            is_aoe=True,
            can_crit=True,
        ),
    )

    result = calculate_classified_skill_combat_damage(skill, _stats(), classifications)

    assert len(result.components) == 1
    assert result.components[0].coefficient_number == 1
    assert result.raw_damage == pytest.approx(1000.0)
    assert result.unresolved == ()


def test_incomplete_damage_identity_is_explicitly_unresolved():
    skill = _skill(_component(1, 1000.0))
    classifications = (
        SkillComponentClassification(
            skill_rank_id=777,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="flame",
            is_dot=None,
            is_aoe=False,
            can_crit=True,
        ),
    )

    result = calculate_classified_skill_combat_damage(skill, _stats(), classifications)

    assert result.components == ()
    assert result.unresolved == (
        "Skill rank 777 coefficient 1: damage classification incomplete",
    )
