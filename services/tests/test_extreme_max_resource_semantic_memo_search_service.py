from __future__ import annotations

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_max_resource_ordinary_named_gear_search_service import _Candidate
from services.extreme_max_resource_semantic_memo_search_service import (
    ExtremeMaxResourceSemanticMemoSearchService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)

_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_WEAPONS = (
    "Axe",
    "Mace",
    "Sword",
    "Dagger",
    "Shield",
    "Two-Handed Sword",
    "Two-Handed Axe",
    "Two-Handed Mace",
    "Bow",
    "Restoration Staff",
    "Inferno Staff",
    "Ice Staff",
    "Lightning Staff",
)


def _eligibility(set_id: int) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=f"Set {set_id}",
        category="Trial",
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )


def _service(set_ids: tuple[int, ...]) -> ExtremeMaxResourceSemanticMemoSearchService:
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=tuple(_eligibility(set_id) for set_id in sorted(set(set_ids)))
    )
    return ExtremeMaxResourceSemanticMemoSearchService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(sets=()),
        eligibility=eligibility,
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_magicka",
            evidence=(),
        ),
    )


def _frontier(rows: tuple[tuple[int, int], ...]) -> ExtremeGearSetBonusBreakpointCatalog:
    by_id: dict[int, set[int]] = {}
    for set_id, count in rows:
        by_id.setdefault(set_id, set()).add(count)
    return ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(
            ExtremeGearSetBonusBreakpoints(
                set_id=set_id,
                name=f"Set {set_id}",
                max_equip_count=5,
                bonus_counts=tuple(sorted(counts)),
            )
            for set_id, counts in sorted(by_id.items())
        )
    )


def test_semantic_memo_collapses_prefix_ids_that_cannot_reappear() -> None:
    signature_2 = (("same-two-piece-effect",),)
    signature_3 = (("same-three-piece-effect",),)
    candidates = {
        2: (
            _Candidate(10, "Set 10", 2, 1000.0, _eligibility(10), signature_2),
            _Candidate(20, "Set 20", 2, 1000.0, _eligibility(20), signature_2),
        ),
        3: (
            _Candidate(30, "Set 30", 3, 500.0, _eligibility(30), signature_3),
            _Candidate(40, "Set 40", 3, 500.0, _eligibility(40), signature_3),
        ),
    }
    service = _service((10, 20, 30, 40))
    topology = ExtremeGearSetCountTopology(counts=(2, 3), unused_units=7)

    winner = service._search_topology(
        topology,
        candidates,
        _frontier(((10, 2), (20, 2), (30, 3), (40, 3))),
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    assert winner.best_exact_flat_delta == 1500.0
    assert len(winner.realizations) == 1
    # Without prefix memo this tiny Cartesian case reaches four tied leaves.
    assert winner.stats.leaves < 4


def test_semantic_memo_keeps_used_identity_when_it_can_reappear_later() -> None:
    signature_2 = (("same-two-piece-effect",),)
    candidates = {
        2: (
            _Candidate(10, "Set 10", 2, 1000.0, _eligibility(10), signature_2),
            _Candidate(20, "Set 20", 2, 1000.0, _eligibility(20), signature_2),
        ),
        3: (
            _Candidate(10, "Set 10", 3, 5000.0, _eligibility(10), (("huge-three",),)),
            _Candidate(30, "Set 30", 3, 100.0, _eligibility(30), (("small-three",),)),
        ),
    }
    service = _service((10, 20, 30))
    topology = ExtremeGearSetCountTopology(counts=(2, 3), unused_units=7)

    winner = service._search_topology(
        topology,
        candidates,
        _frontier(((10, 2), (10, 3), (20, 2), (30, 3))),
        feasibility=ExtremePartialNamedGearPhysicalFeasibilityService(),
    )

    # The optimizer must preserve the branch that uses Set 20 at two pieces so Set
    # 10 remains available for its much stronger three-piece breakpoint.
    assert winner.best_exact_flat_delta == 6000.0
    assert {row.set_ids for row in winner.realizations} == {(20, 10)}
