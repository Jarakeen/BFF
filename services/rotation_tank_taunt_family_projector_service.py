from __future__ import annotations

from pathlib import Path

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_candidate_service import (
    RotationTankTauntActionClaim,
    RotationTankTauntCandidateService,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
)


class RotationTankTauntFamilyProjectorService:
    """Adapt tank taunt application policy to the role-neutral family hook."""

    def __init__(
        self,
        *,
        requirements: tuple[RotationTankTauntApplicationRequirement, ...],
        claims: tuple[RotationTankTauntActionClaim, ...] = (),
        slot_requirements: tuple[RotationActionSlotRequirement, ...] = (),
        database_path: str | Path | None = None,
        candidate_service: RotationTankTauntCandidateService | None = None,
    ) -> None:
        self.requirements = tuple(requirements)
        self.claims = tuple(claims)
        self.slot_requirements = tuple(slot_requirements)
        if candidate_service is not None:
            self.candidate_service = candidate_service
        else:
            if database_path is None:
                raise ValueError(
                    "tank taunt family projector requires database_path or candidate_service"
                )
            self.candidate_service = RotationTankTauntCandidateService(database_path)

    def __call__(self, candidate: GeneratedRotationCandidate) -> GeneratedRotationCandidate:
        projection = self.candidate_service.project(
            candidate=candidate,
            requirements=self.requirements,
            claims=self.claims,
            slot_requirements=self.slot_requirements,
        )
        if projection.candidate is not None and not projection.unresolved:
            return projection.candidate

        reasons = tuple(
            dict.fromkeys(
                str(reason).strip()
                for reason in projection.unresolved
                if str(reason).strip()
            )
        ) or ("tank taunt family projection unresolved",)
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


__all__ = ["RotationTankTauntFamilyProjectorService"]
