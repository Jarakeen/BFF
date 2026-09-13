from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_cross_bar_route_proposal_service import RotationCrossBarRouteProposal


@dataclass(frozen=True)
class RotationCrossBarRouteSlotFeasibility:
    wait_time_seconds: float
    source_bar: str
    target_bar: str
    filler_skill_name: str
    required_wait_slots: int
    available_wait_times: tuple[float, ...]
    feasible: bool
    reason: str


class RotationCrossBarRouteSlotFeasibilityService:
    """Check whether a proposed cross-bar route fits the current 1-second slot model.

    The semi-static planner models BAR_SWAP as its own scheduled step. Therefore a
    cross-bar filler cannot be inserted into a single WAIT slot without inventing
    sub-GCD swap timing. Under the current model a route requires two consecutive
    WAIT slots for ``swap -> filler`` and three when a return swap is required before
    the next explicit skill obligation.

    This service is diagnostic only and never mutates the plan.
    """

    _EPSILON = 1e-9

    def assess(
        self,
        plan: RotationPlan,
        proposals: tuple[RotationCrossBarRouteProposal, ...],
    ) -> tuple[RotationCrossBarRouteSlotFeasibility, ...]:
        wait_times = {
            float(action.time_seconds)
            for action in plan.actions
            if action.kind is RotationActionKind.WAIT
        }
        results: list[RotationCrossBarRouteSlotFeasibility] = []

        for proposal in proposals:
            start = float(proposal.wait_time_seconds)
            required = 3 if proposal.return_swap_required else 2
            candidate_times = tuple(start + float(offset) for offset in range(required))
            available = tuple(
                value
                for value in candidate_times
                if self._contains_time(wait_times, value)
            )

            before_next_required = True
            if proposal.next_required_time_seconds is not None:
                final_route_time = candidate_times[-1]
                before_next_required = (
                    final_route_time + self._EPSILON
                    < float(proposal.next_required_time_seconds)
                )

            feasible = len(available) == required and before_next_required
            if len(available) != required:
                reason = (
                    f"requires {required} consecutive WAIT slots from {start:g}s but "
                    f"only {len(available)} are available"
                )
            elif not before_next_required:
                reason = (
                    "route would consume or collide with the next explicit skill "
                    f"obligation at {float(proposal.next_required_time_seconds):g}s"
                )
            else:
                reason = "route fits the current 1-second BAR_SWAP/filler timing model"

            results.append(
                RotationCrossBarRouteSlotFeasibility(
                    wait_time_seconds=start,
                    source_bar=proposal.source_bar,
                    target_bar=proposal.target_bar,
                    filler_skill_name=proposal.filler_skill_name,
                    required_wait_slots=required,
                    available_wait_times=available,
                    feasible=feasible,
                    reason=reason,
                )
            )

        return tuple(results)

    @classmethod
    def _contains_time(cls, values: set[float], target: float) -> bool:
        return any(abs(value - target) <= cls._EPSILON for value in values)


__all__ = [
    "RotationCrossBarRouteSlotFeasibility",
    "RotationCrossBarRouteSlotFeasibilityService",
]
