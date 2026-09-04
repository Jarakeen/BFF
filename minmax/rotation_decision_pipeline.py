from __future__ import annotations

from dataclasses import dataclass

from .rotation_ability_priority import AbilityPriorityList
from .rotation_action_selection import (
    AbilityActionEligibility,
    RotationActionSelectionResult,
    select_priority_ability_action,
)
from .rotation_bar_swap_selection import (
    RotationBarSwapSelectionResult,
    select_priority_bar_swap,
)
from .rotation_decision_progression import RotationDecisionEvaluation
from .rotation_demand_window import RotationDemandWindow


@dataclass(frozen=True)
class RotationDecisionPipelineResult:
    """Auditable composed result for one rotation decision point."""

    evaluation: RotationDecisionEvaluation
    action_selection: RotationActionSelectionResult
    bar_swap_selection: RotationBarSwapSelectionResult


def evaluate_priority_decision(
    *,
    priorities: AbilityPriorityList,
    current_bar: str,
    eligibility: tuple[AbilityActionEligibility, ...],
    demand: RotationDemandWindow | None = None,
) -> RotationDecisionPipelineResult:
    """Run the role-neutral priority and explicit bar-swap selectors together.

    This function intentionally contains no ESO timing, sustain, cooldown,
    effect, encounter, or resource formulas. It only composes already-proven
    eligibility evidence with the role-neutral priority list so callers cannot
    accidentally build action and bar-swap decisions from different inputs.
    """

    action_selection = select_priority_ability_action(
        priorities=priorities,
        current_bar=current_bar,
        eligibility=eligibility,
        demand=demand,
    )
    bar_swap_selection = select_priority_bar_swap(
        priorities=priorities,
        current_bar=current_bar,
        eligibility=eligibility,
        demand=demand,
    )
    evaluation = RotationDecisionEvaluation(
        action_selection=action_selection,
        bar_swap_selection=bar_swap_selection,
    )
    return RotationDecisionPipelineResult(
        evaluation=evaluation,
        action_selection=action_selection,
        bar_swap_selection=bar_swap_selection,
    )
