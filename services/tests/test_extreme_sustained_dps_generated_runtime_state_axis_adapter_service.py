from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_generated_runtime_state_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService,
    ExtremeSustainedDPSGeneratedRuntimeStateLeaf,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontierService,
)


def _frontier(*, proven=True, omitted_scope=()):
    return ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (
            ExtremeSustainedDPSRuntimeStateChoice("runtime:a", "snapshot-a"),
            ExtremeSustainedDPSRuntimeStateChoice("runtime:b", "snapshot-b"),
        ),
        denominator_proven=proven,
        source="reviewed local runtime family",
        omitted_scope=tuple(omitted_scope),
    )


def test_runtime_family_becomes_lazy_terminal_axis_and_preserves_scope() -> None:
    frontier = _frontier(
        omitted_scope=("encounter-triggered runtime histories remain outside this branch",)
    )
    axis = ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(frontier)
    upstream = SimpleNamespace(complete=True, marker="pipeline")

    assert axis.candidate_count(upstream) == 2
    leaf = axis.candidate_at(upstream, 1)

    assert isinstance(leaf, ExtremeSustainedDPSGeneratedRuntimeStateLeaf)
    assert leaf.complete is True
    assert leaf.runtime_state_choice.runtime_state_id == "runtime:b"
    assert leaf.runtime_state_choice.snapshot == "snapshot-b"
    assert leaf.marker == "pipeline"
    assert leaf.omitted_scope == (
        "encounter-triggered runtime histories remain outside this branch",
    )

    proof = ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.coverage(frontier)
    assert proof.dominated_axes == ("runtime_state",)
    assert proof.omitted_scope == leaf.omitted_scope


def test_unproven_runtime_family_cannot_be_appended_to_generated_search() -> None:
    frontier = _frontier(proven=False)

    with pytest.raises(ValueError, match="proven local denominator"):
        ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(frontier)


def test_runtime_axis_requires_complete_upstream_pipeline_state() -> None:
    axis = ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(
        _frontier()
    )

    with pytest.raises(ValueError, match="complete upstream"):
        axis.candidate_count(SimpleNamespace(complete=False))
