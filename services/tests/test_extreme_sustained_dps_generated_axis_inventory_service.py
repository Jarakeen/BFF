from __future__ import annotations

from services.extreme_sustained_dps_generated_axis_inventory_service import (
    ExtremeSustainedDPSGeneratedAxisInventoryService,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)


def _axis(name, canonical_axes=()):
    return ExtremeSustainedDPSIndexedFrontierAxis(
        name,
        candidate_count=lambda _state: 1,
        candidate_at=lambda state, _index: state,
        canonical_axes=tuple(canonical_axes),
    )


def test_inventory_reports_physically_searched_axes_without_claiming_proof() -> None:
    result = ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
        (
            _axis("Gear", ("gear_topology", "named_gear_realization")),
            _axis("Mundus", ("mundus",)),
            _axis("Food", ("food",)),
        ),
        additional_canonical_axes=("race", "class_route", "attributes"),
    )

    assert {
        "race",
        "class_route",
        "attributes",
        "gear_topology",
        "named_gear_realization",
        "mundus",
        "food",
    }.issubset(set(result.searched_canonical_axes))
    assert "encounter_policy" in result.missing_canonical_axes
    assert result.unresolved == ()
    assert any("structural evidence only" in row for row in result.evidence)


def test_inventory_surfaces_untagged_generated_axis() -> None:
    result = ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
        (_axis("Mystery"),)
    )

    assert result.untagged_axis_names == ("Mystery",)


def test_inventory_flags_duplicate_canonical_axis_enumeration() -> None:
    result = ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
        (
            _axis("One", ("mundus",)),
            _axis("Two", ("mundus",)),
        )
    )

    assert result.duplicate_canonical_axes == ("mundus",)
    assert any("more than once" in row for row in result.unresolved)
