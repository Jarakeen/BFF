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



def test_candidate_runtime_axis_resolves_frontier_per_upstream_candidate() -> None:
    calls = []

    class _Resolver:
        def resolve(self, state):
            calls.append(state.marker)
            suffix = state.marker[-1]
            return ExtremeSustainedDPSRuntimeStateFrontierService.build(
                (
                    ExtremeSustainedDPSRuntimeStateChoice(
                        f"runtime:{suffix}",
                        f"snapshot:{suffix}",
                    ),
                ),
                denominator_proven=True,
                source=f"candidate {state.marker}",
            )

    axis = ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.candidate_axis(
        _Resolver()
    )
    state_a = SimpleNamespace(complete=True, marker="candidate-a")
    state_b = SimpleNamespace(complete=True, marker="candidate-b")

    assert axis.candidate_count(state_a) == 1
    assert axis.candidate_count(state_b) == 1

    leaf_a = axis.candidate_at(state_a, 0)
    leaf_b = axis.candidate_at(state_b, 0)

    assert leaf_a.runtime_state_choice.snapshot == "snapshot:a"
    assert leaf_b.runtime_state_choice.snapshot == "snapshot:b"
    assert calls == [
        "candidate-a",
        "candidate-b",
        "candidate-a",
        "candidate-b",
    ]


def test_candidate_runtime_axis_rejects_omitted_runtime_scope() -> None:
    class _Resolver:
        def resolve(self, _state):
            return _frontier(
                omitted_scope=("scenario trigger family omitted",)
            )

    axis = ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.candidate_axis(
        _Resolver()
    )

    with pytest.raises(ValueError, match="theoretical omitted scope"):
        axis.candidate_count(SimpleNamespace(complete=True))


def test_truthy_non_boolean_upstream_complete_flag_fails_closed() -> None:
    axis = ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(_frontier())

    with pytest.raises(TypeError, match="complete flag must be boolean"):
        axis.candidate_count(SimpleNamespace(complete="false"))


def test_duck_typed_runtime_frontier_cannot_enter_proven_axis() -> None:
    frontier = SimpleNamespace(
        choices=(ExtremeSustainedDPSRuntimeStateChoice("runtime:a", "snapshot-a"),),
        candidate_count=1,
        denominator_proven=True,
        unresolved=(),
        omitted_scope=(),
    )

    with pytest.raises(TypeError, match="canonical runtime-state frontier"):
        ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(frontier)


def test_runtime_axis_rejects_boolean_choice_index() -> None:
    axis = ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(_frontier())
    state = SimpleNamespace(complete=True)

    with pytest.raises(TypeError, match="choice index must be an integer"):
        axis.candidate_at(state, True)


def test_candidate_runtime_axis_rejects_boolean_choice_index() -> None:
    class _Resolver:
        def resolve(self, _state):
            return _frontier()

    axis = ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.candidate_axis(
        _Resolver()
    )
    state = SimpleNamespace(complete=True)

    with pytest.raises(TypeError, match="choice index must be an integer"):
        axis.candidate_at(state, False)
