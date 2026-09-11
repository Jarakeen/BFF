from __future__ import annotations

from types import SimpleNamespace

from minmax.gear_sets import GearSet, GearSetBonus
from models.build_model import PlayerBuild
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidenceService,
    ExtremeDualBarSetActivationScope,
)
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


class _Repository:
    def __init__(self):
        self.sets = {
            "Bar Set": GearSet(10, "Bar Set", "Trial", 5),
            "Arena Staff": GearSet(20, "Arena Staff", "Arena", 2),
        }
        self.bonuses = {
            10: tuple(
                GearSetBonus(index, 10, count, f"{count} piece")
                for index, count in enumerate((2, 3, 4, 5), start=1)
            ),
            20: (GearSetBonus(20, 20, 2, "arena effect"),),
        }

    def get_set(self, name):
        return self.sets.get(name)

    def get_bonuses(self, set_id):
        return list(self.bonuses.get(int(set_id), ()))


def _shared():
    return (
        ExtremeNamedGearSlotAssignment("Chest", 10, "Bar Set"),
        ExtremeNamedGearSlotAssignment("Legs", 10, "Bar Set"),
        ExtremeNamedGearSlotAssignment("Feet", 10, "Bar Set"),
    )


def _state():
    front = ExtremeNamedGearSetRealization(
        topology_signature="5|unused:7",
        set_ids=(10,),
        set_names=("Bar Set",),
        counts=(5,),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            *_shared(),
            ExtremeNamedGearSlotAssignment(
                "Main Hand", 10, "Bar Set", "Inferno Staff"
            ),
        ),
    )
    back = ExtremeNamedGearSetRealization(
        topology_signature="3+2|unused:7",
        set_ids=(10, 20),
        set_names=("Bar Set", "Arena Staff"),
        counts=(3, 2),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            *_shared(),
            ExtremeNamedGearSlotAssignment(
                "Main Hand", 20, "Arena Staff", "Inferno Staff"
            ),
        ),
    )
    return ExtremeDualBarGearState(front=front, back=back)


def _eligibility():
    return ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(
            ExtremeNamedGearSetSlotEligibility(
                set_id=10,
                name="Bar Set",
                category="Trial",
                max_equip_count=5,
                armor_slots=("Chest", "Legs", "Feet"),
                weapon_types=("Inferno Staff",),
            ),
            ExtremeNamedGearSetSlotEligibility(
                set_id=20,
                name="Arena Staff",
                category="Arena",
                max_equip_count=2,
                weapon_types=("Inferno Staff",),
            ),
        )
    )


def test_reports_front_bar_five_piece_and_back_bar_arena_activation():
    service = ExtremeDualBarSetActivationEvidenceService(
        repository=_Repository(),
        eligibility=_eligibility(),
    )

    result = service.build(_state(), build=PlayerBuild())

    assert result.denominator_proven is True
    rows = {row.set_name: row for row in result.evidence}

    bar_set = rows["Bar Set"]
    assert bar_set.front_count == 5
    assert bar_set.back_count == 3
    assert bar_set.front_active_breakpoints == (2, 3, 4, 5)
    assert bar_set.back_active_breakpoints == (2, 3)
    assert bar_set.highest_front_breakpoint == 5
    assert bar_set.highest_back_breakpoint == 3
    assert bar_set.activation_scope is ExtremeDualBarSetActivationScope.BOTH
    assert bar_set.weapon_only_two_piece is False

    arena = rows["Arena Staff"]
    assert arena.front_count == 0
    assert arena.back_count == 2
    assert arena.front_active_breakpoints == ()
    assert arena.back_active_breakpoints == (2,)
    assert arena.activation_scope is ExtremeDualBarSetActivationScope.BACK_ONLY
    assert arena.weapon_only_two_piece is True


def test_missing_slot_evidence_keeps_activation_proof_open():
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=tuple(row for row in _eligibility().sets if row.set_id != 20)
    )
    service = ExtremeDualBarSetActivationEvidenceService(
        repository=_Repository(),
        eligibility=eligibility,
    )

    result = service.build(_state())

    assert result.denominator_proven is False
    assert any("Arena Staff" in item and "slot-eligibility" in item for item in result.unresolved)


def test_conflicting_shared_gear_fails_closed_before_activation_projection():
    state = _state()
    bad_back = ExtremeNamedGearSetRealization(
        topology_signature=state.back.topology_signature,
        set_ids=state.back.set_ids,
        set_names=state.back.set_names,
        counts=state.back.counts,
        weapon_shape=state.back.weapon_shape,
        assignments=(
            ExtremeNamedGearSlotAssignment("Chest", 99, "Different Shared Set"),
            *state.back.assignments[1:],
        ),
    )
    service = ExtremeDualBarSetActivationEvidenceService(
        repository=_Repository(),
        eligibility=_eligibility(),
    )

    result = service.build(ExtremeDualBarGearState(front=state.front, back=bad_back))

    assert result.evidence == ()
    assert result.denominator_proven is False
    assert any("shared body/jewelry" in item for item in result.unresolved)
