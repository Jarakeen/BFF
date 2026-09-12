from __future__ import annotations

from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_max_resource_named_gear_realization_adapter_service import (
    ExtremeMaxResourceNamedGearRealizationAdapterService,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchResult,
    ExtremeOrdinaryNamedGearSearchStats,
    ExtremeOrdinaryNamedGearTopologyWinner,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)


def _topology() -> ExtremeGearSetCountTopology:
    return ExtremeGearSetCountTopology(counts=(2,), unused_units=10)


def _realization() -> ExtremeNamedGearSetRealization:
    topology = _topology()
    return ExtremeNamedGearSetRealization(
        topology_signature=topology.signature,
        set_ids=(10,),
        set_names=("Set 10",),
        counts=(2,),
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment(
                slot="Main Hand",
                set_id=10,
                set_name="Set 10",
                weapon_type="Inferno Staff",
            ),
        ),
    )


def _search(objective: str, *, special=()) -> ExtremeMaxResourceOrdinaryNamedGearSearchResult:
    topology = _topology()
    return ExtremeMaxResourceOrdinaryNamedGearSearchResult(
        objective_key=objective,
        topologies=(
            ExtremeOrdinaryNamedGearTopologyWinner(
                topology=topology,
                best_exact_flat_delta=1000.0,
                realizations=(_realization(),),
                stats=ExtremeOrdinaryNamedGearSearchStats(),
            ),
        ),
        equivalent_breakpoints_pruned=3,
        frontier_breakpoints_pruned=2,
        representative_limit=4,
        special_or_nonflat_pairs=tuple(special),
        unresolved=(),
    )


def _catalog() -> ExtremeGearSetTopologyCatalog:
    return ExtremeGearSetTopologyCatalog(sets=(), topologies=(_topology(),))


def _relevance(objective: str) -> ExtremeGearSetObjectiveRelevanceCatalog:
    return ExtremeGearSetObjectiveRelevanceCatalog(objective_key=objective, evidence=())


def test_max_magicka_ordinary_frontier_closes_legacy_denominator() -> None:
    result = ExtremeMaxResourceNamedGearRealizationAdapterService.build(
        search=_search("max_magicka"),
        topology_catalog=_catalog(),
        relevance=_relevance("max_magicka"),
    )

    assert result.objective_key == "max_magicka"
    assert result.candidate_reduction_proven is True
    assert result.denominator_proven is True
    assert result.assignments_realized == 1
    assert result.breakpoints_pruned_equivalent == 3


def test_max_stamina_ordinary_frontier_closes_legacy_denominator() -> None:
    result = ExtremeMaxResourceNamedGearRealizationAdapterService.build(
        search=_search("max_stamina"),
        topology_catalog=_catalog(),
        relevance=_relevance("max_stamina"),
    )

    assert result.objective_key == "max_stamina"
    assert result.candidate_reduction_proven is True
    assert result.denominator_proven is True


def test_nonordinary_resource_branch_fails_closed() -> None:
    result = ExtremeMaxResourceNamedGearRealizationAdapterService.build(
        search=_search("max_magicka", special=((99, "Odd Set", 5),)),
        topology_catalog=_catalog(),
        relevance=_relevance("max_magicka"),
    )

    assert result.candidate_reduction_proven is False
    assert result.denominator_proven is False
    assert any("Odd Set" in item for item in result.unresolved)
