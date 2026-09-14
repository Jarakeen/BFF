from __future__ import annotations

from pathlib import Path

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_maintenance_candidate_service import (
    RotationTankTauntMaintenanceCandidateService,
    RotationTankTauntMaintenanceRefreshPolicy,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
)


class RotationTankTauntMaintenanceFamilyProjectorService:
    """Adapt target-specific taunt maintenance to the role-neutral family hook.

    Projection remains candidate-local. A sibling whose explicit refresh policy cannot
    be realized keeps its original schedule and receives unresolved evidence on that
    plan; otherwise-valid siblings continue through the recommendation family.
    """

    def __init__(
        self,
        *,
        requirements: tuple[RotationTankTauntMaintenanceRequirement, ...],
        policies: tuple[RotationTankTauntMaintenanceRefreshPolicy, ...] = (),
        slot_requirements: tuple[RotationActionSlotRequirement, ...] = (),
        database_path: str | Path | None = None,
        candidate_service: RotationTankTauntMaintenanceCandidateService | None = None,
    ) -> None:
        self.requirements = tuple(requirements)
        self.policies = tuple(policies)
        self.slot_requirements = tuple(slot_requirements)
        if candidate_service is not None:
            self.candidate_service = candidate_service
        else:
            if database_path is None:
                raise ValueError(
                    "tank taunt maintenance family projector requires database_path or candidate_service"
                )
            self.candidate_service = RotationTankTauntMaintenanceCandidateService(
                database_path
            )

    def __call__(self, candidate: GeneratedRotationCandidate) -> GeneratedRotationCandidate:
        projection = self.candidate_service.project(
            candidate=candidate,
            requirements=self.requirements,
            policies=self.policies,
            slot_requirements=self.slot_requirements,
        )
        if projection.candidate is not None and not projection.unresolved:
            if projection.candidate.candidate_id != candidate.candidate_id:
                raise ValueError(
                    "tank taunt maintenance family projection must preserve candidate identity"
                )
            return projection.candidate

        reasons = tuple(
            dict.fromkeys(
                str(reason).strip()
                for reason in projection.unresolved
                if str(reason).strip()
            )
        ) or ("tank taunt maintenance family projection unresolved",)
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


__all__ = ["RotationTankTauntMaintenanceFamilyProjectorService"]
