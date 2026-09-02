import pytest

from minmax.skill_component_utility_effect import (
    SkillComponentUtilityEffect,
    SkillComponentUtilityEffectType,
    extract_explicit_component_utility_effects,
)


def test_extracts_movement_speed_reduction_with_magnitude():
    effects = extract_explicit_component_utility_effects(
        skill_rank_id=10,
        coefficient_number=1,
        component_text="Their first attack reduces their Movement Speed by 30% and deals $1 Magic Damage.",
    )
    assert len(effects) == 1
    assert effects[0].effect_type is SkillComponentUtilityEffectType.MOVEMENT_SPEED_REDUCTION
    assert effects[0].magnitude_fraction == 0.30


def test_extracts_stun_and_immobilize_without_temporal_fields():
    effects = extract_explicit_component_utility_effects(
        skill_rank_id=20,
        coefficient_number=2,
        component_text="Their second attack immobilizes them and then stuns them.",
    )
    assert [effect.effect_type for effect in effects] == [
        SkillComponentUtilityEffectType.STUN,
        SkillComponentUtilityEffectType.IMMOBILIZE,
    ]
    assert all(effect.magnitude_fraction is None for effect in effects)


def test_extracts_spaced_knockback_wording():
    effects = extract_explicit_component_utility_effects(
        skill_rank_id=25,
        coefficient_number=1,
        component_text="Strike the enemy and knock them back.",
    )
    assert [effect.effect_type for effect in effects] == [SkillComponentUtilityEffectType.KNOCKBACK]


def test_contextual_stun_mentions_do_not_apply_stun():
    for text in (
        "Deals $1 Magic Damage if the stun lasts the full duration.",
        "After the stun ends, the target takes $1 Flame Damage.",
    ):
        assert extract_explicit_component_utility_effects(
            skill_rank_id=27,
            coefficient_number=1,
            component_text=text,
        ) == ()


def test_explicit_interrupt_immunity_grant_is_utility_effect():
    effects = extract_explicit_component_utility_effects(
        skill_rank_id=28,
        coefficient_number=2,
        component_text="Gain a damage shield that absorbs up to $2 damage and grants interrupt immunity.",
    )
    assert [effect.effect_type for effect in effects] == [
        SkillComponentUtilityEffectType.INTERRUPT_IMMUNITY
    ]


def test_damage_only_text_emits_no_utility_effect():
    assert extract_explicit_component_utility_effects(
        skill_rank_id=30,
        coefficient_number=1,
        component_text="Deal $1 Flame Damage every 1 second.",
    ) == ()


def test_non_speed_utility_rejects_numeric_magnitude():
    with pytest.raises(ValueError):
        SkillComponentUtilityEffect(
            skill_rank_id=40,
            coefficient_number=1,
            effect_type=SkillComponentUtilityEffectType.STUN,
            evidence="stuns",
            magnitude_fraction=0.5,
        )
