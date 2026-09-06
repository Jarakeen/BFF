from __future__ import annotations

from dataclasses import dataclass
import math

from .heavy_attack_opportunity import HeavyAttackOpportunity
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
    heavy_attack_opportunity: HeavyAttackOpportunity | None = None,
    heavy_attack_bar: str | None = None,
) -> RotationDecisionScheduleResult:
    """Convert proven priority decisions into one explicit scheduled action.

    This adapter does not invent timing, legality, costs, or bar-swap duration.
    The caller supplies the decision timestamp and sequence. An optional heavy
    attack opportunity may claim the current-bar action only when its upstream
    evidence has already established that no higher-priority legal action should
    take precedence. Otherwise the existing bar-swap and selected-skill behavior
    is preserved exactly.
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

    if heavy_attack_opportunity is not None:
        if heavy_attack_bar is None:
            raise ValueError("heavy attack scheduling requires the equipped bar")
        bar = str(heavy_attack_bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("heavy attack bar must be front or back")
        if bar != action_selection.current_bar:
            raise ValueError(
                "heavy attack opportunity must belong to the current rotation bar"
            )
        if heavy_attack_opportunity.recommended:
            return RotationDecisionScheduleResult(
                action=RotationAction(
                    time_seconds=time_value,
                    sequence=sequence_value,
                    kind=RotationActionKind.HEAVY_ATTACK,
                    bar=bar,
                ),
                reason=heavy_attack_opportunity.reason,
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
