from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranchKind,
)


def _classify(
    description: str,
    *,
    name: str = "Fixture",
    pieces: int = 5,
    objective_key: str = "health_recovery",
):
    row = ExtremeGearSetRecoverySpecialBranchService.classify(
        set_name=name,
        piece_count=pieces,
        description=description,
        objective_key=objective_key,
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


def test_classifies_parallel_flat_reward_clause_without_borrowing_damage_range():
    row = _classify(
        "When you cast an ability that grants Major or Minor Resolve while in combat, "
        "you gain 7-341 Weapon and Spell Damage and 7-341 Health Recovery for 15 seconds."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.CONDITIONAL_FLAT
    assert row.flat_ceiling == 341.0
    assert row.can_raise_self


def test_classifies_major_fortitude_as_named_buff():
    row = _classify("You gain Major Fortitude, increasing your Health Recovery by 30%.")
    assert row.kind is ExtremeRecoverySpecialBranchKind.NAMED_BUFF
    assert row.percent_ceiling == 30.0


def test_classifies_willows_path_percent():
    row = _classify("Increases your Health, Magicka, and Stamina Recovery by 18%.")
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


def test_classifies_bastion_per_stack_ceiling():
    row = _classify(
        "Blocking an attack grants you a stack of Inflection for 10 seconds, up to 3 stacks max. "
        "You can gain up to 1 stack every 0.5 seconds. Increase your Magicka and Stamina Recovery "
        "by 106 per stack of Inflection.",
        name="Bastion of the Draoife",
        objective_key="magicka_recovery",
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.STACKED_FLAT
    assert row.flat_ceiling == 318.0
    assert row.can_raise_self


def test_classifies_wrathsun_grants_per_stack_ceiling():
    row = _classify(
        "When you deal damage with a Dawn's Wrath ability, you gain a stack of Sunlight for 15 seconds, "
        "once per attack and up to 30 times. Each stack grants 21 Magicka Recovery. When at max stacks, "
        "stacks no longer refresh.",
        name="Wrathsun",
        objective_key="magicka_recovery",
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.STACKED_FLAT
    assert row.flat_ceiling == 630.0
    assert row.can_raise_self


def test_classifies_max_resource_scaled_recovery_formula():
    row = _classify(
        "Gain 1 Magicka Recovery for every 100 Max Magicka you have. Current Increase: 120 Magicka Recovery.",
        name="Three Queens Wellspring",
        objective_key="magicka_recovery",
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.FORMULA
    assert row.flat_ceiling is None
    assert row.formula_numerator == 1.0
    assert row.formula_denominator == 100.0
    assert row.formula_resource == "max_magicka"
    assert row.condition == "max_magicka_scaled"
    assert row.can_raise_self


def test_classifies_enemy_recovery_reduction_as_non_challenger():
    row = _classify("Enemies in the area have their healing received and Health Recovery reduced by 6%.")
    assert row.kind is ExtremeRecoverySpecialBranchKind.NEGATIVE_ONLY
    assert not row.can_raise_self


def test_classifies_embedded_thurvokun_reduction_as_non_challenger():
    row = _classify(
        "Enemies are afflicted with Minor Maim and the Diseased status, reducing their "
        "damage done by 5% and healing received and Health Recovery by 6%."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.NEGATIVE_ONLY
    assert not row.can_raise_self


def test_classifies_reordered_shared_recovery_reduction_as_non_challenger():
    row = _classify(
        "When max Skirmish ends, your Stamina, Magicka, and Health Recovery are reduced by 422 for 10 seconds.",
        name="The Ruckus",
        pieces=2,
        objective_key="magicka_recovery",
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.NEGATIVE_ONLY
    assert not row.can_raise_self


def test_classifies_cannot_affect_self_as_non_challenger():
    row = _classify(
        "Group members within the zone increase their Health Recovery by 950. The Health Recovery cannot affect yourself.",
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


def test_classifies_second_mundus_as_positive_search_state_mutation():
    row = _classify(
        "You can have two Mundus Stone boons at the same time.",
        name="Twice-Born Star",
        pieces=5,
        objective_key="magicka_recovery",
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.SEARCH_STATE_MUTATION
    assert row.search_state_rule == "allows_two_mundus"
    assert row.condition == "second_mundus"
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
        "Increase your Health Recovery by 2% of your sum total Physical Resistance and Spell Resistance, up to a maximum of 1320."
    )
    assert row.kind is ExtremeRecoverySpecialBranchKind.FORMULA
    assert row.flat_ceiling == 1320.0
