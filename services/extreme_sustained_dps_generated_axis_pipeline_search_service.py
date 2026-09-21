from __future__ import annotations

"""Run the composed generated-axis pipeline through proof-safe branch-and-bound."""

from services.extreme_sustained_dps_generated_axis_pipeline_service import (
    ExtremeSustainedDPSGeneratedAxisPipelineService,
    ExtremeSustainedDPSGeneratedAxisPipelineState,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierWiringService,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSGeneratedSearchResult,
)


class ExtremeSustainedDPSGeneratedAxisPipelineSearchService:
    """Bind one pipeline root and exact runtime scenario to the search coordinator."""

    def __init__(
        self,
        *,
        pipeline: ExtremeSustainedDPSGeneratedAxisPipelineService | object,
        leaf_evaluation: object,
    ) -> None:
        self.pipeline = pipeline
        self.leaf_evaluation = leaf_evaluation

    def search(
        self,
        root_state: ExtremeSustainedDPSGeneratedAxisPipelineState | object,
        *,
        required_duration_seconds: float,
        runtime_snapshot: object,
        target_health: int,
        target_resistance: float,
        target_name: str = "Boss",
        initial_bar: str = "front",
        root_key: str = "generated-root",
        root_bound_inputs=None,
        branch_bound_inputs=None,
    ) -> ExtremeSustainedDPSGeneratedSearchResult:
        evaluate_leaf = self.leaf_evaluation.evaluator(
            runtime_snapshot=runtime_snapshot,
            target_health=int(target_health),
            target_resistance=float(target_resistance),
            target_name=target_name,
            initial_bar=initial_bar,
        )
        return ExtremeSustainedDPSGeneratedFrontierWiringService.search(
            root_state,
            axes=tuple(self.pipeline.axes()),
            evaluate_leaf=evaluate_leaf,
            required_duration_seconds=float(required_duration_seconds),
            root_key=root_key,
            root_bound_inputs=root_bound_inputs,
            branch_bound_inputs=branch_bound_inputs,
        )


__all__ = ["ExtremeSustainedDPSGeneratedAxisPipelineSearchService"]
