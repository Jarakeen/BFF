from minmax.gear_sets import GearSetBonus
from services.extreme_gear_search_state_rule_service import (
    ExtremeGearSearchStateRule,
    ExtremeGearSearchStateRuleService,
)


def _bonus(text: str) -> tuple[GearSetBonus, ...]:
    return (GearSetBonus(id=1, set_id=1, piece_count=1, description=text),)


def test_oakensoul_maps_one_bar_rule_without_retaining_max_resource_candidate():
    row = ExtremeGearSearchStateRuleService.review(
        "Oakensoul Ring",
        _bonus(
            "(1 item) While equipped, you are unable to swap between your Primary and Backup Weapon Sets "
            "and gain Minor Berserk."
        ),
    )
    assert row is not None
    assert row.rule is ExtremeGearSearchStateRule.ONE_BAR_ONLY
    assert row.retains_max_resource_candidate is False


def test_torc_maps_set_suppression_rule():
    row = ExtremeGearSearchStateRuleService.review(
        "Torc of the Last Ayleid King",
        _bonus(
            "(1 item) Reduce your damage taken by 15%. Adds 1337 Weapon and Spell Damage. "
            "Adds 500 Magicka and Stamina Recovery. Disable all other item set bonuses."
        ),
    )
    assert row is not None
    assert row.rule is ExtremeGearSearchStateRule.SUPPRESSES_OTHER_SET_BONUSES
    assert row.retains_max_resource_candidate is False


def test_twice_born_star_maps_two_mundus_rule_and_stays_in_resource_search():
    row = ExtremeGearSearchStateRuleService.review(
        "Twice-Born Star",
        _bonus("(5 items) You can have two Mundus Stone boons at the same time."),
    )
    assert row is not None
    assert row.rule is ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS
    assert row.retains_max_resource_candidate is True


def test_name_and_mechanic_text_must_both_match():
    assert ExtremeGearSearchStateRuleService.review(
        "Some Other Set",
        _bonus("(5 items) You can have two Mundus Stone boons at the same time."),
    ) is None
    assert ExtremeGearSearchStateRuleService.review(
        "Twice-Born Star",
        _bonus("(5 items) Adds 1000 Maximum Health."),
    ) is None
