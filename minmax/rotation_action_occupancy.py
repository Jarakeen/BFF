from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_plan import RotationActionKind, RotationPlan


_BLOCKING_KINDS = frozenset({
    RotationActionKind.SKILL,
    RotationActionKind.ULTIMATE,
})


@dataclass(frozen=True)
class RotationActionOccupancyRequirement:
    """Caller-supplied execution occupancy for one named skill or ultimate."""

    action_name: str
    occupancy_seconds: float
    action_kind: RotationActionKind = RotationActionKind.SKILL
    bar: str | None = None

    def __post_init__(self) -> None:
        name = str(self.action_name or "").strip()
        if not name:
            raise ValueError("rotation occupancy requirement needs action_name")
        object.__setattr__(self, "action_name", name)

        occupancy = float(self.occupancy_seconds)
        if not math.isfinite(occupancy) or occupancy < 0:
            raise ValueError("rotation occupancy must be finite and non-negative")
        object.__setattr__(self, "occupancy_seconds", occupancy)

        try:
            kind = (
                self.action_kind
                if isinstance(self.action_kind, RotationActionKind)
                else RotationActionKind(str(self.action_kind))
            )
        except ValueError as exc:
            raise ValueError(
                f"unsupported rotation occupancy action kind: {self.action_kind!r}"
            ) from exc
        if kind not in _BLOCKING_KINDS:
            raise ValueError("rotation occupancy requirements support skill or ultimate actions")
        object.__setattr__(self, "action_kind", kind)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation occupancy requirement bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationActionOccupancyViolation:
    requirement: RotationActionOccupancyRequirement
    occupying_time_seconds: float
    occupying_until_seconds: float
    blocked_time_seconds: float
    blocked_action_kind: RotationActionKind
    blocked_action_name: str | None
    blocked_action_bar: str | None


@dataclass(frozen=True)
class RotationActionOccupancyAssessment:
    violations: tuple[RotationActionOccupancyViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationActionOccupancyAssessor:
    """Audit skill/ultimate overlap from explicit canonical occupancy evidence.

    The caller supplies the already-resolved occupancy duration, typically from
    canonical cast-time or channel-time evidence. The assessor does not infer a
    global action cadence or animation lock. Only later skill/ultimate actions are
    treated as blocking in this first role-neutral contract.
    """

    def assess(
        self,
        plan: RotationPlan,
        requirements: tuple[RotationActionOccupancyRequirement, ...],
    ) -> RotationActionOccupancyAssessment:
        self._validate_unique(requirements)
        violations: list[RotationActionOccupancyViolation] = []

        for requirement in requirements:
            target = requirement.action_name.casefold()
            for index, action in enumerate(plan.actions):
                if action.kind is not requirement.action_kind:
                    continue
                if not action.name or str(action.name).casefold() != target:
                    continue
                if requirement.bar is not None and action.bar != requirement.bar:
                    continue
                if requirement.occupancy_seconds <= 0:
                    continue

                start = float(action.time_seconds)
                end = start + requirement.occupancy_seconds
                for blocked in plan.actions[index + 1 :]:
                    blocked_time = float(blocked.time_seconds)
                    if blocked_time + 1e-9 >= end:
                        break
                    if blocked.kind not in _BLOCKING_KINDS:
                        continue
                    violations.append(
                        RotationActionOccupancyViolation(
                            requirement=requirement,
                            occupying_time_seconds=start,
                            occupying_until_seconds=end,
                            blocked_time_seconds=blocked_time,
                            blocked_action_kind=blocked.kind,
                            blocked_action_name=blocked.name,
                            blocked_action_bar=blocked.bar,
                        )
                    )

        return RotationActionOccupancyAssessment(tuple(violations))

    @staticmethod
    def _validate_unique(
        requirements: tuple[RotationActionOccupancyRequirement, ...],
    ) -> None:
        seen: set[tuple[RotationActionKind, str, str | None]] = set()
        for requirement in requirements:
            key = (
                requirement.action_kind,
                requirement.action_name.casefold(),
                requirement.bar,
            )
            if key in seen:
                raise ValueError(
                    "duplicate rotation occupancy requirement for "
                    f"{requirement.action_name!r}"
                )
            seen.add(key)
