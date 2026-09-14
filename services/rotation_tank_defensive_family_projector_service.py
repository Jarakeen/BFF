from __future__ import annotations

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_defensive_candidate_service import (
    RotationTankDefensiveActionClaim,
    RotationTankDefensiveCandidateService,
)
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)


class RotationTankDefensiveFamilyProjectorService:
    """Adapt shared tank defensive policy to the role-neutral family projector hook.

    Resolved candidates preserve/insert exact reviewed defensive responses through
    ``RotationTankDefensiveCandidateService``. Candidate-specific projection failures
    remain in that candidate plan's unresolved channel so downstream scorecard logic
    can reject the candidate without aborting its otherwise-comparable siblings.
    """

    def __init__(
        self,
        *,
        obligations: tuple[RotationTankDefensiveObligation, ...],
        claims: tuple[RotationTankDefensiveActionClaim, ...] = (),
        candidate_service: RotationTankDefensiveCandidateService | None = None,
    ) -> None:
        self.obligations = tuple(obligations)
        self.claims = tuple(claims)
        self.candidate_service = candidate_service or RotationTankDefensiveCandidateService()

    def __call__(self, candidate: GeneratedRotationCandidate) -> GeneratedRotationCandidate:
        projection = self.candidate_service.project(
            candidate=candidate,
            obligations=self.obligations,
            claims=self.claims,
        )
        if projection.candidate is not None and not projection.unresolved:
            return projection.candidate

        reasons = tuple(
            dict.fromkeys(
                str(reason).strip()
                for reason in projection.unresolved
                if str(reason).strip()
            )
        ) or ("tank defensive family projection unresolved",)
        plan = RotationPlan(
            character_name=candidate.plan.character_name,
            build_name=candidate.plan.build_name,
            duration_seconds=candidate.plan.duration_seconds,
            actions=candidate.plan.actions,
            assumptions=candidate.plan.assumptions,
            unresolved=tuple(candidate.plan.unresolved) + reasons,
        )
        return GeneratedRotationCandidate(
            candidate_id=candidate.candidate_id,
            plan=plan,
            refresh_leads=candidate.refresh_leads,
            action_claims=candidate.action_claims,
        )


__all__ = ["RotationTankDefensiveFamilyProjectorService"]
