from __future__ import annotations

from dataclasses import dataclass

from services.extreme_gear_set_topology_catalog_service import (
    ACTIVE_SNAPSHOT_SET_UNITS,
    ExtremeGearSetTopologyCatalogService,
)


@dataclass(frozen=True)
class _Set:
    id: int
    name: str
    category: str | None
    max_equip_count: int | None


class _Repository:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def list_sets(self):
        return self.rows


def _standard_repository():
    return _Repository(
        (
            _Set(1, "Five A", "Dungeon", 5),
            _Set(2, "Five B", "Trial", 5),
            _Set(3, "Monster", "Monster", 2),
            _Set(4, "Mythic", "Mythic", 1),
        )
    )


def test_catalog_uses_twelve_active_snapshot_set_count_units():
    catalog = ExtremeGearSetTopologyCatalogService(_standard_repository()).build()

    assert catalog.active_snapshot_units == ACTIVE_SNAPSHOT_SET_UNITS == 12
    assert all(topology.used_units + topology.unused_units == 12 for topology in catalog.topologies)


def test_catalog_contains_standard_five_five_two_and_mythic_variant_topologies():
    catalog = ExtremeGearSetTopologyCatalogService(_standard_repository()).build()
    signatures = {topology.signature for topology in catalog.topologies}

    assert "5+5+2|unused:0" in signatures
    assert "5+5+1+1|unused:0" in signatures


def test_catalog_includes_legal_no_set_baseline_and_partial_set_allocations():
    catalog = ExtremeGearSetTopologyCatalogService(_standard_repository()).build()
    signatures = {topology.signature for topology in catalog.topologies}

    assert "none|unused:12" in signatures
    assert "5|unused:7" in signatures
    assert "2+1|unused:9" in signatures


def test_capacity_matching_requires_distinct_set_identities():
    repository = _Repository(
        (
            _Set(1, "Only Five Piece", "Dungeon", 5),
            _Set(2, "Only Two Piece", "Monster", 2),
        )
    )
    catalog = ExtremeGearSetTopologyCatalogService(repository).build()
    signatures = {topology.signature for topology in catalog.topologies}

    assert "5+2|unused:5" in signatures
    assert "5+5|unused:2" not in signatures
    assert "2+2|unused:8" not in signatures


def test_missing_capacity_is_fail_closed_and_prevents_count_denominator_proof():
    repository = _Repository(
        (
            _Set(1, "Good Set", "Dungeon", 5),
            _Set(2, "Mystery Set", "Unknown", None),
        )
    )
    catalog = ExtremeGearSetTopologyCatalogService(repository).build()

    assert catalog.count_topology_denominator_proven is False
    assert catalog.gear_denominator_proven is False
    assert catalog.unresolved == (
        "Gear set Mystery Set has no positive canonical max_equip_count",
    )


def test_count_topology_can_be_complete_without_claiming_physical_gear_legality():
    catalog = ExtremeGearSetTopologyCatalogService(_standard_repository()).build()

    assert catalog.count_topology_denominator_proven is True
    assert catalog.physical_slot_realization_proven is False
    assert catalog.gear_denominator_proven is False
