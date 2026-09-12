import pytest

from minmax.status_effect_chance import (
    StatusEffectChanceSource,
    base_status_effect_chance,
    calculate_status_effect_chance,
    classify_skill_status_effect_source,
)


def test_reviewed_source_baselines_are_centralized() -> None:
    assert base_status_effect_chance(StatusEffectChanceSource.SINGLE_TARGET_DIRECT) == pytest.approx(0.10)
    assert base_status_effect_chance(StatusEffectChanceSource.AREA_DIRECT) == pytest.approx(0.05)
    assert base_status_effect_chance(StatusEffectChanceSource.SINGLE_TARGET_DOT) == pytest.approx(0.03)
    assert base_status_effect_chance(StatusEffectChanceSource.AREA_DOT) == pytest.approx(0.01)
    assert base_status_effect_chance(StatusEffectChanceSource.WEAPON_ENCHANTMENT) == pytest.approx(0.20)
    assert base_status_effect_chance(StatusEffectChanceSource.WEAPON_POISON) == pytest.approx(0.20)
    assert base_status_effect_chance(StatusEffectChanceSource.LIGHT_ATTACK) == 0.0
    assert base_status_effect_chance(StatusEffectChanceSource.HEAVY_ATTACK) == 0.0


def test_skill_component_classification_selects_reviewed_baseline_family() -> None:
    assert classify_skill_status_effect_source(is_dot=False, is_aoe=False) is StatusEffectChanceSource.SINGLE_TARGET_DIRECT
    assert classify_skill_status_effect_source(is_dot=False, is_aoe=True) is StatusEffectChanceSource.AREA_DIRECT
    assert classify_skill_status_effect_source(is_dot=True, is_aoe=False) is StatusEffectChanceSource.SINGLE_TARGET_DOT
    assert classify_skill_status_effect_source(is_dot=True, is_aoe=True) is StatusEffectChanceSource.AREA_DOT


def test_percent_increases_multiply_the_source_baseline() -> None:
    result = calculate_status_effect_chance(
        StatusEffectChanceSource.SINGLE_TARGET_DIRECT,
        increase_percent=365.0,
    )

    assert result.base_chance == pytest.approx(0.10)
    assert result.final_chance == pytest.approx(0.465)


def test_status_effect_chance_caps_at_one_hundred_percent() -> None:
    result = calculate_status_effect_chance(
        StatusEffectChanceSource.WEAPON_ENCHANTMENT,
        increase_percent=500.0,
    )

    assert result.final_chance == 1.0


def test_zero_baseline_attacks_stay_zero_even_with_chance_increases() -> None:
    assert calculate_status_effect_chance(
        StatusEffectChanceSource.LIGHT_ATTACK,
        increase_percent=365.0,
    ).final_chance == 0.0
    assert calculate_status_effect_chance(
        StatusEffectChanceSource.HEAVY_ATTACK,
        increase_percent=365.0,
    ).final_chance == 0.0


def test_negative_chance_increase_fails_closed() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        calculate_status_effect_chance(
            StatusEffectChanceSource.SINGLE_TARGET_DIRECT,
            increase_percent=-1.0,
        )
