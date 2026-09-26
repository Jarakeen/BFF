from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_generated_tree_coverage_service import (
    ExtremeSustainedDPSGeneratedTreeCoverageService,
)


def _inventory(**kwargs):
    values = {
        "searched_canonical_axes": ("race", "class_route", "attributes"),
        "omitted_scope": (),
        "unresolved": (),
        "duplicate_canonical_axes": (),
    }
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_completed_tree_promotes_only_physically_searched_axes() -> None:
    result = ExtremeSustainedDPSGeneratedTreeCoverageService.from_search(
        search_result=SimpleNamespace(global_maximum_proven=True),
        axis_inventory=_inventory(),
    )

    assert result.proof.dominated_axes == (
        "race",
        "class_route",
        "attributes",
    )
    assert result.proof.unresolved == ()


def test_tree_coverage_preserves_axis_theoretical_omissions() -> None:
    result = ExtremeSustainedDPSGeneratedTreeCoverageService.from_search(
        search_result=SimpleNamespace(global_maximum_proven=True),
        axis_inventory=_inventory(
            searched_canonical_axes=(
                "ultimate_policy",
                "potion_timing_policy",
            ),
            omitted_scope=(
                "continuous timing remains open",
            ),
        ),
    )

    assert result.proof.dominated_axes == (
        "ultimate_policy",
        "potion_timing_policy",
    )
    assert result.proof.omitted_scope == (
        "continuous timing remains open",
    )


def test_incomplete_tree_promotes_no_canonical_coverage() -> None:
    result = ExtremeSustainedDPSGeneratedTreeCoverageService.from_search(
        search_result=SimpleNamespace(global_maximum_proven=False),
        axis_inventory=_inventory(),
    )

    assert result.proof.dominated_axes == ()
    assert any("not proven" in row for row in result.proof.unresolved)


def test_inventory_duplicate_axis_fails_closed() -> None:
    result = ExtremeSustainedDPSGeneratedTreeCoverageService.from_search(
        search_result=SimpleNamespace(global_maximum_proven=True),
        axis_inventory=_inventory(
            duplicate_canonical_axes=("mundus",),
        ),
    )

    assert result.proof.dominated_axes == ()
    assert any("duplicate canonical-axis" in row for row in result.unresolved)



def test_globally_proven_flag_with_unresolved_search_evidence_promotes_no_coverage() -> None:
    result = ExtremeSustainedDPSGeneratedTreeCoverageService.from_search(
        search_result=SimpleNamespace(
            global_maximum_proven=True,
            unresolved=("one descendant remains mechanically unresolved",),
        ),
        axis_inventory=_inventory(),
    )

    assert result.proof.dominated_axes == ()
    assert any(
        "mechanically unresolved" in row
        for row in result.proof.unresolved
    )



def test_complete_heavy_attack_axis_reaches_tree_coverage_without_omission() -> None:
    result = ExtremeSustainedDPSGeneratedTreeCoverageService.from_search(
        search_result=SimpleNamespace(global_maximum_proven=True),
        axis_inventory=_inventory(
            searched_canonical_axes=("heavy_attack_policy",),
            omitted_scope=(),
        ),
    )

    assert result.proof.dominated_axes == ("heavy_attack_policy",)
    assert result.proof.omitted_scope == ()


def test_tree_coverage_rejects_truthy_non_boolean_global_maximum_proof() -> None:
    try:
        ExtremeSustainedDPSGeneratedTreeCoverageService.from_search(
            search_result=SimpleNamespace(global_maximum_proven="false"),
            axis_inventory=_inventory(),
        )
    except TypeError as exc:
        assert "boolean global_maximum_proven" in str(exc)
    else:
        raise AssertionError("truthy non-boolean search proof must fail closed")
