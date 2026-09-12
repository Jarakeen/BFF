from __future__ import annotations

"""Enumerate concrete named-set assignments for Extreme gear topologies.

This layer composes canonical set-bonus breakpoints, named physical-slot
eligibility, and exact slot-witness realization. Equal-count topology parts are
symmetry-reduced by set id, so ``5(A)+5(B)`` and ``5(B)+5(A)`` are one named
assignment rather than two copies of the same equipment state.

Physical realizability depends on topology plus slot-eligibility shape, not set
identity. Exhaustive production searches therefore memoize exact witness templates
by that semantic legality shape and rematerialize the current set ids/names. The
immutable concrete slot assignments used during rematerialization are interned by
set identity + slot + weapon type, avoiding repeated dataclass construction across
large named-set combinations without pruning any named assignment.

A caller may cap assignments for exploratory/runtime use. Any such truncation is
explicit and prevents denominator proof. Exhaustive means exhaustive; a progress
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
    ExtremeNamedGearSlotAssignment,
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


@dataclass(frozen=True)
class _EligibilityShape:
    """Identity-free physical legality inputs consumed by the witness solver."""

    mythic: bool
    max_equip_count: int
    armor_slots: tuple[str, ...]
    jewelry_slots: tuple[str, ...]
    weapon_types: tuple[str, ...]
    other_equip_types: tuple[int, ...]


@dataclass(frozen=True)
class _WitnessTemplateAssignment:
    set_position: int
    slot: str
    weapon_type: str


@dataclass(frozen=True)
class _WitnessTemplate:
    weapon_shape: object
    assignments: tuple[_WitnessTemplateAssignment, ...]


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
        self._witness_template_cache: dict[
            tuple[str, tuple[_EligibilityShape, ...]],
            _WitnessTemplate | None,
        ] = {}
        self._slot_assignment_cache: dict[
            tuple[int, str, str, str],
            ExtremeNamedGearSlotAssignment,
        ] = {}

    @staticmethod
    def _eligibility_shape(row: ExtremeNamedGearSetSlotEligibility) -> _EligibilityShape:
        return _EligibilityShape(
            mythic=row.category.strip().casefold()
            == ExtremeNamedGearSetRealizationService.MYTHIC_CATEGORY,
            max_equip_count=int(row.max_equip_count),
            armor_slots=tuple(row.armor_slots),
            jewelry_slots=tuple(row.jewelry_slots),
            weapon_types=tuple(row.weapon_types),
            other_equip_types=tuple(row.other_equip_types),
        )

    @classmethod
    def _template_from_witness(
        cls,
        witness: ExtremeNamedGearSetRealization,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> _WitnessTemplate:
        position_by_set_id = {
            int(row.set_id): position for position, row in enumerate(selected)
        }
        return _WitnessTemplate(
            weapon_shape=witness.weapon_shape,
            assignments=tuple(
                _WitnessTemplateAssignment(
                    set_position=position_by_set_id[int(assignment.set_id)],
                    slot=assignment.slot,
                    weapon_type=assignment.weapon_type,
                )
                for assignment in witness.assignments
            ),
        )

    def _materialized_slot_assignment(
        self,
        row: ExtremeNamedGearSetSlotEligibility,
        template_assignment: _WitnessTemplateAssignment,
    ) -> ExtremeNamedGearSlotAssignment:
        key = (
            int(row.set_id),
            row.name,
            template_assignment.slot,
            template_assignment.weapon_type,
        )
        assignment = self._slot_assignment_cache.get(key)
        if assignment is None:
            assignment = ExtremeNamedGearSlotAssignment(
                slot=template_assignment.slot,
                set_id=int(row.set_id),
                set_name=row.name,
                weapon_type=template_assignment.weapon_type,
            )
            self._slot_assignment_cache[key] = assignment
        return assignment

    def _materialize_template(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
        template: _WitnessTemplate,
    ) -> ExtremeNamedGearSetRealization:
        assignments = tuple(
            self._materialized_slot_assignment(
                selected[item.set_position],
                item,
            )
            for item in template.assignments
        )
        return ExtremeNamedGearSetRealization(
            topology_signature=topology.signature,
            set_ids=tuple(int(row.set_id) for row in selected),
            set_names=tuple(row.name for row in selected),
            counts=tuple(topology.counts),
            weapon_shape=template.weapon_shape,
            assignments=assignments,
        )

    def _find_witness_cached(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> ExtremeNamedGearSetRealization | None:
        key = (
            topology.signature,
            tuple(self._eligibility_shape(row) for row in selected),
        )
        if key not in self._witness_template_cache:
            witness = ExtremeNamedGearSetRealizationService.find_witness(
                topology,
                selected,
            )
            self._witness_template_cache[key] = (
                None if witness is None else self._template_from_witness(witness, selected)
            )
        template = self._witness_template_cache[key]
        if template is None:
            return None
        return self._materialize_template(topology, selected, template)

    def _candidates_for_count(
        self,
        count: int,
    ) -> tuple[ExtremeNamedGearSetSlotEligibility, ...]:
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
            witness = self._find_witness_cached(topology, ())
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
                witness = self._find_witness_cached(
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
                # Equal-count topology parts are indistinguishable. Canonical
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
