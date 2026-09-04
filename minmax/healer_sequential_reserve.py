from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .healer_reserve_bridge import HealerReserveProtectionBridgeResult
from .healer_reserve_decision import (
    HealerReserveDecisionResult,
    propose_healer_reserve_decision,
)
from .rotation_plan import RotationPlan
from .rotation_reserve_priority import ReserveProtectionPriority


@dataclass(frozen=True)
class HealerSequentialReserveStep:
    """Caller-recomputed inputs for one demand against the current plan.

    ``bridge`` must be built from the same current plan passed to the evaluator.
    This keeps resource/timeline consequences delegated to the existing sustain
    pipeline while allowing later demand windows to observe earlier schedule
    adjustments.
    """

    bridge: HealerReserveProtectionBridgeResult
    priorities: tuple[ReserveProtectionPriority, ...]


HealerSequentialStepEvaluator = Callable[
    [RotationPlan, int],
    HealerSequentialReserveStep,
]


@dataclass(frozen=True)
class HealerSequentialReserveResult:
    """Ordered healer reserve decisions sharing one evolving rotation plan."""

    original_plan: RotationPlan
    final_plan: RotationPlan
    decisions: tuple[HealerReserveDecisionResult, ...]



def propose_sequential_healer_reserve_decisions(
    *,
    plan: RotationPlan,
    step_count: int,
    evaluate_step: HealerSequentialStepEvaluator,
) -> HealerSequentialReserveResult:
    """Apply multiple healer demand decisions to one evolving schedule.

    The evaluator is called once per step with the plan produced by the previous
    decision. It is therefore responsible for recomputing the demand-policy
    bridge, resource timeline, and reserve assessment against that exact plan.
    Demand windows may overlap (for example staggered Ice Cages), but their start
    times must strictly increase so execution order is deterministic.
    """

    count = int(step_count)
    if count < 0:
        raise ValueError("healer sequential reserve step count cannot be negative")

    current = plan
    decisions: list[HealerReserveDecisionResult] = []
    previous_start: float | None = None

    for index in range(count):
        step = evaluate_step(current, index)
        demand = step.bridge.demand_assessment.demand

        if previous_start is not None and demand.start_seconds <= previous_start:
            raise ValueError(
                "healer sequential demand starts must strictly increase: "
                f"{demand.name} starts at {demand.start_seconds:g}s after {previous_start:g}s"
            )

        decision = propose_healer_reserve_decision(
            plan=current,
            bridge=step.bridge,
            priorities=step.priorities,
        )
        decisions.append(decision)
        current = decision.adjustment.adjusted_plan
        previous_start = demand.start_seconds

    return HealerSequentialReserveResult(
        original_plan=plan,
        final_plan=current,
        decisions=tuple(decisions),
    )
