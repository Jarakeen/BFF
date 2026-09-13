from __future__ import annotations

from dataclasses import dataclass
import re

from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_cross_bar_route_selection_service import (
    RotationCrossBarRouteSelection,
    RotationCrossBarRouteSelectionResult,
)


_WAIT_TIME_PATTERN = re.compile(r"\bat\s+([0-9]+(?:\.[0-9]+)?)s\b", re.IGNORECASE)


@dataclass(frozen=True)
class RotationCrossBarRouteMutationResult:
    plan: RotationPlan
    applied: tuple[RotationCrossBarRouteSelection, ...]
    consumed_wait_times: tuple[float, ...]


class RotationCrossBarRouteMutationService:
    """Apply only already-selected cross-bar routes to a rotation plan.

    This layer owns no route discovery or priority inference. A selected route proves
    that one WAIT timestamp is available for the target-bar filler skill. ESO weapon
    swap is not a separate skill GCD, so the same timestamp may contain an outbound
    BAR_SWAP, the normal LA/skill weave, and, when required, a return BAR_SWAP after
    the skill. The resulting active-bar progression is validated canonically.
    """

    _EPSILON = 1e-9

    def __init__(
        self,
        *,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
    ) -> None:
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()

    def apply(
        self,
        plan: RotationPlan,
        selection: RotationCrossBarRouteSelectionResult,
        *,
        weave_light_attacks: bool = True,
        initial_bar: str = "front",
    ) -> RotationCrossBarRouteMutationResult:
        selected = tuple(selection.selected)
        if not selected:
            return RotationCrossBarRouteMutationResult(
                plan=plan,
                applied=(),
                consumed_wait_times=(),
            )

        reserved: dict[float, RotationCrossBarRouteSelection] = {}
        for row in selected:
            for value in row.reserved_wait_times:
                time_value = float(value)
                if self._find_time(reserved, time_value) is not None:
                    raise ValueError(
                        f"selected cross-bar routes overlap reserved WAIT time {time_value:g}s"
                    )
                reserved[time_value] = row

        wait_times = {
            float(action.time_seconds)
            for action in plan.actions
            if action.kind is RotationActionKind.WAIT
        }
        missing = [
            value
            for value in sorted(reserved)
            if not self._contains_time(wait_times, value)
        ]
        if missing:
            raise ValueError(
                "selected cross-bar route no longer maps to WAIT slot(s): "
                + ", ".join(f"{value:g}s" for value in missing)
            )

        consumed = tuple(sorted(reserved))
        actions = [
            action
            for action in plan.actions
            if not (
                action.kind is RotationActionKind.WAIT
                and self._contains_time(set(consumed), float(action.time_seconds))
            )
        ]

        for row in selected:
            proposal = row.proposal
            times = tuple(float(value) for value in row.reserved_wait_times)
            if len(times) != 1:
                raise ValueError(
                    "selected cross-bar route must reserve exactly one WAIT skill slot"
                )

            route_time = times[0]
            actions.append(
                RotationAction(
                    time_seconds=route_time,
                    sequence=0,
                    kind=RotationActionKind.BAR_SWAP,
                    bar=proposal.target_bar,
                )
            )

            if weave_light_attacks:
                actions.append(
                    RotationAction(
                        time_seconds=route_time,
                        sequence=1,
                        kind=RotationActionKind.LIGHT_ATTACK,
                        bar=proposal.target_bar,
                    )
                )
                skill_sequence = 2
            else:
                skill_sequence = 1
            actions.append(
                RotationAction(
                    time_seconds=route_time,
                    sequence=skill_sequence,
                    kind=RotationActionKind.SKILL,
                    name=proposal.filler_skill_name,
                    bar=proposal.target_bar,
                )
            )

            if proposal.return_swap_required:
                actions.append(
                    RotationAction(
                        time_seconds=route_time,
                        sequence=skill_sequence + 1,
                        kind=RotationActionKind.BAR_SWAP,
                        bar=proposal.source_bar,
                    )
                )

        actions.sort(key=lambda action: (float(action.time_seconds), int(action.sequence)))
        assumptions = list(plan.assumptions)
        for row in selected:
            proposal = row.proposal
            route_time = float(row.reserved_wait_times[0])
            label = (
                f"selected cross-bar route at {route_time:g}s uses non-GCD "
                f"{proposal.source_bar}->{proposal.target_bar} swap and "
                f"'{proposal.filler_skill_name}' in the same skill-GCD slot"
            )
            if proposal.return_swap_required:
                label += f" then returns to {proposal.source_bar} after the skill"
            assumptions.append(label)

        unresolved = tuple(
            message
            for message in plan.unresolved
            if not self._is_consumed_wait_diagnostic(message, set(consumed))
        )
        mutated = RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=tuple(actions),
            assumptions=tuple(self._dedupe(assumptions)),
            unresolved=unresolved,
        )

        assessment = self.active_bar_assessor.assess(mutated, initial_bar=initial_bar)
        if not assessment.legal:
            details = "; ".join(
                f"{row.time_seconds:g}s {row.action_kind.value} {row.action_name}: {row.reason}"
                for row in assessment.violations
            )
            raise ValueError("cross-bar route mutation produced illegal active-bar plan: " + details)

        return RotationCrossBarRouteMutationResult(
            plan=mutated,
            applied=selected,
            consumed_wait_times=consumed,
        )

    @classmethod
    def _is_consumed_wait_diagnostic(cls, message: str, consumed: set[float]) -> bool:
        text = str(message or "")
        if "scheduled wait instead" not in text.casefold():
            return False
        match = _WAIT_TIME_PATTERN.search(text)
        if match is None:
            return False
        try:
            value = float(match.group(1))
        except ValueError:
            return False
        return cls._contains_time(consumed, value)

    @classmethod
    def _contains_time(cls, values: set[float], target: float) -> bool:
        return any(abs(float(value) - float(target)) <= cls._EPSILON for value in values)

    @classmethod
    def _find_time(cls, values: dict[float, object], target: float) -> float | None:
        return next(
            (value for value in values if abs(float(value) - float(target)) <= cls._EPSILON),
            None,
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result


__all__ = [
    "RotationCrossBarRouteMutationResult",
    "RotationCrossBarRouteMutationService",
]
