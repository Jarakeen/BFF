from __future__ import annotations

"""Shared joint identity/physical precheck for ordinary max-resource gear search.

The ordinary branch-and-bound optimizer is score ordered. That is ideal once a
legal realization exists, but pathological for topologies that are impossible
only after identity and slot legality are considered together. This service adds
a proof-safe feasibility-only pass before score search. It uses the same canonical
candidate frontier and partial physical feasibility contract, but orders topology
positions by domain size so constrained breakpoint classes are proven first.

No score, objective delta, or winner semantics live here. A False result proves
that no concrete ordinary assignment can satisfy both distinct identity and exact
active-snapshot physical legality. A True result merely permits the existing exact
optimizer to run. The service therefore applies equally to Max Health, Max Magicka,
and Max Stamina.
"""

from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchResult,
    ExtremeMaxResourceOrdinaryNamedGearSearchService,
    ExtremeOrdinaryNamedGearTopologyWinner,
    _Candidate,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)
from services.extreme_partial_named_gear_physical_feasibility_service import (
    ExtremePartialNamedGearPhysicalFeasibilityService,
)


class ExtremeMaxResourceJointFeasibilitySearchService(
    ExtremeMaxResourceOrdinaryNamedGearSearchService
):
    """Exact ordinary max-resource search with a joint legality precheck."""

    @staticmethod
    def _slot_span(row: _Candidate) -> int:
        eligibility = row.eligibility
        jewelry = 0
        if "Necklace" in eligibility.jewelry_slots:
            jewelry += 1
        if "Ring" in eligibility.jewelry_slots:
            jewelry += 2
        return (
            len(tuple(eligibility.armor_slots))
            + jewelry
            + len(tuple(eligibility.weapon_types))
        )

    @classmethod
    def _joint_legality_possible(
        cls,
        *,
        topology: ExtremeGearSetCountTopology,
        candidates_by_count: dict[int, tuple[_Candidate, ...]],
        feasibility: ExtremePartialNamedGearPhysicalFeasibilityService,
    ) -> bool:
        """Prove existence of one concrete distinct-ID physical assignment.

        Set identities are labels in a topology, so reordering the count vector for
        this feasibility-only search does not change the legal universe. Positions
        with smaller candidate domains are searched first; ties prefer physically
        narrower domains. The temporary topology preserves the exact count multiset,
        unused units, and total active-snapshot units.
        """

        positions: list[tuple[int, tuple[_Candidate, ...]]] = []
        for count in topology.counts:
            rows = tuple(candidates_by_count.get(int(count), ()))
            if not rows:
                return False
            positions.append((int(count), rows))

        positions.sort(
            key=lambda item: (
                len(item[1]),
                min((cls._slot_span(row) for row in item[1]), default=0),
                int(item[0]),
            )
        )
        probe_counts = tuple(count for count, _rows in positions)
        probe = ExtremeGearSetCountTopology(
            counts=probe_counts,
            unused_units=int(topology.unused_units),
            total_units=int(topology.total_units),
        )
        domains = tuple(
            tuple(
                sorted(
                    rows,
                    key=lambda row: (
                        cls._slot_span(row),
                        row.eligibility.category.strip().casefold(),
                        int(row.set_id),
                    ),
                )
            )
            for _count, rows in positions
        )

        selected: list[_Candidate] = []
        used_ids: set[int] = set()
        failed_states: set[tuple[int, tuple[int, ...], tuple[tuple[object, ...], ...]]] = set()

        def visit(position: int) -> bool:
            if position >= len(probe_counts):
                return True

            shape_key = tuple(
                feasibility._cached_shape(row.eligibility)
                for row in selected
            )
            state = (position, tuple(sorted(used_ids)), shape_key)
            if state in failed_states:
                return False

            previous_equal_id: int | None = None
            if position > 0 and probe_counts[position - 1] == probe_counts[position]:
                previous_equal_id = selected[position - 1].set_id

            for row in domains[position]:
                set_id = int(row.set_id)
                if set_id in used_ids:
                    continue
                if previous_equal_id is not None and set_id <= previous_equal_id:
                    continue

                selected.append(row)
                used_ids.add(set_id)
                physical = tuple(item.eligibility for item in selected)
                possible = feasibility.is_possible(probe, physical)
                if possible and visit(position + 1):
                    used_ids.remove(set_id)
                    selected.pop()
                    return True
                used_ids.remove(set_id)
                selected.pop()

            failed_states.add(state)
            return False

        return visit(0)

    def search(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
    ) -> ExtremeMaxResourceOrdinaryNamedGearSearchResult:
        objective = str(self.relevance.objective_key or "").strip().casefold()
        if objective not in self.SUPPORTED_OBJECTIVES:
            raise ValueError(
                "ordinary named-gear branch-and-bound supports only max-resource objectives"
            )

        reducer = ExtremeObjectiveNamedGearSetCatalogRealizationService(
            breakpoints=self.breakpoints,
            eligibility=self.eligibility,
            relevance=self.relevance,
        )
        reduced, equivalent_pruned, representative_limit = reducer.proof_reduced_breakpoints(
            topology_catalog
        )
        frontier, frontier_pruned = self._frontier(reduced, representative_limit)
        candidates, special = self._candidates(frontier)
        feasibility = ExtremePartialNamedGearPhysicalFeasibilityService()

        winners: list[ExtremeOrdinaryNamedGearTopologyWinner] = []
        for topology in topology_catalog.topologies:
            counts = tuple(int(value) for value in topology.counts)
            if not self._identity_legality_possible(
                counts=counts,
                candidates_by_count=candidates,
            ):
                winners.append(
                    ExtremeOrdinaryNamedGearTopologyWinner(
                        topology=topology,
                        best_exact_flat_delta=None,
                        realizations=(),
                        stats=self._stats(),
                    )
                )
                continue
            if not self._physical_shape_legality_possible(
                topology=topology,
                counts=counts,
                candidates_by_count=candidates,
                feasibility=feasibility,
            ):
                winners.append(
                    ExtremeOrdinaryNamedGearTopologyWinner(
                        topology=topology,
                        best_exact_flat_delta=None,
                        realizations=(),
                        stats=self._stats(),
                    )
                )
                continue
            if not self._joint_legality_possible(
                topology=topology,
                candidates_by_count=candidates,
                feasibility=feasibility,
            ):
                winners.append(
                    ExtremeOrdinaryNamedGearTopologyWinner(
                        topology=topology,
                        best_exact_flat_delta=None,
                        realizations=(),
                        stats=self._stats(),
                    )
                )
                continue
            winners.append(
                self._search_topology(
                    topology,
                    candidates,
                    frontier,
                    feasibility=feasibility,
                )
            )

        unresolved = tuple(
            dict.fromkeys(
                (
                    *topology_catalog.unresolved,
                    *frontier.unresolved,
                    *self.relevance.unresolved,
                )
            )
        )
        return ExtremeMaxResourceOrdinaryNamedGearSearchResult(
            objective_key=objective,
            topologies=tuple(winners),
            equivalent_breakpoints_pruned=int(equivalent_pruned),
            frontier_breakpoints_pruned=int(frontier_pruned),
            representative_limit=int(representative_limit),
            special_or_nonflat_pairs=special,
            unresolved=unresolved,
        )


__all__ = ["ExtremeMaxResourceJointFeasibilitySearchService"]
