from __future__ import annotations

import math
from dataclasses import dataclass

from .rotation_plan import RotationActionKind, RotationPlan


_BAR_BOUND_KINDS = frozenset({
    RotationActionKind.SKILL,
    RotationActionKind.ULTIMATE,
    RotationActionKind.LIGHT_ATTACK,
    RotationActionKind.HEAVY_ATTACK,
})


@dataclass(frozen=True)
class RotationActiveBarViolation:
    time_seconds: float
    action_name: str
    action_kind: RotationActionKind
    scheduled_bar: str | None
    active_bar: str
    reason: str


@dataclass(frozen=True)
class RotationActiveBarAssessment:
    initial_bar: str
    final_bar: str
    violations: tuple[RotationActiveBarViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationActiveBarAssessor:
    """Audit and query the plan's canonical BAR_SWAP progression.

    BAR_SWAP actions set the destination bar immediately in deterministic plan order.
    This layer does not decide whether a skill belongs on a bar or which weapon family
    is equipped there; saved-build slot and weapon projections own those separate
    questions. It verifies bar-labelled actions and also exposes the same ordered bar
    progression for runtime consumers that need the active bar at an exact instant.
    """

    def assess(
        self,
        plan: RotationPlan,
        *,
        initial_bar: str = "front",
    ) -> RotationActiveBarAssessment:
        active_bar = self._normalize_bar(initial_bar)
        initial = active_bar
        violations: list[RotationActiveBarViolation] = []

        for action in plan.actions:
            if action.kind is RotationActionKind.BAR_SWAP:
                # RotationAction already guarantees BAR_SWAP has a valid bar.
                active_bar = str(action.bar)
                continue

            if action.kind not in _BAR_BOUND_KINDS:
                continue

            if action.bar is None:
                violations.append(
                    RotationActiveBarViolation(
                        time_seconds=float(action.time_seconds),
                        action_name=str(action.name or action.kind.value),
                        action_kind=action.kind,
                        scheduled_bar=None,
                        active_bar=active_bar,
                        reason="bar-bound action does not declare its scheduled bar",
                    )
                )
                continue

            if action.bar != active_bar:
                violations.append(
                    RotationActiveBarViolation(
                        time_seconds=float(action.time_seconds),
                        action_name=str(action.name or action.kind.value),
                        action_kind=action.kind,
                        scheduled_bar=action.bar,
                        active_bar=active_bar,
                        reason="scheduled bar does not match the active bar",
                    )
                )

        return RotationActiveBarAssessment(
            initial_bar=initial,
            final_bar=active_bar,
            violations=tuple(violations),
        )

    def active_bar_at(
        self,
        plan: RotationPlan,
        *,
        time_seconds: float,
        sequence: int | None = None,
        initial_bar: str = "front",
    ) -> str:
        """Return the active bar at one deterministic point in plan order.

        When ``sequence`` is supplied, only actions at the requested timestamp whose
        sequence is less than or equal to that value have occurred. When it is omitted,
        the query represents the state after all actions scheduled at that timestamp.
        This distinction matters for same-timestamp LA/skill/swap ordering and lets
        runtime evidence use the exact same bar progression as legality checks.
        """

        instant = float(time_seconds)
        if not math.isfinite(instant) or instant < 0.0:
            raise ValueError("rotation active-bar lookup time must be finite and non-negative")
        boundary_sequence = None if sequence is None else int(sequence)
        if boundary_sequence is not None and boundary_sequence < 0:
            raise ValueError("rotation active-bar lookup sequence cannot be negative")

        active_bar = self._normalize_bar(initial_bar)
        epsilon = 1e-12
        for action in plan.actions:
            action_time = float(action.time_seconds)
            if action_time > instant + epsilon:
                break
            if (
                boundary_sequence is not None
                and abs(action_time - instant) <= epsilon
                and int(action.sequence) > boundary_sequence
            ):
                break
            if action.kind is RotationActionKind.BAR_SWAP:
                active_bar = str(action.bar)
        return active_bar

    @staticmethod
    def _normalize_bar(value: str) -> str:
        bar = str(value or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("rotation initial bar must be front or back")
        return bar


__all__ = [
    "RotationActiveBarAssessment",
    "RotationActiveBarAssessor",
    "RotationActiveBarViolation",
]
