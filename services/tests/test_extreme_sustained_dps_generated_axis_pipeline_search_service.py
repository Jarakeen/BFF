from __future__ import annotations

import pytest

from dataclasses import dataclass, replace

from services.extreme_sustained_dps_generated_axis_pipeline_search_service import (
    ExtremeSustainedDPSGeneratedAxisPipelineSearchService,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontierService,
)


@dataclass(frozen=True)
class _State:
    selected: int | None = None

    @property
    def complete(self) -> bool:
        return self.selected is not None


class _Pipeline:
    @staticmethod
    def axes():
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Choice",
                candidate_count=lambda _state: 2,
                candidate_at=lambda state, index: replace(state, selected=index),
            ),
        )


class _LeafEvaluation:
    def __init__(self):
        self.config = None

    def evaluator(self, **kwargs):
        self.config = kwargs

        def evaluate(node):
            return ExtremeSustainedDPSExactLeafEvaluation(
                candidate_key=node.candidate_key,
                modeled_dps=float(node.state.selected),
                duration_seconds=10.0,
                mechanic_complete=True,
            )

        return evaluate


def test_runs_composed_pipeline_with_one_shared_runtime_scenario() -> None:
    leaf = _LeafEvaluation()
    service = ExtremeSustainedDPSGeneratedAxisPipelineSearchService(
        pipeline=_Pipeline(),
        leaf_evaluation=leaf,
    )

    result = service.search(
        _State(),
        required_duration_seconds=10.0,
        runtime_snapshot="snapshot",
        target_health=1_000_000,
        target_resistance=18_200.0,
        target_name="Boss",
        initial_bar="back",
        root_key="structural:0",
    )

    assert result.evaluated_leaf_count == 2
    assert result.best_modeled_dps == 1.0
    assert result.global_maximum_proven is True
    assert leaf.config == {
        "runtime_snapshot": "snapshot",
        "target_health": 1_000_000,
        "target_resistance": 18_200.0,
        "target_name": "Boss",
        "initial_bar": "back",
    }


def test_forwards_root_bound_provider_to_lazy_wiring() -> None:
    leaf = _LeafEvaluation()
    service = ExtremeSustainedDPSGeneratedAxisPipelineSearchService(
        pipeline=_Pipeline(),
        leaf_evaluation=leaf,
    )
    seen = []

    def root_bounds(state):
        seen.append(state)
        return ()

    result = service.search(
        _State(),
        required_duration_seconds=10.0,
        runtime_snapshot="snapshot",
        target_health=100,
        target_resistance=0.0,
        root_bound_inputs=root_bounds,
    )

    assert result.global_maximum_proven is True
    assert seen == [_State()]



def test_forwards_node_bound_provider_to_lazy_wiring() -> None:
    leaf = _LeafEvaluation()
    service = ExtremeSustainedDPSGeneratedAxisPipelineSearchService(
        pipeline=_Pipeline(),
        leaf_evaluation=leaf,
    )
    seen = []

    def branch_bounds(node):
        seen.append((node.candidate_key, node.depth))
        return ()

    result = service.search(
        _State(),
        required_duration_seconds=10.0,
        runtime_snapshot="snapshot",
        target_health=100,
        target_resistance=0.0,
        root_key="structural:0",
        branch_bound_inputs=branch_bounds,
    )

    assert result.global_maximum_proven is True
    assert seen == [
        ("structural:0", 0),
        ("structural:0|choice:0", 1),
        ("structural:0|choice:1", 1),
    ]



def test_appends_proven_local_runtime_family_as_terminal_search_axis() -> None:
    leaf = _LeafEvaluation()
    service = ExtremeSustainedDPSGeneratedAxisPipelineSearchService(
        pipeline=_Pipeline(),
        leaf_evaluation=leaf,
    )
    runtime_frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (
            ExtremeSustainedDPSRuntimeStateChoice("runtime:a", "snapshot-a"),
            ExtremeSustainedDPSRuntimeStateChoice("runtime:b", "snapshot-b"),
        ),
        denominator_proven=True,
        source="reviewed local runtime family",
    )

    result = service.search(
        _State(),
        required_duration_seconds=10.0,
        runtime_snapshot="fallback-snapshot",
        target_health=100,
        target_resistance=0.0,
        runtime_state_frontier=runtime_frontier,
    )

    assert result.evaluated_leaf_count == 4
    assert result.best_modeled_dps == 1.0
    assert result.global_maximum_proven is True


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("required_duration_seconds", "10", "required_duration_seconds must be numeric"),
        ("target_health", True, "target_health must be an integer"),
        ("target_resistance", "18200", "target_resistance must be numeric"),
        ("target_name", "", "target_name must be a non-empty string"),
        ("initial_bar", 1, "initial_bar must be a string"),
        ("root_key", "", "root_key must be a non-empty string"),
    ),
)
def test_pipeline_search_rejects_coerced_scalar_inputs(field, value, match) -> None:
    service = ExtremeSustainedDPSGeneratedAxisPipelineSearchService(
        pipeline=_Pipeline(),
        leaf_evaluation=_LeafEvaluation(),
    )
    kwargs = {
        "required_duration_seconds": 10.0,
        "runtime_snapshot": "snapshot",
        "target_health": 100,
        "target_resistance": 0.0,
    }
    kwargs[field] = value

    with pytest.raises((TypeError, ValueError), match=match):
        service.search(_State(), **kwargs)


def test_pipeline_search_rejects_invalid_scalar_ranges() -> None:
    service = ExtremeSustainedDPSGeneratedAxisPipelineSearchService(
        pipeline=_Pipeline(),
        leaf_evaluation=_LeafEvaluation(),
    )

    with pytest.raises(ValueError, match="required_duration_seconds must be finite and positive"):
        service.search(
            _State(),
            required_duration_seconds=0.0,
            runtime_snapshot="snapshot",
            target_health=100,
            target_resistance=0.0,
        )

    with pytest.raises(ValueError, match="target_health must be positive"):
        service.search(
            _State(),
            required_duration_seconds=10.0,
            runtime_snapshot="snapshot",
            target_health=0,
            target_resistance=0.0,
        )

    with pytest.raises(ValueError, match="initial_bar must be 'front' or 'back'"):
        service.search(
            _State(),
            required_duration_seconds=10.0,
            runtime_snapshot="snapshot",
            target_health=100,
            target_resistance=0.0,
            initial_bar="middle",
        )
