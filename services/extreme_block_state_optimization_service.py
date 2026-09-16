from __future__ import annotations

from minmax.block_stats import BlockStatCalculator
from minmax.stat_ids import StatId
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_optimization_service import ExtremeObjective


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

_BLOCK_OBJECTIVES: tuple[ExtremeObjective, ...] = (
    BLOCK_MITIGATION_OBJECTIVE,
    BLOCK_COST_REDUCTION_OBJECTIVE,
)
_BLOCK_OBJECTIVE_BY_KEY = {objective.key: objective for objective in _BLOCK_OBJECTIVES}


class ExtremeBlockStateOptimizationService(ExtremeCompleteOptimizationService):
    """Reuse canonical build/block math for the two Extreme block-state records.

    This service deliberately does not implement block mechanics.  Existing
    ``BuildCalculationContext`` assembly already owns Sturdy, armor-weight
    penalties/passives, One Hand and Shield passives, CP, gear effects, and the
    canonical ``BlockStatCalculator`` stacking/rounding rules.  Extreme only adds
    objective scoring on top of those traces.

    ``block_mitigation`` maximizes the canonical mitigation ratio directly.
    ``block_cost_reduction`` maximizes the fraction removed from ESO's canonical
    1750 base block cost.  Returning a reduction ratio keeps the inherited Extreme
    optimizer's "higher is better" contract without inverting or duplicating the
    underlying block-cost calculation.
    """

    @staticmethod
    def objective(key: str) -> ExtremeObjective:
        normalized = str(key or "").strip().casefold()
        if normalized in _BLOCK_OBJECTIVE_BY_KEY:
            return _BLOCK_OBJECTIVE_BY_KEY[normalized]
        return ExtremeCompleteOptimizationService.objective(normalized)

    @staticmethod
    def _objective_value(context, objective: ExtremeObjective) -> float:
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

        return ExtremeCompleteOptimizationService._objective_value(context, objective)


__all__ = [
    "BLOCK_COST_REDUCTION_OBJECTIVE",
    "BLOCK_MITIGATION_OBJECTIVE",
    "ExtremeBlockStateOptimizationService",
]
