from __future__ import annotations

"""Enumerate objective-neutral active-snapshot gear-set count topologies.

This layer deliberately stops before physical slot realization.  ESO exposes 12
*effective set-count units* in an active-bar snapshot: seven armor pieces, three
jewelry pieces, and two weapon set-count units.  A two-handed weapon occupies one
physical weapon item while contributing two set-count units; paired one-hand
weapons occupy two physical items and also contribute two units.

The canonical ``gear_set`` table proves set identity/category/max_equip_count but
not, by itself, every special set's physical-slot legality.  This service therefore
answers the narrower denominator question first: which piece-count partitions are
representable by distinct canonical set capacities?  A later realization layer must
prove exact armor/jewelry/weapon placement before the gear axis can be globally
closed.
"""

from dataclasses import dataclass
from typing import Iterable

from minmax.gear_set_repository import GearSetRepository


ACTIVE_SNAPSHOT_SET_UNITS = 12


@dataclass(frozen=True)
class ExtremeGearSetDescriptor:
    set_id: int
    name: str
    category: str
    max_equip_count: int


@dataclass(frozen=True)
class ExtremeGearSetCountTopology:
    """One abstract allocation of active-snapshot set-count units.

    ``counts`` contains one equipped-count value per distinct set identity, sorted
    descending. ``unused_units`` are legal non-set / otherwise unassigned units.
    This is intentionally not a physical slot assignment.
    """

    counts: tuple[int, ...]
    unused_units: int
    total_units: int = ACTIVE_SNAPSHOT_SET_UNITS

    @property
    def used_units(self) -> int:
        return sum(self.counts)

    @property
    def signature(self) -> str:
        parts = "+".join(str(value) for value in self.counts) or "none"
        return f"{parts}|unused:{self.unused_units}"


@dataclass(frozen=True)
class ExtremeGearSetTopologyCatalog:
    sets: tuple[ExtremeGearSetDescriptor, ...]
    topologies: tuple[ExtremeGearSetCountTopology, ...]
    unresolved: tuple[str, ...] = ()
    active_snapshot_units: int = ACTIVE_SNAPSHOT_SET_UNITS
    physical_slot_realization_proven: bool = False

    @property
    def count_topology_denominator_proven(self) -> bool:
        """Whether the abstract count-partition denominator is complete.

        This does *not* prove physical gear legality.  The separate boolean keeps
        callers from promoting a count partition into a legal equipped build.
        """

        return bool(self.sets and self.topologies and not self.unresolved)

    @property
    def gear_denominator_proven(self) -> bool:
        return self.count_topology_denominator_proven and self.physical_slot_realization_proven


class ExtremeGearSetTopologyCatalogService:
    """Build the finite active-snapshot set-count topology catalog."""

    def __init__(
        self,
        repository: GearSetRepository,
        *,
        active_snapshot_units: int = ACTIVE_SNAPSHOT_SET_UNITS,
    ) -> None:
        self.repository = repository
        self.active_snapshot_units = int(active_snapshot_units)
        if self.active_snapshot_units <= 0:
            raise ValueError("active_snapshot_units must be positive")

    def _descriptors(self) -> tuple[tuple[ExtremeGearSetDescriptor, ...], tuple[str, ...]]:
        descriptors: list[ExtremeGearSetDescriptor] = []
        unresolved: list[str] = []
        seen_ids: set[int] = set()

        for gear_set in self.repository.list_sets():
            set_id = int(gear_set.id)
            if set_id in seen_ids:
                continue
            seen_ids.add(set_id)

            name = str(gear_set.name or "").strip()
            if not name:
                unresolved.append(f"Gear set {set_id} has no canonical name")
                continue
            try:
                capacity = int(gear_set.max_equip_count or 0)
            except (TypeError, ValueError):
                capacity = 0
            if capacity <= 0:
                unresolved.append(
                    f"Gear set {name} has no positive canonical max_equip_count"
                )
                continue

            descriptors.append(
                ExtremeGearSetDescriptor(
                    set_id=set_id,
                    name=name,
                    category=str(gear_set.category or "").strip(),
                    max_equip_count=capacity,
                )
            )

        descriptors.sort(key=lambda item: (item.name.casefold(), item.name, item.set_id))
        return tuple(descriptors), tuple(dict.fromkeys(unresolved))

    @staticmethod
    def _integer_partitions(total: int, *, maximum_part: int) -> Iterable[tuple[int, ...]]:
        """Yield deterministic non-increasing integer partitions of ``total``."""

        def visit(remaining: int, ceiling: int, prefix: tuple[int, ...]):
            if remaining == 0:
                yield prefix
                return
            for value in range(min(ceiling, remaining), 0, -1):
                yield from visit(remaining - value, value, (*prefix, value))

        if total == 0:
            yield ()
            return
        yield from visit(total, min(maximum_part, total), ())

    @staticmethod
    def _capacity_realizable(
        counts: tuple[int, ...],
        descriptors: tuple[ExtremeGearSetDescriptor, ...],
    ) -> bool:
        """Whether distinct set identities can satisfy this abstract count vector."""

        if not counts:
            return True
        capacities = sorted(
            (descriptor.max_equip_count for descriptor in descriptors),
            reverse=True,
        )
        requested = sorted(counts, reverse=True)
        if len(requested) > len(capacities):
            return False

        # Greedy matching is sufficient for one-dimensional lower-bound capacity
        # constraints when both sides are sorted descending.
        available = list(capacities)
        for count in requested:
            match_index = next(
                (index for index, capacity in enumerate(available) if capacity >= count),
                None,
            )
            if match_index is None:
                return False
            available.pop(match_index)
        return True

    def build(self) -> ExtremeGearSetTopologyCatalog:
        descriptors, unresolved = self._descriptors()
        maximum_capacity = max(
            (descriptor.max_equip_count for descriptor in descriptors),
            default=0,
        )

        topologies: list[ExtremeGearSetCountTopology] = []
        if maximum_capacity > 0:
            for used_units in range(0, self.active_snapshot_units + 1):
                for counts in self._integer_partitions(
                    used_units,
                    maximum_part=maximum_capacity,
                ):
                    if not self._capacity_realizable(counts, descriptors):
                        continue
                    topologies.append(
                        ExtremeGearSetCountTopology(
                            counts=counts,
                            unused_units=self.active_snapshot_units - used_units,
                            total_units=self.active_snapshot_units,
                        )
                    )

        topologies.sort(
            key=lambda item: (
                item.unused_units,
                tuple(-value for value in item.counts),
                item.counts,
            )
        )
        return ExtremeGearSetTopologyCatalog(
            sets=descriptors,
            topologies=tuple(topologies),
            unresolved=unresolved,
            active_snapshot_units=self.active_snapshot_units,
            physical_slot_realization_proven=False,
        )
