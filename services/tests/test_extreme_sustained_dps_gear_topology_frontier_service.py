from __future__ import annotations

from dataclasses import dataclass

import pytest

from services.extreme_sustained_dps_gear_topology_frontier_service import (
    ExtremeSustainedDPSGearTopologyFrontierService,
)


@dataclass(frozen=True)
class _Set:
    id: int
    name: str
    category: str
    max_equip_count: int


class _Repository:
    def list_sets(self):
        return (
            _Set(1, "Five A", "standard", 5),
            _Set(2, "Five B", "standard", 5),
            _Set(3, "Monster", "monster", 2),
            _Set(4, "Mythic", "mythic", 1),
        )


def _service():
    return ExtremeSustainedDPSGearTopologyFrontierService(
        _Repository(),
        active_snapshot_units=4,
    )


def test_gear_topology_frontier_closes_abstract_count_denominator_only() -> None:
    result = _service().frontier()

    assert result.count_topology_denominator_proven is True
    assert result.physical_realization_proven is False
    assert result.topology_count > 0
    assert result.canonical_set_count == 4
    assert any("count partitions only" in row for row in result.evidence)


def test_topology_page_is_deterministic() -> None:
    service = _service()
    rows = service.page(offset=1, limit=3)

    assert rows == service.catalog().topologies[1:4]


def test_topology_at_matches_catalog_order() -> None:
    service = _service()

    assert service.topology_at(0) == service.catalog().topologies[0]


def test_invalid_topology_index_fails_closed() -> None:
    service = _service()
    count = service.frontier().topology_count

    with pytest.raises(IndexError):
        service.topology_at(-1)
    with pytest.raises(IndexError):
        service.topology_at(count)


def test_topology_frontier_keeps_unused_units_states() -> None:
    service = _service()
    rows = service.catalog().topologies

    assert any(row.unused_units > 0 for row in rows)
    assert any(row.unused_units == 0 for row in rows)
