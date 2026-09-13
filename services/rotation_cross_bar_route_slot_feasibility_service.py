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
    """Check whether a proposed cross-bar filler route fits one skill-GCD slot.

    ESO weapon swap is not a separate skill global cooldown. A player may swap bars
    between skill casts without consuming another one-second skill slot, including
    swap-cancel play that returns to the source bar after the target-bar filler. The
    semi-static planner therefore needs one WAIT skill slot for either
    ``swap -> LA/skill`` or ``swap -> LA/skill -> return swap``.

    The next explicit skill obligation must still occur strictly after the filler
    slot. This service never invents an additional skill cast, refresh timing, or bar
    route when no WAIT slot exists.

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
            required = 1
            candidate_times = (start,)
            available = tuple(
                value
                for value in candidate_times
                if self._contains_time(wait_times, value)
            )

            before_next_required = True
            if proposal.next_required_time_seconds is not None:
                before_next_required = (
                    start + self._EPSILON
                    < float(proposal.next_required_time_seconds)
                )

            feasible = len(available) == required and before_next_required
            if len(available) != required:
                reason = f"requires a WAIT skill slot at {start:g}s but none is available"
            elif not before_next_required:
                reason = (
                    "route filler would consume or collide with the next explicit skill "
                    f"obligation at {float(proposal.next_required_time_seconds):g}s"
                )
            else:
                return_note = " with same-GCD return swap" if proposal.return_swap_required else ""
                reason = (
                    "route fits one skill-GCD WAIT slot using non-GCD bar swap"
                    + return_note
                )

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
