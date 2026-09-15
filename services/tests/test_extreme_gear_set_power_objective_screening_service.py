import pytest

from services.extreme_gear_set_power_objective_screening_service import (
    ExtremeGearSetPowerObjectiveScreeningService,
)


def test_damage_scaling_from_power_is_not_a_sheet_power_mutation() -> None:
    result = ExtremeGearSetPowerObjectiveScreeningService.review(
        "Deal 1000 Flame Damage. This effect scales off the higher of your Weapon or Spell Damage.",
        "weapon_damage",
    )

    assert result.proven_irrelevant
    assert result.blockers == ()


def test_direct_self_power_increase_remains_a_blocker() -> None:
    result = ExtremeGearSetPowerObjectiveScreeningService.review(
        "When you deal damage, increase your Weapon and Spell Damage by 490 for 8 seconds.",
        "weapon_damage",
    )

    assert not result.proven_irrelevant
    assert result.power_hazards == ("direct self Weapon/Spell Damage mutation",)


def test_enemy_power_reduction_is_irrelevant_to_own_sheet_power() -> None:
    result = ExtremeGearSetPowerObjectiveScreeningService.review(
        "Reduce the attacker's Weapon and Spell Damage by 300 for 5 seconds.",
        "weapon_damage",
    )

    assert result.proven_irrelevant


def test_named_buff_is_scoped_to_the_requested_power_stat() -> None:
    weapon = ExtremeGearSetPowerObjectiveScreeningService.review(
        "Gain Major Brutality for 20 seconds.",
        "weapon_damage",
    )
    spell = ExtremeGearSetPowerObjectiveScreeningService.review(
        "Gain Major Brutality for 20 seconds.",
        "spell_damage",
    )

    assert not weapon.proven_irrelevant
    assert spell.proven_irrelevant


def test_weapon_trait_effectiveness_remains_a_global_search_hazard() -> None:
    result = ExtremeGearSetPowerObjectiveScreeningService.review(
        "Increase the effectiveness of your Weapon Traits by 100%.",
        "weapon_damage",
    )

    assert not result.proven_irrelevant
    assert result.global_equipment_hazards


def test_unknown_power_objective_fails_closed() -> None:
    with pytest.raises(KeyError, match="unreviewed Extreme power screening objective"):
        ExtremeGearSetPowerObjectiveScreeningService.review("Anything", "actual_damage")
