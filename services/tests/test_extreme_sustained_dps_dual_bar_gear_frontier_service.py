from __future__ import annotations

import pytest

from types import SimpleNamespace

from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)
from services.extreme_sustained_dps_dual_bar_gear_frontier_service import (
    ExtremeSustainedDPSDualBarGearFrontierService,
)


def _realization(*, shared_set: int, weapon_set: int, weapon_type: str):
    shared_name = f"Shared {shared_set}"
    weapon_name = f"Weapon {weapon_set}"
    return ExtremeNamedGearSetRealization(
        topology_signature="5+2|unused:5",
        set_ids=(shared_set, weapon_set),
        set_names=(shared_name, weapon_name),
        counts=(5, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment("Head", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment("Shoulders", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment("Chest", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment("Hands", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment("Waist", shared_set, shared_name),
            ExtremeNamedGearSlotAssignment(
                "Main Hand", weapon_set, weapon_name, weapon_type
            ),
        ),
    )


def _branch(index, realizations=(), *, proven=True, unresolved=()):
    return SimpleNamespace(
        topology_index=index,
        denominator_proven=proven,
        unresolved=tuple(unresolved),
        result=SimpleNamespace(realizations=tuple(realizations)),
    )


def test_complete_topology_coverage_can_prove_dual_bar_denominator() -> None:
    front = _realization(shared_set=10, weapon_set=20, weapon_type="Inferno Staff")
    back = _realization(shared_set=10, weapon_set=30, weapon_type="Restoration Staff")

    result = ExtremeSustainedDPSDualBarGearFrontierService.build(
        (
            _branch(0, (front,)),
            _branch(1, (back,)),
            _branch(2, ()),
        ),
        expected_topology_count=3,
    )

    assert result.supplied_topology_count == 3
    assert result.proven_topology_count == 3
    assert result.denominator_proven is True
    assert result.active_snapshot_count == 2
    assert result.dual_bar_state_count == 4
    assert result.unresolved == ()


def test_missing_topology_branch_keeps_dual_bar_denominator_open() -> None:
    row = _realization(shared_set=10, weapon_set=20, weapon_type="Inferno Staff")

    result = ExtremeSustainedDPSDualBarGearFrontierService.build(
        (_branch(0, (row,)),),
        expected_topology_count=2,
    )

    assert result.denominator_proven is False
    assert any("Missing" in item for item in result.unresolved)


def test_unproven_source_branch_keeps_dual_bar_denominator_open() -> None:
    row = _realization(shared_set=10, weapon_set=20, weapon_type="Inferno Staff")

    result = ExtremeSustainedDPSDualBarGearFrontierService.build(
        (
            _branch(0, (row,)),
            _branch(1, (), proven=False, unresolved=("branch truncated",)),
        ),
        expected_topology_count=2,
    )

    assert result.denominator_proven is False
    assert any("branch truncated" in item for item in result.unresolved)


def test_duplicate_topology_index_fails_closed() -> None:
    result = ExtremeSustainedDPSDualBarGearFrontierService.build(
        (_branch(0), _branch(0)),
        expected_topology_count=1,
    )

    assert result.denominator_proven is False
    assert any("Duplicate" in item for item in result.unresolved)


def test_out_of_range_topology_index_fails_closed() -> None:
    result = ExtremeSustainedDPSDualBarGearFrontierService.build(
        (_branch(2),),
        expected_topology_count=1,
    )

    assert result.denominator_proven is False
    assert any("outside expected" in item for item in result.unresolved)


def test_dual_bar_frontier_rejects_boolean_expected_topology_count() -> None:
    with pytest.raises(TypeError, match="expected_topology_count must be an integer"):
        ExtremeSustainedDPSDualBarGearFrontierService.build(
            (),
            expected_topology_count=True,
        )


def test_dual_bar_frontier_rejects_truthy_branch_denominator_proof() -> None:
    with pytest.raises(TypeError, match="branch denominator_proven must be boolean"):
        ExtremeSustainedDPSDualBarGearFrontierService.build(
            (_branch(0, proven="true"),),
            expected_topology_count=1,
        )


def test_dual_bar_frontier_rejects_boolean_branch_index() -> None:
    with pytest.raises(TypeError, match="topology_index must be an integer"):
        ExtremeSustainedDPSDualBarGearFrontierService.build(
            (_branch(True),),
            expected_topology_count=1,
        )


def test_dual_bar_frontier_rejects_mutable_branch_unresolved() -> None:
    branch = _branch(0)
    branch.unresolved = ["open"]

    with pytest.raises(TypeError, match="branch unresolved must be a tuple"):
        ExtremeSustainedDPSDualBarGearFrontierService.build(
            (branch,),
            expected_topology_count=1,
        )
