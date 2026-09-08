from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_plan import RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationActionCooldownRequirement:
    """Caller-supplied cooldown evidence for one named scheduled action."""

    action_name: str
    cooldown_seconds: float
    action_kind: RotationActionKind = RotationActionKind.SKILL
    bar: str | None = None

    def __post_init__(self) -> None:
        name = str(self.action_name or "").strip()
        if not name:
            raise ValueError("rotation cooldown requirement needs action_name")
        object.__setattr__(self, "action_name", name)

        cooldown = float(self.cooldown_seconds)
        if not math.isfinite(cooldown) or cooldown < 0:
            raise ValueError("rotation cooldown must be finite and non-negative")
        object.__setattr__(self, "cooldown_seconds", cooldown)

        try:
            kind = (
                self.action_kind
                if isinstance(self.action_kind, RotationActionKind)
                else RotationActionKind(str(self.action_kind))
            )
        except ValueError as exc:
            raise ValueError(f"unsupported rotation cooldown action kind: {self.action_kind!r}") from exc
        if kind not in {
            RotationActionKind.SKILL,
            RotationActionKind.ULTIMATE,
            RotationActionKind.POTION,
        }:
            raise ValueError("rotation cooldown requirements support skill, ultimate, or potion actions")
        object.__setattr__(self, "action_kind", kind)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation cooldown requirement bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationActionCooldownViolation:
    requirement: RotationActionCooldownRequirement
    previous_time_seconds: float
    time_seconds: float
    actual_interval_seconds: float
    required_interval_seconds: float


@dataclass(frozen=True)
class RotationActionCooldownAssessment:
    violations: tuple[RotationActionCooldownViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationActionCooldownAssessor:
    """Audit a plan against explicit canonical cooldown evidence.

    This layer does not infer cooldowns from action names or role. Callers must
    provide the already-resolved cooldown duration. Matching actions share one
    cooldown history when the requirement has no bar scope; a bar-scoped
    requirement tracks only matching actions on that bar.
    """

    def assess(
        self,
        plan: RotationPlan,
        requirements: tuple[RotationActionCooldownRequirement, ...],
    ) -> RotationActionCooldownAssessment:
        self._validate_unique(requirements)
        violations: list[RotationActionCooldownViolation] = []

        for requirement in requirements:
            previous_time: float | None = None
            target = requirement.action_name.casefold()
            for action in plan.actions:
                if action.kind is not requirement.action_kind:
                    continue
                if not action.name or str(action.name).casefold() != target:
                    continue
                if requirement.bar is not None and action.bar != requirement.bar:
                    continue

                current_time = float(action.time_seconds)
                if previous_time is not None:
                    interval = current_time - previous_time
                    if interval + 1e-9 < requirement.cooldown_seconds:
                        violations.append(
                            RotationActionCooldownViolation(
                                requirement=requirement,
                                previous_time_seconds=previous_time,
                                time_seconds=current_time,
                                actual_interval_seconds=interval,
                                required_interval_seconds=requirement.cooldown_seconds,
                            )
                        )
                previous_time = current_time

        return RotationActionCooldownAssessment(tuple(violations))

    @staticmethod
    def _validate_unique(
        requirements: tuple[RotationActionCooldownRequirement, ...],
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
                    "duplicate rotation cooldown requirement for "
                    f"{requirement.action_name!r}"
                )
            seen.add(key)
