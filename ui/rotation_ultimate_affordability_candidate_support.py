from __future__ import annotations

from dataclasses import replace

from minmax.rotation_ultimate_affordability import (
    RotationUltimateAffordabilityAssessor,
    RotationUltimateAffordabilityRequirement,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport


class RotationUltimateAffordabilityCandidateSupport:
    """Decorate final canonical candidate scorecards with Ultimate affordability.

    The wrapped canonical candidate path remains the owner of generation, recovery,
    legality, ranking, and selection. This adapter only replays explicit shared-pool
    Ultimate evidence against each final stabilized plan and attaches the resulting
    hard-obligation assessment to that candidate's scorecard.
    """

    def __init__(
        self,
        *,
        canonical_candidates=None,
        assessor: RotationUltimateAffordabilityAssessor | None = None,
    ) -> None:
        self.canonical_candidates = canonical_candidates or RotationCanonicalCandidateSupport()
        self.assessor = assessor or RotationUltimateAffordabilityAssessor()

    @property
    def static_context_service(self):
        return getattr(self.canonical_candidates, "static_context_service", None)

    def run_effects(
        self,
        *,
        ultimate_affordability_requirement: RotationUltimateAffordabilityRequirement | None = None,
        **kwargs,
    ):
        if ultimate_affordability_requirement is None:
            return self.canonical_candidates.run_effects(**kwargs)

        resolver = kwargs["scorecard_resolver"]

        def with_ultimate_affordability(snapshot):
            scorecard = resolver(snapshot)
            assessment = self.assessor.assess(
                snapshot.plan,
                ultimate_affordability_requirement,
            )
            return replace(
                scorecard,
                ultimate_affordability_assessment=assessment,
            )

        kwargs["scorecard_resolver"] = with_ultimate_affordability
        return self.canonical_candidates.run_effects(**kwargs)


__all__ = ["RotationUltimateAffordabilityCandidateSupport"]
