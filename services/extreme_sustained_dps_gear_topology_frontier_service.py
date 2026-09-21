from __future__ import annotations

"""Objective-neutral gear-set count topology frontier for sustained-DPS search.

This layer reuses the canonical Extreme set-count topology authority. It closes only
the abstract active-snapshot count partition denominator. Named-set identity,
physical armor/jewelry/weapon placement, and front/back compatibility remain separate
proof obligations.
"""

from dataclasses import dataclass

from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
    ExtremeGearSetTopologyCatalogService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGearTopologyFrontier:
    topology_count: int
    canonical_set_count: int
    count_topology_denominator_proven: bool
    physical_realization_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSGearTopologyFrontierService:
    """Expose the canonical active-snapshot gear count partitions to DPS search."""

    def __init__(
        self,
        repository: GearSetRepository | object,
        *,
        active_snapshot_units: int = 12,
    ) -> None:
        self.catalog_service = ExtremeGearSetTopologyCatalogService(
            repository,
            active_snapshot_units=active_snapshot_units,
        )
        self._catalog: ExtremeGearSetTopologyCatalog | None = None

    @classmethod
    def from_database(cls, database_path) -> "ExtremeSustainedDPSGearTopologyFrontierService":
        return cls(GearSetRepository(database_path))

    def catalog(self) -> ExtremeGearSetTopologyCatalog:
        if self._catalog is None:
            self._catalog = self.catalog_service.build()
        return self._catalog

    def frontier(self) -> ExtremeSustainedDPSGearTopologyFrontier:
        catalog = self.catalog()
        count = len(catalog.topologies)
        proven = bool(catalog.count_topology_denominator_proven)
        unresolved = tuple(catalog.unresolved)
        if count <= 0 and not unresolved:
            unresolved = ("Canonical gear-set count topology frontier is empty",)

        return ExtremeSustainedDPSGearTopologyFrontier(
            topology_count=count,
            canonical_set_count=len(catalog.sets),
            count_topology_denominator_proven=proven and not unresolved,
            physical_realization_proven=bool(catalog.physical_slot_realization_proven),
            evidence=(
                f"Canonical named gear sets reviewed: {len(catalog.sets)}",
                f"Active-snapshot set-count units: {int(catalog.active_snapshot_units)}",
                f"Legal abstract count topologies: {count}",
                "Topology closure proves count partitions only; named-set identities and physical slot witnesses remain separate",
                "Two-handed weapons contribute two set-count units even though they occupy one physical weapon item",
            ),
            unresolved=unresolved,
        )

    def topology_at(self, index: int) -> ExtremeGearSetCountTopology:
        catalog = self.catalog()
        target = int(index)
        if target < 0 or target >= len(catalog.topologies):
            raise IndexError("gear-set topology index out of range")
        return catalog.topologies[target]

    def page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ExtremeGearSetCountTopology, ...]:
        catalog = self.catalog()
        start = max(0, int(offset))
        size = max(0, int(limit))
        if size == 0 or start >= len(catalog.topologies):
            return ()
        return tuple(catalog.topologies[start : start + size])


__all__ = [
    "ExtremeSustainedDPSGearTopologyFrontier",
    "ExtremeSustainedDPSGearTopologyFrontierService",
]
