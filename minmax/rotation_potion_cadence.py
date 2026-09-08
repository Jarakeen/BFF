from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_plan import RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationPotionCadenceRequirement:
    """Explicit effective shared potion cooldown for one rotation plan.

    The caller owns resolution of the effective cooldown, including any verified
    cooldown-reduction mechanics. This layer deliberately does not assume the base
    45-second potion cooldown is universally applicable to every saved build.
    """

    cooldown_seconds: float

    def __post_init__(self) -> None:
        cooldown = float(self.cooldown_seconds)
        if not math.isfinite(cooldown) or cooldown <= 0:
            raise ValueError("rotation potion cadence cooldown must be finite and positive")
        object.__setattr__(self, "cooldown_seconds", cooldown)


@dataclass(frozen=True)
class RotationPotionCadenceViolation:
    previous_name: str
    previous_time_seconds: float
    action_name: str
    time_seconds: float
    actual_interval_seconds: float
    required_interval_seconds: float


@dataclass(frozen=True)
class RotationPotionCadenceAssessment:
    requirement: RotationPotionCadenceRequirement
    violations: tuple[RotationPotionCadenceViolation, ...]

    @property
    def legal(self) -> bool:
        return not self.violations


class RotationPotionCadenceAssessor:
    """Audit all potion actions against one shared effective cooldown timeline.

    Potion identity does not create independent cooldown histories. Consecutive
    potion actions therefore share one cadence even when their names differ.
    Exact cooldown boundaries are legal.
    """

    def assess(
        self,
        plan: RotationPlan,
        requirement: RotationPotionCadenceRequirement,
    ) -> RotationPotionCadenceAssessment:
        previous_name: str | None = None
        previous_time: float | None = None
        violations: list[RotationPotionCadenceViolation] = []

        for action in plan.actions:
            if action.kind is not RotationActionKind.POTION:
                continue
            current_time = float(action.time_seconds)
            current_name = str(action.name or "potion")
            if previous_time is not None and previous_name is not None:
                interval = current_time - previous_time
                if interval + 1e-9 < requirement.cooldown_seconds:
                    violations.append(
                        RotationPotionCadenceViolation(
                            previous_name=previous_name,
                            previous_time_seconds=previous_time,
                            action_name=current_name,
                            time_seconds=current_time,
                            actual_interval_seconds=interval,
                            required_interval_seconds=requirement.cooldown_seconds,
                        )
                    )
            previous_name = current_name
            previous_time = current_time

        return RotationPotionCadenceAssessment(
            requirement=requirement,
            violations=tuple(violations),
        )


__all__ = [
    "RotationPotionCadenceRequirement",
    "RotationPotionCadenceViolation",
    "RotationPotionCadenceAssessment",
    "RotationPotionCadenceAssessor",
]
