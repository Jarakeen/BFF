from __future__ import annotations

"""Enumerate concrete named-set assignments for Extreme gear topologies.

This layer composes canonical set-bonus breakpoints, named physical-slot
eligibility, and exact slot-witness realization.  Equal-count topology parts are
symmetry-reduced by set id, so ``5(A)+5(B)`` and ``5(B)+5(A)`` are one named
assignment rather than two copies of the same equipment state.

A caller may cap assignments for exploratory/runtime use.  Any such truncation is
explicit and prevents denominator proof.  Exhaustive means exhaustive; a progress
bar is not a proof theorem.
"""

from dataclasses import dataclass

from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


@dataclass(frozen=True)
class ExtremeNamedGearSetTopologyRealizationResult:
    topology: ExtremeGearSetCountTopology
    realizations: tuple[ExtremeNamedGearSetRealization, ...]
    assignments_considered: int
    assignments_rejected: int
    truncated: bool = False
    unresolved: tuple[str, ...] = ()

    @property
    def assignments_realized(self) -> int:
        return len(self.realizations)

    @property
    def denominator_proven(self) -> bool:
        return not self.truncated and not self.unresolved


@dataclass(frozen=True)
class ExtremeNamedGearSetCatalogRealizationResult:
    topologies: tuple[ExtremeNamedGearSetTopologyRealizationResult, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def assignments_considered(self) -> int:
        return sum(row.assignments_considered for row in self.topologies)

    @property
    def assignments_realized(self) -> int:
        return sum(row.assignments_realized for row in self.topologies)

    @property
    def assignments_rejected(self) -> int:
        return sum(row.assignments_rejected for row in self.topologies)

    @property
    def truncated(self) -> bool:
        return any(row.truncated for row in self.topologies)

    @property
    def denominator_proven(self) -> bool:
        return bool(self.topologies) and not self.unresolved and all(
            row.denominator_proven for row in self.topologies
        )


class ExtremeNamedGearSetCatalogRealizationService:
    """Enumerate breakpoint-relevant named assignments and exact slot witnesses."""

    def __init__(
        self,
        *,
        breakpoints: ExtremeGearSetBonusBreakpointCatalog,
        eligibility: ExtremeNamedGearSetSlotEligibilityCatalog,
    ) -> None:
        self.breakpoints = breakpoints
        self.eligibility = eligibility
        self._breakpoint_by_id = {row.set_id: row for row in breakpoints.sets}
        self._eligibility_by_id = {row.set_id: row for row in eligibility.sets}

    def _candidates_for_count(self, count: int) -> tuple[ExtremeNamedGearSetSlotEligibility, ...]:
        rows: list[ExtremeNamedGearSetSlotEligibility] = []
        for set_id, breakpoint in self._breakpoint_by_id.items():
            if int(count) not in breakpoint.bonus_counts:
                continue
            eligibility = self._eligibility_by_id.get(set_id)
            if eligibility is None or not eligibility.has_physical_slot_evidence:
                continue
            if int(count) > int(eligibility.max_equip_count):
                continue
            rows.append(eligibility)
        rows.sort(key=lambda row: (row.set_id, row.name.casefold(), row.name))
        return tuple(rows)

    def realize_topology(
        self,
        topology: ExtremeGearSetCountTopology,
        *,
        max_assignments: int | None = None,
    ) -> ExtremeNamedGearSetTopologyRealizationResult:
        if max_assignments is not None and int(max_assignments) <= 0:
            raise ValueError("max_assignments must be positive when provided")

        unresolved = tuple(
            dict.fromkeys((*self.breakpoints.unresolved, *self.eligibility.unresolved))
        )
        counts = tuple(int(value) for value in topology.counts)
        candidate_rows = tuple(self._candidates_for_count(count) for count in counts)

        # The no-set baseline has exactly one named assignment: the empty tuple.
        if not counts:
            witness = ExtremeNamedGearSetRealizationService.find_witness(topology, ())
            return ExtremeNamedGearSetTopologyRealizationResult(
                topology=topology,
                realizations=(() if witness is None else (witness,)),
                assignments_considered=1,
                assignments_rejected=1 if witness is None else 0,
                unresolved=unresolved,
            )

        if any(not rows for rows in candidate_rows):
            return ExtremeNamedGearSetTopologyRealizationResult(
                topology=topology,
                realizations=(),
                assignments_considered=0,
                assignments_rejected=0,
                unresolved=unresolved,
            )

        realizations: list[ExtremeNamedGearSetRealization] = []
        selected: list[ExtremeNamedGearSetSlotEligibility] = []
        used_ids: set[int] = set()
        considered = 0
        rejected = 0
        truncated = False

        def visit(position: int) -> bool:
            nonlocal considered, rejected, truncated
            if position >= len(counts):
                if max_assignments is not None and considered >= int(max_assignments):
                    truncated = True
                    return False
                considered += 1
                witness = ExtremeNamedGearSetRealizationService.find_witness(
                    topology,
                    tuple(selected),
                )
                if witness is None:
                    rejected += 1
                else:
                    realizations.append(witness)
                return True

            count = counts[position]
            previous_equal_id: int | None = None
            if position > 0 and counts[position - 1] == count:
                previous_equal_id = int(selected[position - 1].set_id)

            for row in candidate_rows[position]:
                set_id = int(row.set_id)
                if set_id in used_ids:
                    continue
                # Equal-count topology parts are indistinguishable.  Canonical
                # ascending set ids remove permutation duplicates without removing
                # any unique named equipment state.
                if previous_equal_id is not None and set_id <= previous_equal_id:
                    continue
                selected.append(row)
                used_ids.add(set_id)
                keep_going = visit(position + 1)
                used_ids.remove(set_id)
                selected.pop()
                if not keep_going and truncated:
                    return False
            return True

        visit(0)
        realizations.sort(
            key=lambda witness: (
                witness.set_ids,
                witness.weapon_shape.value,
                tuple((row.slot, row.set_id, row.weapon_type) for row in witness.assignments),
            )
        )
        return ExtremeNamedGearSetTopologyRealizationResult(
            topology=topology,
            realizations=tuple(realizations),
            assignments_considered=considered,
            assignments_rejected=rejected,
            truncated=truncated,
            unresolved=unresolved,
        )

    def build(
        self,
        topology_catalog: ExtremeGearSetTopologyCatalog,
        *,
        max_assignments_per_topology: int | None = None,
    ) -> ExtremeNamedGearSetCatalogRealizationResult:
        rows = tuple(
            self.realize_topology(
                topology,
                max_assignments=max_assignments_per_topology,
            )
            for topology in topology_catalog.topologies
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *topology_catalog.unresolved,
                    *self.breakpoints.unresolved,
                    *self.eligibility.unresolved,
                )
            )
        )
        return ExtremeNamedGearSetCatalogRealizationResult(
            topologies=rows,
            unresolved=unresolved,
        )
