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
        self._result_cache: dict[
            tuple[str, tuple[tuple[object, ...], ...]],
            ExtremePartialNamedGearPhysicalFeasibilityResult,
        ] = {}
        self._shape_cache: dict[int, tuple[object, ...]] = {}

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

    def _physicals(
        self,
        topology: ExtremeGearSetCountTopology,
    ) -> tuple[ExtremeGearPhysicalRealization, ...]:
        rows = self._physical_cache.get(topology.signature)
        if rows is None:
            rows = ExtremeGearPhysicalSlotRealizationService._witnesses_for_topology(topology)
            self._physical_cache[topology.signature] = rows
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

    @staticmethod
    def _body_compatible(
        physical: ExtremeGearPhysicalRealization,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> bool:
        if not selected:
            return True
        remaining = tuple(
            int(value)
            for value in physical.body_jewelry_counts[: len(selected)]
        )
        return (
            ExtremeNamedGearSetRealizationService._body_assignments(
                remaining,
                selected,
            )
            is not None
        )

    def evaluate(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> ExtremePartialNamedGearPhysicalFeasibilityResult:
        counts = tuple(int(value) for value in topology.counts)
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

        key = (
            topology.signature,
            tuple(self._cached_shape(row) for row in selected),
        )
        cached = self._result_cache.get(key)
        if cached is not None:
            return cached

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
            self._result_cache[key] = result
            return result

        compatible = 0
        for physical in self._physicals(topology):
            if not self._weapon_compatible(physical, selected):
                continue
            if not self._body_compatible(physical, selected):
                continue
            compatible += 1

        result = ExtremePartialNamedGearPhysicalFeasibilityResult(
            possible=compatible > 0,
            selected_count=len(selected),
            compatible_physical_shapes=compatible,
            reason=(
                ""
                if compatible > 0
                else "selected prefix cannot fit any canonical physical realization"
            ),
        )
        self._result_cache[key] = result
        return result

    def is_possible(
        self,
        topology: ExtremeGearSetCountTopology,
        selected: tuple[ExtremeNamedGearSetSlotEligibility, ...],
    ) -> bool:
        return self.evaluate(topology, selected).possible


__all__ = [
    "ExtremePartialNamedGearPhysicalFeasibilityResult",
    "ExtremePartialNamedGearPhysicalFeasibilityService",
]
