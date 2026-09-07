from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_bar_availability import (
    RotationBarAvailabilityAssessor,
    RotationBarAvailabilityWindow,
)
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationDemandBarAccessClaim:
    """Explicit mechanic permission to route to one bar for one required skill cast.

    This is intentionally narrower than general bar-swap optimization. The claim
    may only act inside one named demand window and only when the required skill is
    not already scheduled there on the requested bar.
    """

    demand_name: str
    bar: str
    skill_name: str

    def __post_init__(self) -> None:
        demand = str(self.demand_name or "").strip()
        if not demand:
            raise ValueError("demand bar-access claim requires demand_name")
        object.__setattr__(self, "demand_name", demand)

        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("demand bar-access claim bar must be front or back")
        object.__setattr__(self, "bar", bar)

        skill = str(self.skill_name or "").strip()
        if not skill:
            raise ValueError("demand bar-access claim requires skill_name")
        object.__setattr__(self, "skill_name", skill)


@dataclass(frozen=True)
class RotationDemandBarAccessResult:
    plan: RotationPlan
    applied: bool
    reason: str
    displaced_actions: tuple[RotationAction, ...] = ()


class RotationDemandBarAccessService:
    """Route briefly to a required bar inside a demand, then restore displaced work.

    The service consumes three existing decision slots inside the demand:
    swap to target bar, cast required skill, swap back. Any displaced ordinary
    skills are restored only into later WAIT slots on the original bar before the
    next hard bar-swap boundary. If the plan cannot preserve that work exactly, no
    rewrite is performed.

    Caller-supplied bar-availability windows are hard encounter legality. A rescue
    that would violate one of those windows is refused rather than treated as a
    viable candidate.

    This deliberately avoids inventing swap duration, extra action slots, cross-bar
    skill legality, or hidden priority. It is an explicit encounter rescue policy
    whose downstream resource and consequence costs remain visible to the scorecard.
    """

    def __init__(self, *, bar_assessor: RotationBarAvailabilityAssessor | None = None) -> None:
        self.bar_assessor = bar_assessor or RotationBarAvailabilityAssessor()

    def refine(
        self,
        *,
        plan: RotationPlan,
        demands: tuple[RotationDemandWindow, ...],
        claim: RotationDemandBarAccessClaim,
        bar_availability_windows: tuple[RotationBarAvailabilityWindow, ...] = (),
    ) -> RotationDemandBarAccessResult:
        demand = self._resolve_demand(demands, claim.demand_name)
        if self._already_satisfied(plan, demand, claim):
            return RotationDemandBarAccessResult(
                plan=plan,
                applied=False,
                reason="required skill is already scheduled on the requested bar inside the demand",
            )

        actions = list(plan.actions)
        active_by_index = self._active_bar_by_index(actions)
        decision_indices = [
            index
            for index, action in enumerate(actions)
            if demand.start_seconds <= float(action.time_seconds) < demand.end_seconds
            and action.kind in {RotationActionKind.SKILL, RotationActionKind.WAIT}
        ]
        blocked_by_bar_state = False

        for offset in range(max(0, len(decision_indices) - 2)):
            window = decision_indices[offset : offset + 3]
            if len(window) < 3:
                break
            first_index, cast_index, return_index = window
            first = actions[first_index]
            cast_slot = actions[cast_index]
            return_slot = actions[return_index]

            original_bar = active_by_index[first_index]
            if original_bar not in {"front", "back"} or original_bar == claim.bar:
                continue
            if active_by_index[cast_index] != original_bar or active_by_index[return_index] != original_bar:
                continue
            if any(
                actions[index].kind not in {RotationActionKind.SKILL, RotationActionKind.WAIT}
                for index in window
            ):
                continue

            displaced = tuple(
                action
                for action in (first, cast_slot, return_slot)
                if action.kind is RotationActionKind.SKILL
            )
            restore_indices = self._restore_wait_indices(
                actions,
                start_index=return_index + 1,
                original_bar=original_bar,
                active_by_index=active_by_index,
                count=len(displaced),
            )
            if len(restore_indices) != len(displaced):
                continue

            rewritten = list(actions)
            rewritten[first_index] = RotationAction(
                time_seconds=first.time_seconds,
                sequence=first.sequence,
                kind=RotationActionKind.BAR_SWAP,
                bar=claim.bar,
            )
            rewritten[cast_index] = RotationAction(
                time_seconds=cast_slot.time_seconds,
                sequence=cast_slot.sequence,
                kind=RotationActionKind.SKILL,
                name=claim.skill_name,
                bar=claim.bar,
            )
            rewritten[return_index] = RotationAction(
                time_seconds=return_slot.time_seconds,
                sequence=return_slot.sequence,
                kind=RotationActionKind.BAR_SWAP,
                bar=original_bar,
            )

            for restore_index, displaced_action in zip(restore_indices, displaced):
                slot = rewritten[restore_index]
                rewritten[restore_index] = RotationAction(
                    time_seconds=slot.time_seconds,
                    sequence=slot.sequence,
                    kind=RotationActionKind.SKILL,
                    name=displaced_action.name,
                    bar=original_bar,
                )

            assumption = (
                f"explicit demand bar-access claim routed to {claim.bar} bar for {claim.skill_name!r} "
                f"inside {demand.name!r} and restored displaced {original_bar}-bar skills into later waits"
            )
            refined = RotationPlan(
                character_name=plan.character_name,
                build_name=plan.build_name,
                duration_seconds=plan.duration_seconds,
                actions=tuple(rewritten),
                assumptions=self._append_once(plan.assumptions, assumption),
                unresolved=plan.unresolved,
            )
            if bar_availability_windows:
                assessment = self.bar_assessor.assess(refined, bar_availability_windows)
                if not assessment.legal:
                    blocked_by_bar_state = True
                    continue

            return RotationDemandBarAccessResult(
                plan=refined,
                applied=True,
                reason="temporary bar route created and displaced same-bar skills were preserved",
                displaced_actions=displaced,
            )

        if blocked_by_bar_state:
            return RotationDemandBarAccessResult(
                plan=plan,
                applied=False,
                reason="candidate bar route violates caller-supplied encounter bar availability",
            )

        return RotationDemandBarAccessResult(
            plan=plan,
            applied=False,
            reason=(
                "no three-slot demand route could preserve displaced original-bar skills before the next hard bar boundary"
            ),
        )

    @staticmethod
    def _resolve_demand(
        demands: tuple[RotationDemandWindow, ...],
        demand_name: str,
    ) -> RotationDemandWindow:
        matches = tuple(demand for demand in demands if demand.name == demand_name)
        if len(matches) != 1:
            raise ValueError(
                f"demand bar-access claim requires exactly one demand named {demand_name!r}; found {len(matches)}"
            )
        return matches[0]

    @staticmethod
    def _already_satisfied(
        plan: RotationPlan,
        demand: RotationDemandWindow,
        claim: RotationDemandBarAccessClaim,
    ) -> bool:
        return any(
            action.kind is RotationActionKind.SKILL
            and action.bar == claim.bar
            and str(action.name or "").casefold() == claim.skill_name.casefold()
            and demand.start_seconds <= float(action.time_seconds) < demand.end_seconds
            for action in plan.actions
        )

    @staticmethod
    def _active_bar_by_index(actions: list[RotationAction]) -> list[str | None]:
        current: str | None = None
        result: list[str | None] = []
        for action in actions:
            if action.kind is RotationActionKind.BAR_SWAP:
                current = action.bar
            elif action.bar in {"front", "back"} and current is None:
                current = action.bar
            result.append(current)
        return result

    @staticmethod
    def _restore_wait_indices(
        actions: list[RotationAction],
        *,
        start_index: int,
        original_bar: str,
        active_by_index: list[str | None],
        count: int,
    ) -> tuple[int, ...]:
        if count == 0:
            return ()
        result: list[int] = []
        for index in range(start_index, len(actions)):
            action = actions[index]
            if action.kind is RotationActionKind.BAR_SWAP:
                break
            if active_by_index[index] != original_bar:
                continue
            if action.kind is RotationActionKind.WAIT:
                result.append(index)
                if len(result) == count:
                    break
        return tuple(result)

    @staticmethod
    def _append_once(values: tuple[str, ...], value: str) -> tuple[str, ...]:
        if value in values:
            return values
        return tuple(values) + (value,)
