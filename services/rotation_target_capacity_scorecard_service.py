from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationPlan
from minmax.rotation_target_capacity import (
    RotationTargetCapacityAssessment,
    RotationTargetCapacityAssessor,
    RotationTargetCapacityRequirement,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard


@dataclass(frozen=True)
class RotationTargetCapacityScorecard:
    """Transparent scorecard wrapper carrying explicit target-capacity legality.

    The wrapped scorecard remains authoritative for every existing obligation.
    Capacity is a known legality result, not unresolved mechanics evidence, so this
    wrapper adds one independent hard condition while delegating every other field
    and property to the underlying scorecard.
    """

    base_scorecard: RotationCandidateScorecard
    target_capacity_assessment: RotationTargetCapacityAssessment | None = None

    def __getattr__(self, name: str):
        return getattr(self.base_scorecard, name)

    @property
    def target_capacity_violations(self):
        if self.target_capacity_assessment is None:
            return ()
        return self.target_capacity_assessment.violations

    @property
    def supplied_obligations_satisfied(self) -> bool:
        return (
            bool(self.base_scorecard.supplied_obligations_satisfied)
            and not self.target_capacity_violations
        )


class RotationTargetCapacityScorecardService:
    """Attach explicit target-capacity legality to an existing candidate scorecard."""

    def __init__(
        self,
        assessor: RotationTargetCapacityAssessor | None = None,
    ) -> None:
        self.assessor = assessor or RotationTargetCapacityAssessor()

    def apply(
        self,
        scorecard: RotationCandidateScorecard,
        *,
        plan: RotationPlan,
        demands: tuple[RotationDemandWindow, ...],
        requirements: tuple[RotationTargetCapacityRequirement, ...],
    ) -> RotationTargetCapacityScorecard:
        assessment = (
            self.assessor.assess(plan, demands, requirements)
            if requirements
            else None
        )
        return RotationTargetCapacityScorecard(
            base_scorecard=scorecard,
            target_capacity_assessment=assessment,
        )


__all__ = [
    "RotationTargetCapacityScorecard",
    "RotationTargetCapacityScorecardService",
]
