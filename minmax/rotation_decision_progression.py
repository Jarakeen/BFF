from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import math

from .rotation_action_selection import RotationActionSelectionResult
from .rotation_bar_swap_selection import RotationBarSwapSelectionResult
from .rotation_decision_scheduling import (
    RotationDecisionScheduleResult,
    schedule_priority_decision,
)
from .rotation_plan import RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationDecisionPoint:
    """One caller-supplied scheduler decision timestamp.

    Phase 13 deliberately does not invent GCD, cast, or bar-swap spacing here.
    The caller owns the explicit decision times; this layer only carries state
    forward between them.
    """

    time_seconds: float
    sequence: int

    def __post_init__(self) -> None:
        time_value = float(self.time_seconds)
        if not math.isfinite(time_value) or time_value < 0:
            raise ValueError("rotation decision point time must be finite and non-negative")
        sequence_value = int(self.sequence)
        if sequence_value < 0:
            raise ValueError("rotation decision point sequence cannot be negative")
        object.__setattr__(self, "time_seconds", time_value)
        object.__setattr__(self, "sequence", sequence_value)


@dataclass(frozen=True)
class RotationDecisionEvaluation:
    action_selection: RotationActionSelectionResult
    bar_swap_selection: RotationBarSwapSelectionResult


RotationDecisionEvaluator = Callable[
    [str, int, RotationDecisionPoint],
    RotationDecisionEvaluation,
]


@dataclass(frozen=True)
class RotationDecisionProgressionStep:
    index: int
    decision_point: RotationDecisionPoint
    bar_before: str
    bar_after: str
    evaluation: RotationDecisionEvaluation
    scheduled: RotationDecisionScheduleResult


@dataclass(frozen=True)
class RotationDecisionProgressionResult:
    initial_bar: str
    final_bar: str
    steps: tuple[RotationDecisionProgressionStep, ...]
    plan: RotationPlan


def build_rotation_plan_from_decisions(
    *,
    character_name: str,
    build_name: str,
    duration_seconds: float,
    initial_bar: str,
    decision_points: tuple[RotationDecisionPoint, ...],
    evaluate_decision: RotationDecisionEvaluator,
) -> RotationDecisionProgressionResult:
    """Build a deterministic plan from explicit decision points and proven choices.

    The evaluator receives the active bar produced by the prior decision. A
    scheduled skill leaves the active bar unchanged; a scheduled ``BAR_SWAP``
    moves the active bar to its explicit destination. Decision timestamps must
    strictly increase so this layer never implies a zero-time swap-and-cast
    transition whose timing has not been canonically established.
    """

    bar = str(initial_bar or "").strip().casefold()
    if bar not in {"front", "back"}:
        raise ValueError("rotation decision progression initial bar must be front or back")

    duration = float(duration_seconds)
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("rotation decision progression duration must be finite and non-negative")

    previous_time: float | None = None
    seen_order_keys: set[tuple[float, int]] = set()
    actions = []
    steps: list[RotationDecisionProgressionStep] = []

    for index, point in enumerate(tuple(decision_points)):
        if point.time_seconds > duration:
            raise ValueError("rotation decision point cannot occur after plan duration")
        if previous_time is not None and point.time_seconds <= previous_time:
            raise ValueError("rotation decision point times must strictly increase")
        order_key = (point.time_seconds, point.sequence)
        if order_key in seen_order_keys:
            raise ValueError("duplicate rotation decision point time and sequence")
        seen_order_keys.add(order_key)

        bar_before = bar
        evaluation = evaluate_decision(bar_before, index, point)
        if evaluation.action_selection.current_bar != bar_before:
            raise ValueError(
                "rotation decision evaluator action selection does not match active bar"
            )
        if evaluation.bar_swap_selection.current_bar != bar_before:
            raise ValueError(
                "rotation decision evaluator bar-swap selection does not match active bar"
            )

        scheduled = schedule_priority_decision(
            time_seconds=point.time_seconds,
            sequence=point.sequence,
            action_selection=evaluation.action_selection,
            bar_swap_selection=evaluation.bar_swap_selection,
        )
        action = scheduled.action
        if action is not None:
            actions.append(action)
            if action.kind is RotationActionKind.BAR_SWAP:
                if action.bar is None:
                    raise ValueError("scheduled bar swap is missing destination bar")
                bar = action.bar

        steps.append(
            RotationDecisionProgressionStep(
                index=index,
                decision_point=point,
                bar_before=bar_before,
                bar_after=bar,
                evaluation=evaluation,
                scheduled=scheduled,
            )
        )
        previous_time = point.time_seconds

    plan = RotationPlan(
        character_name=character_name,
        build_name=build_name,
        duration_seconds=duration,
        actions=tuple(actions),
    )
    return RotationDecisionProgressionResult(
        initial_bar=str(initial_bar).strip().casefold(),
        final_bar=bar,
        steps=tuple(steps),
        plan=plan,
    )
