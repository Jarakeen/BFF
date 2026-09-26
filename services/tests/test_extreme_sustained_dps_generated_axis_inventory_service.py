from __future__ import annotations

import pytest

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
)
from services.extreme_sustained_dps_generated_axis_inventory_service import (
    ExtremeSustainedDPSGeneratedAxisInventory,
    ExtremeSustainedDPSGeneratedAxisInventoryService,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)


def _axis(name, canonical_axes=(), omitted_scope=()):
    return ExtremeSustainedDPSIndexedFrontierAxis(
        name,
        candidate_count=lambda _state: 1,
        candidate_at=lambda state, _index: state,
        canonical_axes=tuple(canonical_axes),
        omitted_scope=tuple(omitted_scope),
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



def test_inventory_aggregates_axis_theoretical_omissions() -> None:
    result = ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
        (
            _axis(
                "Anchored",
                ("ultimate_policy", "potion_timing_policy"),
                ("continuous timing remains open",),
            ),
            _axis(
                "Heavy",
                ("heavy_attack_policy",),
                ("unreviewed HA windows remain open",),
            ),
        )
    )

    assert result.omitted_scope == (
        "continuous timing remains open",
        "unreviewed HA windows remain open",
    )



def test_heavy_attack_inventory_omission_depends_on_runtime_adapter_mode() -> None:
    from types import SimpleNamespace

    from services.extreme_sustained_dps_generated_axis_inventory_service import (
        ExtremeSustainedDPSGeneratedAxisInventoryService,
    )
    from services.extreme_sustained_dps_generated_runtime_policy_axis_adapter_service import (
        ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService,
    )

    execute = SimpleNamespace()
    heavy = SimpleNamespace()

    legacy = ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService(
        execute_policies=execute,
        heavy_attack_policies=heavy,
    )
    complete = ExtremeSustainedDPSGeneratedRuntimePolicyAxisAdapterService(
        execute_policies=execute,
        heavy_attack_policies=heavy,
        require_complete_heavy_attack_discovery=True,
    )

    legacy_inventory = ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
        legacy.axes()
    )
    complete_inventory = ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
        complete.axes()
    )

    assert any(
        "Heavy Attack windows outside the caller-supplied reviewed safe set"
        in item
        for item in legacy_inventory.omitted_scope
    )
    assert all(
        "Heavy Attack windows outside the caller-supplied reviewed safe set"
        not in item
        for item in complete_inventory.omitted_scope
    )
    assert "heavy_attack_policy" in complete_inventory.searched_canonical_axes

def test_inventory_rejects_noncanonical_tree_axis_tags() -> None:
    from types import SimpleNamespace

    malformed_axis = SimpleNamespace(
        name="Mystery",
        canonical_axes=("alchemy_moon_phase",),
        omitted_scope=(),
    )
    result = ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
        (malformed_axis,)
    )

    assert result.searched_canonical_axes == ()
    assert any(
        "declares non-canonical mutation axis" in row
        for row in result.unresolved
    )


def test_weapon_poison_formula_axis_does_not_imply_poison_tier_coverage() -> None:
    result = ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
        (_axis("Weapon Poisons", ("weapon_poisons",)),)
    )

    assert "weapon_poisons" in result.searched_canonical_axes
    assert "weapon_poison_tiers" in result.missing_canonical_axes



def test_inventory_rejects_non_tuple_axis_denominator() -> None:
    try:
        ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
            [_axis("Gear", ("gear_topology",))],  # type: ignore[arg-type]
        )
    except TypeError as exc:
        assert "axes must be a tuple" in str(exc)
    else:
        raise AssertionError("mutable axis denominator must fail closed")


def test_inventory_rejects_string_additional_axis_denominator() -> None:
    try:
        ExtremeSustainedDPSGeneratedAxisInventoryService.inventory(
            (),
            additional_canonical_axes="race",  # type: ignore[arg-type]
        )
    except TypeError as exc:
        assert "additional_canonical_axes must be a tuple" in str(exc)
    else:
        raise AssertionError("string additional-axis denominator must fail closed")



def test_axis_inventory_rejects_inconsistent_missing_axes() -> None:
    with pytest.raises(ValueError, match="missing_canonical_axes must match"):
        ExtremeSustainedDPSGeneratedAxisInventory(
            axis_names=(),
            searched_canonical_axes=("race",),
            missing_canonical_axes=(),
            untagged_axis_names=(),
            duplicate_canonical_axes=(),
            omitted_scope=(),
            evidence=(),
            unresolved=(),
        )


def test_axis_inventory_rejects_duplicate_axis_not_searched() -> None:
    missing = tuple(
        axis for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        if axis != "race"
    )
    with pytest.raises(ValueError, match="duplicate axes must also be searched"):
        ExtremeSustainedDPSGeneratedAxisInventory(
            axis_names=(),
            searched_canonical_axes=("race",),
            missing_canonical_axes=missing,
            untagged_axis_names=(),
            duplicate_canonical_axes=("class_route",),
            omitted_scope=(),
            evidence=(),
            unresolved=(),
        )
