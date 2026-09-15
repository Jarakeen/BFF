import pytest

from services.extreme_gear_set_power_upper_bound_service import (
    ExtremeGearSetPowerUpperBoundService,
)


def _bound(description: str):
    return ExtremeGearSetPowerUpperBoundService.build(description, "weapon_damage")


def test_range_power_proc_uses_reviewed_maximum() -> None:
    result = _bound(
        "When healed, increase your Weapon and Spell Damage by 8-369 for 5 seconds."
    )

    assert result.flat_upper_bound == 369.0
    assert result.denominator_proven


def test_per_stack_power_uses_stated_stack_ceiling() -> None:
    result = _bound(
        "Each stack grants you 2-100 Weapon and Spell Damage, up to 10 stacks."
    )

    assert result.flat_upper_bound == 1000.0
    assert "10 stated stacks" in result.assumptions[0]
    assert result.denominator_proven


def test_per_enemy_power_uses_stated_enemy_ceiling() -> None:
    result = _bound(
        "Gain 0-34 Weapon and Spell Damage for each enemy hit, up to 6 enemies."
    )

    assert result.flat_upper_bound == 204.0
    assert result.denominator_proven


def test_named_courage_and_brutality_preserve_distinct_buckets() -> None:
    result = _bound("Gain Minor Courage and Major Brutality while equipped.")

    assert result.flat_upper_bound == 215.0
    assert result.percent_upper_bound == 0.2
    assert result.named_buffs == ("Major Brutality", "Minor Courage")
    assert result.denominator_proven


def test_independent_named_buffs_and_direct_grant_are_summed_conservatively() -> None:
    result = _bound(
        "Gain Minor Courage and Major Courage, and increase your Weapon and Spell Damage by 100."
    )

    assert result.flat_upper_bound == 745.0
    assert result.denominator_proven


def test_direct_percentage_power_stays_in_percentage_bucket() -> None:
    result = _bound("Increase your Weapon and Spell Damage by 20% while active.")

    assert result.flat_upper_bound == 0.0
    assert result.percent_upper_bound == 0.2
    assert result.denominator_proven


def test_formula_without_finite_denominator_fails_closed() -> None:
    result = _bound(
        "Gain 20 Weapon and Spell Damage against enemies for each Minor Buff they have active."
    )

    assert not result.denominator_proven
    assert "finite named-buff denominator" in result.unresolved[0]


@pytest.mark.parametrize(
    "description, fragment",
    (
        (
            "Gain Weapon and Spell Damage equal to the amount of total Ultimate consumed.",
            "Ultimate ceiling",
        ),
        (
            "Increase the effectiveness of your Weapon Traits by 100%.",
            "weapon-trait amplification",
        ),
        (
            "You can have two Mundus Stone boons at the same time.",
            "second-Mundus power",
        ),
    ),
)
def test_nonflat_search_formulas_remain_explicit(description: str, fragment: str) -> None:
    result = _bound(description)

    assert not result.denominator_proven
    assert any(fragment in row for row in result.unresolved)


def test_scaling_only_proc_has_zero_proven_power_ceiling() -> None:
    result = _bound(
        "Deal 1000 Flame Damage. This effect scales off the higher of your Weapon or Spell Damage."
    )

    assert result.flat_upper_bound == 0.0
    assert result.denominator_proven


def test_unknown_objective_fails_closed() -> None:
    with pytest.raises(KeyError, match="unreviewed Extreme power upper-bound objective"):
        ExtremeGearSetPowerUpperBoundService.build("Anything", "actual_damage")
