from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranchKind,
)
from services.extreme_subclass_slot_allocation_service import ExtremeSubclassSlotAllocationService
from tools.audit_extreme_magicka_recovery_oakensoul_vs_torc import (
    MAJOR_INTELLECT_PERCENT,
    _score,
)


def test_oakensoul_one_bar_rule_keeps_reviewed_six_slot_active_bar():
    branch = ExtremeGearSetRecoverySpecialBranchService.classify(
        set_name="Oakensoul Ring",
        piece_count=1,
        description=(
            "While equipped, you are unable to swap between your Primary and Backup Weapon Sets "
            "and gain Minor Fortitude, Minor Intellect, and Minor Endurance."
        ),
        objective_key="magicka_recovery",
    )
    assert branch is not None
    assert branch.kind is ExtremeRecoverySpecialBranchKind.SEARCH_STATE_MUTATION
    assert branch.search_state_rule == "one_bar_only"
    assert branch.percent_ceiling == 15.0
    assert ExtremeSubclassSlotAllocationService.ACTIVE_BAR_SLOTS == 6


def test_legal_torc_beats_equal_structure_oakensoul_at_named_gear_layer():
    shared = 3702.294
    structural = 1032.0
    torc = _score(shared=shared, structural=structural, flat_special=450.0)
    oak = _score(shared=shared, structural=structural, extra_percent=0.15)
    assert torc > oak


def test_legal_torc_still_beats_equal_structure_oakensoul_with_major_intellect():
    shared = 3702.294
    structural = 1032.0
    torc = _score(
        shared=shared,
        structural=structural,
        flat_special=450.0,
        common_percent=MAJOR_INTELLECT_PERCENT,
    )
    oak = _score(
        shared=shared,
        structural=structural,
        extra_percent=0.15,
        common_percent=MAJOR_INTELLECT_PERCENT,
    )
    assert torc > oak


def test_common_major_intellect_is_not_assumed_rank_neutral():
    shared = 3702.294
    torc_structure = 1032.0
    oak_structure = 1100.0
    named_gap = (
        _score(shared=shared, structural=torc_structure, flat_special=450.0)
        - _score(shared=shared, structural=oak_structure, extra_percent=0.15)
    )
    potion_gap = (
        _score(
            shared=shared,
            structural=torc_structure,
            flat_special=450.0,
            common_percent=MAJOR_INTELLECT_PERCENT,
        )
        - _score(
            shared=shared,
            structural=oak_structure,
            extra_percent=0.15,
            common_percent=MAJOR_INTELLECT_PERCENT,
        )
    )
    assert named_gap != potion_gap
