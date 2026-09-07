from __future__ import annotations

from .healer_heavy_attack_runtime_candidates import HeavyAttackDecisionWindow
from .rotation_wait_decision import PrematureRecastDecisionContext


def derive_heavy_attack_decision_window(
    *,
    context: PrematureRecastDecisionContext,
    required_window_seconds: float,
    encounter_allows_channel: bool = True,
    higher_priority_action_ready: bool = False,
) -> HeavyAttackDecisionWindow:
    """Derive channel and refresh evidence from one duration WAIT decision point.

    The available window ends at the earliest of the next scheduled decision,
    the fixed plan horizon, or the next same-bar verified refresh obligation.
    This deliberately refuses to assume that a multi-second heavy may overlap a
    later scheduled action. Encounter safety and higher-priority action state are
    still caller-owned evidence.
    """

    if context.bar not in {"front", "back"}:
        raise ValueError("heavy attack wait window requires an active front or back bar")

    start = float(context.time_seconds)
    boundaries: list[float] = []

    if context.next_decision_time_seconds is not None:
        next_decision = float(context.next_decision_time_seconds)
        if next_decision >= start:
            boundaries.append(next_decision)

    if context.plan_end_seconds is not None:
        plan_end = float(context.plan_end_seconds)
        if plan_end >= start:
            boundaries.append(plan_end)

    same_bar_due = [
        float(due_time)
        for _, bar, due_time in context.next_due
        if bar == context.bar and float(due_time) >= start
    ]
    if same_bar_due:
        boundaries.append(min(same_bar_due))

    available = min(boundaries) - start if boundaries else 0.0
    required = float(required_window_seconds)
    refresh_collision = any(
        bar == context.bar and start < float(due_time) < start + required
        for _, bar, due_time in context.next_due
    )

    return HeavyAttackDecisionWindow(
        time_seconds=start,
        bar=context.bar,
        available_window_seconds=max(0.0, available),
        required_window_seconds=required,
        encounter_allows_channel=encounter_allows_channel,
        higher_priority_action_ready=higher_priority_action_ready,
        refresh_due_before_completion=refresh_collision,
    )
