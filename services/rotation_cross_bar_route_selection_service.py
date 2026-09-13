from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_cross_bar_route_proposal_service import RotationCrossBarRouteProposal
from services.rotation_cross_bar_route_slot_feasibility_service import (
    RotationCrossBarRouteSlotFeasibility,
)


@dataclass(frozen=True)
class RotationCrossBarRouteSelection:
    proposal: RotationCrossBarRouteProposal
    reserved_wait_times: tuple[float, ...]
    outbound_swap_required: bool = True


@dataclass(frozen=True)
class RotationCrossBarRouteRejection:
    proposal: RotationCrossBarRouteProposal
    reason: str


@dataclass(frozen=True)
class RotationCrossBarRouteSelectionResult:
    selected: tuple[RotationCrossBarRouteSelection, ...]
    rejected: tuple[RotationCrossBarRouteRejection, ...]


class RotationCrossBarRouteSelectionService:
    """Select a non-overlapping, active-bar-consistent set of feasible routes.

    Feasibility rows are local facts. Two individually feasible routes may still
    compete for the same WAIT slot, and accepting an earlier stay-on-target route can
    change the active bar seen by a later route. This service resolves those joint
    constraints in deterministic timeline order without mutating the plan.

    If an earlier selected route has already placed the player on a later proposal's
    target bar, that proposal remains usable: its filler can occupy the WAIT skill slot
    without another outbound swap. The selection records that fact explicitly rather
    than rejecting the route because its original source-bar assumption became stale.

    The current planner starts on the front bar. Original BAR_SWAP actions remain the
    authority between selected routes; selected routes contribute their proven target-
    bar state and optional return-swap transitions.
    """

    _EPSILON = 1e-9

    def select(
        self,
        plan: RotationPlan,
        proposals: tuple[RotationCrossBarRouteProposal, ...],
        feasibility: tuple[RotationCrossBarRouteSlotFeasibility, ...],
        *,
        initial_bar: str = "front",
    ) -> RotationCrossBarRouteSelectionResult:
        initial = str(initial_bar or "").strip().casefold()
        if initial not in {"front", "back"}:
            raise ValueError("rotation initial bar must be front or back")

        feasibility_by_key = {
            self._key(row.wait_time_seconds, row.source_bar, row.target_bar, row.filler_skill_name): row
            for row in feasibility
        }
        selected: list[RotationCrossBarRouteSelection] = []
        rejected: list[RotationCrossBarRouteRejection] = []
        reserved: set[float] = set()

        for proposal in sorted(
            proposals,
            key=lambda row: (
                float(row.wait_time_seconds),
                row.source_bar,
                row.target_bar,
                row.filler_skill_name.casefold(),
            ),
        ):
            key = self._key(
                proposal.wait_time_seconds,
                proposal.source_bar,
                proposal.target_bar,
                proposal.filler_skill_name,
            )
            local = feasibility_by_key.get(key)
            if local is None:
                rejected.append(
                    RotationCrossBarRouteRejection(
                        proposal=proposal,
                        reason="slot feasibility evidence is unavailable",
                    )
                )
                continue
            if not local.feasible:
                rejected.append(
                    RotationCrossBarRouteRejection(
                        proposal=proposal,
                        reason=local.reason,
                    )
                )
                continue

            route_times = tuple(
                float(proposal.wait_time_seconds) + float(offset)
                for offset in range(int(local.required_wait_slots))
            )
            overlap = tuple(
                value for value in route_times if self._contains_time(reserved, value)
            )
            if overlap:
                rejected.append(
                    RotationCrossBarRouteRejection(
                        proposal=proposal,
                        reason=(
                            "route overlaps WAIT slot(s) already reserved by an earlier selected route: "
                            + ", ".join(f"{value:g}s" for value in overlap)
                        ),
                    )
                )
                continue

            active_bar = self._active_bar_before(
                plan,
                time_seconds=float(proposal.wait_time_seconds),
                initial_bar=initial,
                selected=tuple(selected),
            )
            if active_bar == proposal.source_bar:
                outbound_swap_required = True
            elif active_bar == proposal.target_bar:
                outbound_swap_required = False
            else:
                rejected.append(
                    RotationCrossBarRouteRejection(
                        proposal=proposal,
                        reason=(
                            "route active-bar state is neither its reviewed source nor target: "
                            f"source={proposal.source_bar}, target={proposal.target_bar}, active={active_bar}"
                        ),
                    )
                )
                continue

            selected_row = RotationCrossBarRouteSelection(
                proposal=proposal,
                reserved_wait_times=route_times,
                outbound_swap_required=outbound_swap_required,
            )
            selected.append(selected_row)
            reserved.update(route_times)

        return RotationCrossBarRouteSelectionResult(
            selected=tuple(selected),
            rejected=tuple(rejected),
        )

    def _active_bar_before(
        self,
        plan: RotationPlan,
        *,
        time_seconds: float,
        initial_bar: str,
        selected: tuple[RotationCrossBarRouteSelection, ...],
    ) -> str:
        events: list[tuple[float, int, str]] = []
        for action in plan.actions:
            if action.kind is not RotationActionKind.BAR_SWAP:
                continue
            if float(action.time_seconds) >= float(time_seconds) - self._EPSILON:
                continue
            events.append((float(action.time_seconds), 0, str(action.bar)))

        for row in selected:
            proposal = row.proposal
            start = float(proposal.wait_time_seconds)
            if row.outbound_swap_required and start < float(time_seconds) - self._EPSILON:
                events.append((start, 1, proposal.target_bar))
            if proposal.return_swap_required:
                return_time = start + float(len(row.reserved_wait_times) - 1)
                if return_time < float(time_seconds) - self._EPSILON:
                    events.append((return_time, 2, proposal.source_bar))

        active = initial_bar
        for _time, _order, destination in sorted(events, key=lambda row: (row[0], row[1])):
            active = destination
        return active

    @staticmethod
    def _key(time_seconds: float, source_bar: str, target_bar: str, filler: str) -> tuple[object, ...]:
        return (
            round(float(time_seconds), 9),
            str(source_bar).strip().casefold(),
            str(target_bar).strip().casefold(),
            str(filler).strip().casefold(),
        )

    @classmethod
    def _contains_time(cls, values: set[float], target: float) -> bool:
        return any(abs(value - target) <= cls._EPSILON for value in values)


__all__ = [
    "RotationCrossBarRouteRejection",
    "RotationCrossBarRouteSelection",
    "RotationCrossBarRouteSelectionResult",
    "RotationCrossBarRouteSelectionService",
]
