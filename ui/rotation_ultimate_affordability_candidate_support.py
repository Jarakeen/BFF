from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from minmax.rotation_plan import RotationPlan
from minmax.rotation_ultimate_affordability import (
    RotationUltimateAffordabilityAssessor,
    RotationUltimateAffordabilityRequirement,
)
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport


UltimateGenerationEventResolver = Callable[
    [RotationPlan],
    tuple[UltimateGenerationEvent, ...],
]


class RotationUltimateAffordabilityCandidateSupport:
    """Decorate final canonical candidate scorecards with Ultimate affordability.

    The wrapped canonical candidate path remains the owner of generation, recovery,
    legality, ranking, and selection. This adapter replays explicit shared-pool
    Ultimate evidence against each final stabilized plan and attaches the resulting
    hard-obligation assessment to that candidate's scorecard.

    Candidate-dependent Ultimate generation may be supplied through
    ``ultimate_generation_event_resolver``. The resolver receives the stabilized
    candidate plan, so evidence derived from scheduled attacks is recomputed from
    the plan being judged rather than copied from the seed schedule.
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
        ultimate_generation_event_resolver: UltimateGenerationEventResolver | None = None,
        **kwargs,
    ):
        if ultimate_affordability_requirement is None:
            return self.canonical_candidates.run_effects(**kwargs)

        resolver = kwargs["scorecard_resolver"]

        def with_ultimate_affordability(snapshot):
            scorecard = resolver(snapshot)
            requirement = ultimate_affordability_requirement
            if ultimate_generation_event_resolver is not None:
                dynamic_events = tuple(
                    ultimate_generation_event_resolver(snapshot.plan)
                )
                requirement = replace(
                    requirement,
                    generation_events=(
                        tuple(requirement.generation_events) + dynamic_events
                    ),
                )
            assessment = self.assessor.assess(
                snapshot.plan,
                requirement,
            )
            return replace(
                scorecard,
                ultimate_affordability_assessment=assessment,
            )

        kwargs["scorecard_resolver"] = with_ultimate_affordability
        return self.canonical_candidates.run_effects(**kwargs)


__all__ = [
    "RotationUltimateAffordabilityCandidateSupport",
    "UltimateGenerationEventResolver",
]
