from __future__ import annotations

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

COMPLETE_EXTREME_OBJECTIVES: tuple[ExtremeObjective, ...] = (
    *EXTREME_OBJECTIVES,
    CRITICAL_HEALING_OBJECTIVE,
)

_COMPLETE_OBJECTIVE_BY_KEY = {
    objective.key: objective for objective in COMPLETE_EXTREME_OBJECTIVES
}


class ExtremeCompleteOptimizationService(ExtremeOptimizationService):
    """Completion layer for sheet-stat Extreme objectives.

    The legacy Extreme service remains the canonical evaluator for its existing
    objective catalog. This layer adds reviewed objectives whose StatIds already
    exist in the shared character-state pipeline, rather than inventing parallel
    combat math.
    """

    @staticmethod
    def objective(key: str) -> ExtremeObjective:
        normalized = str(key or "").strip().casefold()
        if normalized not in _COMPLETE_OBJECTIVE_BY_KEY:
            raise ValueError(f"Unknown extreme optimization objective: {key!r}")
        return _COMPLETE_OBJECTIVE_BY_KEY[normalized]

    @staticmethod
    def _objective_value(context, objective: ExtremeObjective) -> float:
        if objective.key != "critical_healing":
            return ExtremeOptimizationService._objective_value(context, objective)

        trace = context.core_state.derived.get(StatId.CRITICAL_HEALING)
        if trace is None:
            raise ValueError("Canonical core stat is unavailable for Critical Healing")
        return float(trace.final_value)
