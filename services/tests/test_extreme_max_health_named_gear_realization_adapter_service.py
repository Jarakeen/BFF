from __future__ import annotations

from types import SimpleNamespace

from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_max_health_named_gear_realization_adapter_service import (
    ExtremeMaxHealthNamedGearRealizationAdapterService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)


def _realization() -> ExtremeNamedGearSetRealization:
    topology = ExtremeGearSetCountTopology(counts=(2,), unused_units=10)
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


def _search(*, proven: bool):
    return SimpleNamespace(
        candidate_realizations=(_realization(),),
        candidate_reduction_proven=proven,
        unresolved=(),
        ordinary=SimpleNamespace(
            equivalent_breakpoints_pruned=0,
            representative_limit=1,
        ),
    )


def _topology_catalog() -> ExtremeGearSetTopologyCatalog:
    topology = ExtremeGearSetCountTopology(counts=(2,), unused_units=10)
    return ExtremeGearSetTopologyCatalog(sets=(), topologies=(topology,))


def _relevance() -> ExtremeGearSetObjectiveRelevanceCatalog:
    return ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=(),
    )


def test_proven_reduced_frontier_survives_canonical_dual_bar_admissibility() -> None:
    result = ExtremeMaxHealthNamedGearRealizationAdapterService.build(
        search=_search(proven=True),
        topology_catalog=_topology_catalog(),
        relevance=_relevance(),
    )

    assert result.candidate_reduction_proven is True
    assert result.denominator_proven is True
    assert result.assignments_realized == 1
    assert result.realization.topologies[0].realizations[0].set_ids == (10,)


def test_unproven_candidate_reduction_cannot_close_legacy_denominator() -> None:
    result = ExtremeMaxHealthNamedGearRealizationAdapterService.build(
        search=_search(proven=False),
        topology_catalog=_topology_catalog(),
        relevance=_relevance(),
    )

    assert result.candidate_reduction_proven is False
    assert result.denominator_proven is False
