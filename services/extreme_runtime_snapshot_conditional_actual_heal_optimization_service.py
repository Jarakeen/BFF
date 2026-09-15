from __future__ import annotations

"""Snapshot-aware bridge for conditional Extreme actual-heal optimization.

The underlying conditional optimizer still owns healer-specific legality and scoring.
This adapter only migrates two legacy boolean scenario inputs onto E1's role-neutral
runtime-condition timeline so production callers do not maintain parallel truth.
"""

from services.extreme_conditional_actual_heal_optimization_service import (
    ExtremeConditionalActualHealOptimizationService,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot


RESTORATION_HEAVY_POST_COMPLETION_CONDITION = (
    "restoration_staff_heavy_post_completion_window"
)
SACRED_GROUND_CONDITION = "sacred_ground_window"


class ExtremeRuntimeSnapshotConditionalActualHealOptimizationService(
    ExtremeConditionalActualHealOptimizationService
):
    """Derive reviewed healer scenario windows from one unified runtime snapshot."""

    def __init__(
        self,
        *,
        runtime_snapshot: ExtremeRuntimeSnapshot | None = None,
        fully_charged_restoration_heavy_attack_completed: bool = False,
        sacred_ground_window_active: bool = False,
        **kwargs,
    ) -> None:
        active_conditions = (
            frozenset()
            if runtime_snapshot is None
            else frozenset(runtime_snapshot.active_condition_ids)
        )
        super().__init__(
            runtime_snapshot=runtime_snapshot,
            fully_charged_restoration_heavy_attack_completed=(
                bool(fully_charged_restoration_heavy_attack_completed)
                or RESTORATION_HEAVY_POST_COMPLETION_CONDITION in active_conditions
            ),
            sacred_ground_window_active=(
                bool(sacred_ground_window_active)
                or SACRED_GROUND_CONDITION in active_conditions
            ),
            **kwargs,
        )


__all__ = [
    "ExtremeRuntimeSnapshotConditionalActualHealOptimizationService",
    "RESTORATION_HEAVY_POST_COMPLETION_CONDITION",
    "SACRED_GROUND_CONDITION",
]
