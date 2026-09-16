from __future__ import annotations

from minmax.block_stats import BlockStatCalculator
from minmax.stat_ids import StatId
from services.extreme_optimization_service import (
    EXTREME_OBJECTIVES,
    ExtremeObjective,
    ExtremeOptimizationService,
)


CRITICAL_HEALING_OBJECTIVE = ExtremeObjective(
    "critical_healing",
    "Critical Healing",
    ratio=True,
)
BLOCK_MITIGATION_OBJECTIVE = ExtremeObjective(
    "block_mitigation",
    "Block Mitigation",
    ratio=True,
)
BLOCK_COST_REDUCTION_OBJECTIVE = ExtremeObjective(
    "block_cost_reduction",
    "Block Cost Reduction",
    ratio=True,
)

COMPLETE_EXTREME_OBJECTIVES: tuple[ExtremeObjective, ...] = (
    *EXTREME_OBJECTIVES,
    CRITICAL_HEALING_OBJECTIVE,
    BLOCK_MITIGATION_OBJECTIVE,
    BLOCK_COST_REDUCTION_OBJECTIVE,
)

_COMPLETE_OBJECTIVE_BY_KEY = {
    objective.key: objective for objective in COMPLETE_EXTREME_OBJECTIVES
}


class ExtremeCompleteOptimizationService(ExtremeOptimizationService):
    """Completion layer for shared snapshot/stat Extreme objectives.

    The legacy Extreme service remains the canonical evaluator for its existing
    objective catalog. This layer adds reviewed objectives whose canonical math
    already exists in shared character-state services, rather than inventing
    parallel combat math.

    Critical Healing is read from the shared derived-stat pipeline. Block
    Mitigation and Block Cost Reduction reuse the canonical ``BlockStatCalculator``
    traces assembled by the build context. The block-cost record is expressed as
    the fraction removed from ESO's canonical 1750 base cost so the inherited
    optimizer can retain its ordinary "higher is better" scoring contract.
    """

    @staticmethod
    def objective(key: str) -> ExtremeObjective:
        normalized = str(key or "").strip().casefold()
        if normalized not in _COMPLETE_OBJECTIVE_BY_KEY:
            raise ValueError(f"Unknown extreme optimization objective: {key!r}")
        return _COMPLETE_OBJECTIVE_BY_KEY[normalized]

    @staticmethod
    def _objective_value(context, objective: ExtremeObjective) -> float:
        if objective.key == "critical_healing":
            trace = context.core_state.derived.get(StatId.CRITICAL_HEALING)
            if trace is None:
                raise ValueError("Canonical core stat is unavailable for Critical Healing")
            return float(trace.final_value)

        if objective.key == "block_mitigation":
            trace = context.core_state.derived.get(StatId.BLOCK_MITIGATION)
            if trace is None:
                raise ValueError("Canonical core stat is unavailable for Block Mitigation")
            return float(trace.final_value)

        if objective.key == "block_cost_reduction":
            trace = context.core_state.derived.get(StatId.BLOCK_COST)
            if trace is None:
                raise ValueError("Canonical core stat is unavailable for Block Cost")
            base = float(BlockStatCalculator.BASE_BLOCK_COST)
            return max(0.0, (base - float(trace.final_value)) / base)

        return ExtremeOptimizationService._objective_value(context, objective)
