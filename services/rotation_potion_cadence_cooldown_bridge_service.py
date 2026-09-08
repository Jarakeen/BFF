from __future__ import annotations

from minmax.rotation_action_cooldown import (
    RotationActionCooldownAssessment,
    RotationActionCooldownRequirement,
    RotationActionCooldownViolation,
)
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.rotation_potion_cadence import (
    RotationPotionCadenceAssessor,
    RotationPotionCadenceRequirement,
)


class RotationPotionCadenceCooldownBridgeService:
    """Project shared potion-cadence violations into existing cooldown evidence.

    Candidate scorecards and ranking already treat cooldown violations as hard
    legality failures. This bridge lets potion cadence reuse that contract while
    keeping the low-level potion assessor's shared-across-names semantics.
    """

    def __init__(
        self,
        assessor: RotationPotionCadenceAssessor | None = None,
    ) -> None:
        self.assessor = assessor or RotationPotionCadenceAssessor()

    def assess(
        self,
        plan: RotationPlan,
        requirement: RotationPotionCadenceRequirement,
    ) -> RotationActionCooldownAssessment:
        cadence = self.assessor.assess(plan, requirement)
        violations = tuple(
            RotationActionCooldownViolation(
                requirement=RotationActionCooldownRequirement(
                    action_name=violation.action_name,
                    cooldown_seconds=violation.required_interval_seconds,
                    action_kind=RotationActionKind.POTION,
                ),
                previous_time_seconds=violation.previous_time_seconds,
                time_seconds=violation.time_seconds,
                actual_interval_seconds=violation.actual_interval_seconds,
                required_interval_seconds=violation.required_interval_seconds,
            )
            for violation in cadence.violations
        )
        return RotationActionCooldownAssessment(violations)


__all__ = ["RotationPotionCadenceCooldownBridgeService"]
