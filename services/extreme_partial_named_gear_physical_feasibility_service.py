from __future__ import annotations

"""Prove optimistic physical feasibility for a partial named-gear assignment.

A full named-set witness proves that one exact set tuple can occupy a legal active
snapshot. During branch-and-bound search we need a cheaper necessary condition:
can the sets selected *so far* still fit at least one canonical physical realization
if every future, unselected set is treated as unconstrained?

Because future sets are deliberately assumed perfect, a negative result is proof
that the partial branch can never become a legal full assignment. A positive result
is only permission to continue searching; it is not a full legality witness.
"""

from dataclasses import dataclass

from services.extreme_gear_physical_slot_realization_service import (
    ExtremeGearPhysicalRealization,
    ExtremeGearPhysicalSlotRealizationService,
    ExtremeWeaponSlotShape,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealizationService,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
)


_ONE_HANDED_MAIN_TYPES = ("Axe", "Mace", "Sword", "Dagger")
_ONE_HANDED_OFF_TYPES = (*_ONE_HANDED_MAIN_TYPES, "Shield")
_TWO_HANDED_TYPES = (
    "Two-Handed Sword",
    "Two-Handed Axe",
    "Two-Handed Mace",
    "Bow",
    "Restoration Staff",
    "Inferno Staff",
    "Ice Staff",
    "Lightning Staff",
)


@dataclass(frozen=True)
class ExtremePartialNamedGearPhysicalFeasibilityResult:
    possible: bool
    selected_count: int
    compatible_physical_shapes: int
    reason: str = ""


