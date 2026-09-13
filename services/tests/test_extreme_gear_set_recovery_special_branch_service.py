from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranchKind,
)


def _classify(description: str, *, name: str = "Fixture", pieces: int = 5):
    row = ExtremeGearSetRecoverySpecialBranchService.classify(
        set_name=name,
        piece_count=pieces,
        description=description,
        objective_key="health_recovery",
    )
    assert row is not None
    return row


def test_classifies_conditional_flat_without_borrowing_other_stat_range():
    row = _classify(
        "While you have a food buff active, your Max Health is increased by 58-2500 "
        "and Health Recovery by 8-356."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.CONDITIONAL_FLAT
    assert row.flat_ceiling == 356.0
    assert row.can_raise_self


def test_classifies_major_fortitude_as_named_buff():
    row = _classify(
        "You gain Major Fortitude, increasing your Health Recovery by 30%."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.NAMED_BUFF
    assert row.percent_ceiling == 30.0


def test_classifies_willows_path_percent():
    row = _classify(
        "Increases your Health, Magicka, and Stamina Recovery by 18%."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.CONDITIONAL_PERCENT
    assert row.percent_ceiling == 18.0


def test_classifies_roksa_stack_ceiling():
    row = _classify(
        "Each second you are in combat, gain a stack of Darklight, up to 30 stacks max. "
        "Each stack of Darklight increases your Stamina Recovery, Magicka Recovery, "
        "and Health Recovery by 8."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.STACKED_FLAT
    assert row.flat_ceiling == 240.0


def test_classifies_enemy_recovery_reduction_as_non_challenger():
    row = _classify(
        "Enemies in the area have their healing received and Health Recovery reduced by 6%."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.NEGATIVE_ONLY
    assert not row.can_raise_self


def test_classifies_cannot_affect_self_as_non_challenger():
    row = _classify(
        "Group members within the zone increase their Health Recovery by 950. "
        "The Health Recovery cannot affect yourself.",
        name="Syrabane's Ward",
        pieces=1,
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.SELF_INELIGIBLE
    assert not row.can_raise_self


def test_classifies_oakensoul_as_positive_search_state_mutation():
    row = _classify(
        "While equipped, you are unable to swap between your Primary and Backup Weapon Sets "
        "and gain Minor Fortitude, Minor Intellect, and Minor Endurance.",
        name="Oakensoul Ring",
        pieces=1,
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.SEARCH_STATE_MUTATION
    assert row.search_state_rule == "one_bar_only"
    assert row.percent_ceiling == 15.0
    assert row.can_raise_self


def test_classifies_torc_as_nonpositive_search_state_mutation():
    row = _classify(
        "Adds 500 Magicka and Stamina Recovery. Disable all other item set bonuses.",
        name="Torc of the Last Ayleid King",
        pieces=1,
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.SEARCH_STATE_MUTATION
    assert row.search_state_rule == "suppresses_other_set_bonuses"
    assert not row.can_raise_self


def test_classifies_alessian_formula_cap():
    row = _classify(
        "Increase your Health Recovery by 2% of your sum total Physical Resistance and "
        "Spell Resistance, up to a maximum of 1320."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.FORMULA
    assert row.flat_ceiling == 1320.0
