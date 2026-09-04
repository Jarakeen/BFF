from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_action_selection import RotationActionSelectionResult
from .rotation_bar_swap_selection import RotationBarSwapSelectionResult
from .rotation_plan import RotationAction, RotationActionKind


@dataclass(frozen=True)
class RotationDecisionScheduleResult:
    """Concrete schedule output for one already-evaluated rotation decision point."""

    action: RotationAction | None
    reason: str


def schedule_priority_decision(
    *,
    time_seconds: float,
    sequence: int,
    action_selection: RotationActionSelectionResult,
    bar_swap_selection: RotationBarSwapSelectionResult,
) -> RotationDecisionScheduleResult:
    """Convert proven priority decisions into one explicit scheduled action.

    This adapter does not invent timing, legality, costs, or bar-swap duration.
    The caller supplies the decision timestamp and sequence. When the bar-swap
    selector says a swap is required, the scheduled output is exactly one
    ``BAR_SWAP`` action. Otherwise the selected legal ability on the current bar
    becomes one ``SKILL`` action. If neither exists, no action is manufactured.
    """

    time_value = float(time_seconds)
    if not math.isfinite(time_value) or time_value < 0:
        raise ValueError("rotation decision schedule time must be finite and non-negative")
    sequence_value = int(sequence)
    if sequence_value < 0:
        raise ValueError("rotation decision schedule sequence cannot be negative")

    if action_selection.current_bar != bar_swap_selection.current_bar:
        raise ValueError(
            "rotation decision scheduling requires action and bar-swap selections "
            "from the same current bar"
        )
    if action_selection.demand != bar_swap_selection.demand:
        raise ValueError(
            "rotation decision scheduling requires action and bar-swap selections "
            "from the same demand context"
        )

    if bar_swap_selection.should_swap:
        destination = bar_swap_selection.destination_bar
        if destination is None:
            raise ValueError("bar-swap selection requires a destination when should_swap is true")
        return RotationDecisionScheduleResult(
            action=RotationAction(
                time_seconds=time_value,
                sequence=sequence_value,
                kind=RotationActionKind.BAR_SWAP,
                bar=destination,
            ),
            reason=bar_swap_selection.reason,
        )

    selected = action_selection.selected
    if selected is None:
        return RotationDecisionScheduleResult(
            action=None,
            reason="no legal selected ability and no bar swap required",
        )

    entry = selected.priority.entry
    return RotationDecisionScheduleResult(
        action=RotationAction(
            time_seconds=time_value,
            sequence=sequence_value,
            kind=RotationActionKind.SKILL,
            name=entry.skill_name,
            bar=entry.bar,
        ),
        reason=(
            f"selected priority {selected.priority.effective_priority} ability "
            f"on {entry.bar} bar"
        ),
    )