class ExtremePartialNamedGearPhysicalFeasibilityService:
    """Necessary-condition legality test for a selected prefix of named sets."""

    def __init__(self) -> None:
        self._physical_cache: dict[str, tuple[ExtremeGearPhysicalRealization, ...]] = {}
        self._compatible_physical_cache: dict[
            tuple[str, tuple[tuple[object, ...], ...]],
            tuple[ExtremeGearPhysicalRealization, ...],
        ] = {}
        self._result_cache: dict[
            tuple[str, tuple[tuple[object, ...], ...]],
            ExtremePartialNamedGearPhysicalFeasibilityResult,
        ] = {}
        self._shape_cache: dict[int, tuple[object, ...]] = {}
        self._body_cache: dict[
            tuple[tuple[int, ...], tuple[tuple[object, ...], ...]],
            bool,
        ] = {}
        # Topology objects are immutable during one exact search. Their derived
        # signature/count tuple used to be rebuilt millions of times in the hot
        # feasibility path, despite never changing for that object.
        self._topology_signature_cache: dict[int, str] = {}
        self._topology_counts_cache: dict[int, tuple[int, ...]] = {}

    @staticmethod
    def _shape(row: ExtremeNamedGearSetSlotEligibility) -> tuple[object, ...]:
        return (
            row.category.strip().casefold()
            == ExtremeNamedGearSetRealizationService.MYTHIC_CATEGORY,
            int(row.max_equip_count),
            tuple(row.armor_slots),
            tuple(row.jewelry_slots),
            tuple(row.weapon_types),
            tuple(int(value) for value in row.other_equip_types),
        )

    def _cached_shape(
        self,
        row: ExtremeNamedGearSetSlotEligibility,
    ) -> tuple[object, ...]:
        set_id = int(row.set_id)
        cached = self._shape_cache.get(set_id)
        if cached is None:
            cached = self._shape(row)
            self._shape_cache[set_id] = cached
        return cached

    def _topology_signature(self, topology: ExtremeGearSetCountTopology) -> str:
        key = id(topology)
        cached = self._topology_signature_cache.get(key)
        if cached is None:
            cached = topology.signature
            self._topology_signature_cache[key] = cached
        return cached

    def _topology_counts(self, topology: ExtremeGearSetCountTopology) -> tuple[int, ...]:
        key = id(topology)
        cached = self._topology_counts_cache.get(key)
        if cached is None:
            cached = tuple(int(value) for value in topology.counts)
            self._topology_counts_cache[key] = cached
        return cached

    def _physicals(
        self,
        topology: ExtremeGearSetCountTopology,
    ) -> tuple[ExtremeGearPhysicalRealization, ...]:
        signature = self._topology_signature(topology)
        rows = self._physical_cache.get(signature)
        if rows is None:
            rows = ExtremeGearPhysicalSlotRealizationService._witnesses_for_topology(topology)
            self._physical_cache[signature] = rows
        return rows

    @staticmethod
    def _weapon_compatible(
        physical: ExtremeGearPhysicalRealization,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> bool:
        selected_count = len(selected)
        indices = tuple(int(value) for value in physical.weapon_set_indices)

        if physical.weapon_shape is ExtremeWeaponSlotShape.NONE:
            return True

        if physical.weapon_shape is ExtremeWeaponSlotShape.ONE_HANDED_SINGLE:
            index = indices[0]
            if index >= selected_count:
                return True
            allowed = set(selected[index].weapon_types)
            return any(item in allowed for item in _ONE_HANDED_MAIN_TYPES)

        if physical.weapon_shape is ExtremeWeaponSlotShape.TWO_HANDED:
            index = indices[0]
            if index >= selected_count:
                return True
            allowed = set(selected[index].weapon_types)
            return any(item in allowed for item in _TWO_HANDED_TYPES)

        first, second = indices
        if first < selected_count:
            first_allowed = set(selected[first].weapon_types)
            if not any(item in first_allowed for item in _ONE_HANDED_MAIN_TYPES):
                return False
        if second < selected_count:
            second_allowed = set(selected[second].weapon_types)
            if not any(item in second_allowed for item in _ONE_HANDED_OFF_TYPES):
                return False
        return True

    def _body_compatible(
        self,
        physical: ExtremeGearPhysicalRealization,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> bool:
        if not selected:
            return True
        remaining = tuple(
            int(value)
            for value in physical.body_jewelry_counts[: len(selected)]
        )
        key = (
            remaining,
            tuple(self._cached_shape(row) for row in selected),
        )
        cached = self._body_cache.get(key)
        if cached is not None:
            return cached
        possible = (
            ExtremeNamedGearSetRealizationService._body_assignments(
                remaining,
                selected,
            )
            is not None
        )
        self._body_cache[key] = possible
        return possible

    def _compatible_physicals_prevalidated(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
        *,
        candidates: tuple[ExtremeGearPhysicalRealization, ...] | None = None,
    ) -> tuple[ExtremeGearPhysicalRealization, ...]:
        """Return exact compatible topology witnesses for a prevalidated prefix.

        Compatibility is monotone as a prefix grows: adding a named-set constraint
        cannot make a physical realization that already failed the parent prefix
        become legal again. Exact DFS callers may therefore pass the parent's
        compatible witnesses as ``candidates`` and filter only that shrinking set.

        Results are still cached by the full semantic prefix, so a repeated state
        receives the same complete compatible set regardless of which parent path
        reached it. Global named-set legality remains authoritative here.
        """

        counts = self._topology_counts(topology)
        key = (
            self._topology_signature(topology),
            tuple(self._cached_shape(row) for row in selected),
        )
        cached = self._compatible_physical_cache.get(key)
        if cached is not None:
            return cached

        if ExtremeNamedGearSetRealizationService._violates_global_set_legality(
            counts[: len(selected)],
            selected,
        ):
            self._compatible_physical_cache[key] = ()
            return ()

        source = self._physicals(topology) if candidates is None else candidates
        compatible = tuple(
            physical
            for physical in source
            if self._weapon_compatible(physical, selected)
            and self._body_compatible(physical, selected)
        )
        self._compatible_physical_cache[key] = compatible
        return compatible

    def _evaluate_prevalidated(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> ExtremePartialNamedGearPhysicalFeasibilityResult:
        """Evaluate a prefix whose exact-search caller already proved local guards.

        This is intentionally private to exact branch-and-bound callers. They already
        enforce distinct set identities and construct candidates only from rows with
        sufficient breakpoint count and physical-slot evidence. Skipping those three
        repeated guards changes no legality rule; global named-set legality and the
        canonical physical witness-space test below remain authoritative.
        """

        key = (
            self._topology_signature(topology),
            tuple(self._cached_shape(row) for row in selected),
        )
        cached = self._result_cache.get(key)
        if cached is not None:
            return cached

        counts = self._topology_counts(topology)
        if ExtremeNamedGearSetRealizationService._violates_global_set_legality(
            counts[: len(selected)],
            selected,
        ):
            result = ExtremePartialNamedGearPhysicalFeasibilityResult(
                possible=False,
                selected_count=len(selected),
                compatible_physical_shapes=0,
                reason="selected prefix violates global named-set legality",
            )
            self._compatible_physical_cache[key] = ()
            self._result_cache[key] = result
            return result

        compatible = self._compatible_physicals_prevalidated(topology, selected)
        result = ExtremePartialNamedGearPhysicalFeasibilityResult(
            possible=bool(compatible),
            selected_count=len(selected),
            compatible_physical_shapes=len(compatible),
            reason=(
                ""
                if compatible
                else "selected prefix cannot fit any canonical physical realization"
            ),
        )
        self._result_cache[key] = result
        return result

    def evaluate(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> ExtremePartialNamedGearPhysicalFeasibilityResult:
        counts = self._topology_counts(topology)
        if len(selected) > len(counts):
            return ExtremePartialNamedGearPhysicalFeasibilityResult(
                possible=False,
                selected_count=len(selected),
                compatible_physical_shapes=0,
                reason="selected prefix is longer than topology",
            )
        if len({int(row.set_id) for row in selected}) != len(selected):
            return ExtremePartialNamedGearPhysicalFeasibilityResult(
                possible=False,
                selected_count=len(selected),
                compatible_physical_shapes=0,
                reason="selected prefix repeats a named set identity",
            )
        if any(
            int(counts[index]) > int(row.max_equip_count)
            for index, row in enumerate(selected)
        ):
            return ExtremePartialNamedGearPhysicalFeasibilityResult(
                possible=False,
                selected_count=len(selected),
                compatible_physical_shapes=0,
                reason="selected set cannot supply its topology piece count",
            )
        if any(
            int(counts[index]) > 0 and not row.has_physical_slot_evidence
            for index, row in enumerate(selected)
        ):
            return ExtremePartialNamedGearPhysicalFeasibilityResult(
                possible=False,
                selected_count=len(selected),
                compatible_physical_shapes=0,
                reason="selected set lacks physical slot eligibility evidence",
            )

        return self._evaluate_prevalidated(topology, selected)

    def is_possible(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> bool:
        return self.evaluate(topology, selected).possible

    def _is_possible_prevalidated(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> bool:
        return self._evaluate_prevalidated(topology, selected).possible


__all__ = [
    "ExtremePartialNamedGearPhysicalFeasibilityResult",
    "ExtremePartialNamedGearPhysicalFeasibilityService",
]
