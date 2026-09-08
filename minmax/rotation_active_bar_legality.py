from __future__ import annotations

from dataclasses import dataclass

from .rotation_plan import RotationActionKind, RotationPlan


_BAR_BOUND_KINDS = frozenset({
    RotationActionKind.SKILL,
    RotationActionKind.ULTIMATE,
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
    """Audit skill/ultimate actions against the plan's own BAR_SWAP progression.

    BAR_SWAP actions set the destination bar immediately in deterministic plan order.
    This layer does not decide whether a skill belongs on a bar; saved-build slot
    legality owns that separate question. It only verifies that a bar-labelled cast
    matches the bar that is actually active at that instant.
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
