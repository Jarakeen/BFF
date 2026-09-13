from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_cross_bar_filler_opportunity_service import (
    RotationCrossBarFillerOpportunity,
)


@dataclass(frozen=True)
class RotationCrossBarRouteProposal:
    wait_time_seconds: float
    source_bar: str
    target_bar: str
    filler_skill_name: str
    filler_priority: int | None
    next_required_bar: str | None
    next_required_time_seconds: float | None
    return_swap_required: bool


class RotationCrossBarRouteProposalService:
    """Describe bar-routing required to consume proven cross-bar filler opportunities.

    Diagnostic only. This service does not mutate a RotationPlan or assign sub-second
    swap timing. It answers a narrower question: after using an opposite-bar filler at
    a WAIT opportunity, does the remaining plan next require returning to the source
    bar, and when does that next explicit skill action occur?

    The result is intentionally conservative. Only explicit future skill actions are
    treated as a required bar destination; WAITs and BAR_SWAP actions do not invent a
    skill obligation here. Actual schedule mutation belongs to a later routing layer.
    """

    def propose(
        self,
        plan: RotationPlan,
        opportunities: tuple[RotationCrossBarFillerOpportunity, ...],
    ) -> tuple[RotationCrossBarRouteProposal, ...]:
        proposals: list[RotationCrossBarRouteProposal] = []
        for opportunity in opportunities:
            next_bar, next_time = self._next_required_skill_bar(
                plan,
                after_seconds=opportunity.wait_time_seconds,
            )
            proposals.append(
                RotationCrossBarRouteProposal(
                    wait_time_seconds=opportunity.wait_time_seconds,
                    source_bar=opportunity.wait_bar,
                    target_bar=opportunity.target_bar,
                    filler_skill_name=opportunity.filler_skill_name,
                    filler_priority=opportunity.filler_priority,
                    next_required_bar=next_bar,
                    next_required_time_seconds=next_time,
                    return_swap_required=(
                        next_bar is not None
                        and next_bar != opportunity.target_bar
                    ),
                )
            )
        return tuple(proposals)

    @staticmethod
    def _next_required_skill_bar(
        plan: RotationPlan,
        *,
        after_seconds: float,
    ) -> tuple[str | None, float | None]:
        candidates = [
            action
            for action in plan.actions
            if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
            and action.time_seconds > float(after_seconds)
            and str(action.bar or "").strip().casefold() in {"front", "back"}
        ]
        if not candidates:
            return None, None
        action = min(candidates, key=lambda item: (item.time_seconds, item.sequence))
        return str(action.bar).strip().casefold(), float(action.time_seconds)


__all__ = [
    "RotationCrossBarRouteProposal",
    "RotationCrossBarRouteProposalService",
]
