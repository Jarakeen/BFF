from __future__ import annotations

import math

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
from services.extreme_sustained_dps_generated_runtime_state_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService,
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
        runtime_state_frontier=None,
    ) -> ExtremeSustainedDPSGeneratedSearchResult:
        if isinstance(required_duration_seconds, bool) or not isinstance(
            required_duration_seconds,
            (int, float),
        ):
            raise TypeError("required_duration_seconds must be numeric")
        duration = float(required_duration_seconds)
        if not math.isfinite(duration) or duration <= 0.0:
            raise ValueError("required_duration_seconds must be finite and positive")
        if isinstance(target_health, bool) or not isinstance(target_health, int):
            raise TypeError("target_health must be an integer")
        if target_health <= 0:
            raise ValueError("target_health must be positive")
        if isinstance(target_resistance, bool) or not isinstance(target_resistance, (int, float)):
            raise TypeError("target_resistance must be numeric")
        resistance = float(target_resistance)
        if not math.isfinite(resistance):
            raise ValueError("target_resistance must be finite")
        if not isinstance(target_name, str) or not target_name.strip():
            raise TypeError("target_name must be a non-empty string")
        if not isinstance(initial_bar, str):
            raise TypeError("initial_bar must be a string")
        normalized_bar = initial_bar.strip().casefold()
        if normalized_bar not in {"front", "back"}:
            raise ValueError("initial_bar must be 'front' or 'back'")
        if not isinstance(root_key, str) or not root_key.strip():
            raise TypeError("root_key must be a non-empty string")

        evaluate_leaf = self.leaf_evaluation.evaluator(
            runtime_snapshot=runtime_snapshot,
            target_health=target_health,
            target_resistance=resistance,
            target_name=target_name.strip(),
            initial_bar=normalized_bar,
        )
        axes = tuple(self.pipeline.axes())
        if runtime_state_frontier is not None:
            axes = (
                *axes,
                ExtremeSustainedDPSGeneratedRuntimeStateAxisAdapterService.axis(
                    runtime_state_frontier
                ),
            )

        return ExtremeSustainedDPSGeneratedFrontierWiringService.search(
            root_state,
            axes=axes,
            evaluate_leaf=evaluate_leaf,
            required_duration_seconds=duration,
            root_key=root_key.strip(),
            root_bound_inputs=root_bound_inputs,
            branch_bound_inputs=branch_bound_inputs,
        )


__all__ = ["ExtremeSustainedDPSGeneratedAxisPipelineSearchService"]
