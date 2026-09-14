from __future__ import annotations

"""Compose assignment-backed Tank hard obligations for one encounter/build.

This service is orchestration only. Provider ownership remains authoritative in
``ProviderAssignment``; taunt application and maintenance semantics remain owned by
their existing assignment projection services; defensive obligations remain explicit
reviewed inputs. The result is a role-neutral service-layer bundle suitable for an
application adapter to pass into Rotation Builder Generate.
"""

from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild
from services.encounter_provider_assignment import ProviderAssignment
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
    RotationAssignmentTauntMaintenanceService,
)
from services.rotation_assignment_taunt_obligation_service import (
    RotationAssignmentTauntObligationService,
    RotationAssignmentTauntPolicy,
)
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
)


@dataclass(frozen=True)
class RotationTankAssignmentObligationBundle:
    encounter_id: str
    member_id: str
    taunt_application_requirements: tuple[
        RotationTankTauntApplicationRequirement, ...
    ] = ()
    taunt_maintenance_requirements: tuple[
        RotationTankTauntMaintenanceRequirement, ...
    ] = ()
    defensive_obligations: tuple[RotationTankDefensiveObligation, ...] = ()

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        member_id = str(self.member_id or "").strip()
        if not encounter_id:
            raise ValueError("Tank assignment obligation bundle requires encounter_id")
        if not member_id:
            raise ValueError("Tank assignment obligation bundle requires member_id")
        object.__setattr__(self, "encounter_id", encounter_id)
        object.__setattr__(self, "member_id", member_id)
        object.__setattr__(
            self,
            "taunt_application_requirements",
            tuple(self.taunt_application_requirements),
        )
        object.__setattr__(
            self,
            "taunt_maintenance_requirements",
            tuple(self.taunt_maintenance_requirements),
        )
        object.__setattr__(
            self,
            "defensive_obligations",
            tuple(self.defensive_obligations),
        )

    @property
    def has_obligations(self) -> bool:
        return bool(
            self.taunt_application_requirements
            or self.taunt_maintenance_requirements
            or self.defensive_obligations
        )


class RotationTankAssignmentObligationBundleService:
    """Join exact provider ownership to all currently modeled Tank hard obligations."""

    def __init__(
        self,
        *,
        taunt_application_service: RotationAssignmentTauntObligationService | None = None,
        taunt_maintenance_service: RotationAssignmentTauntMaintenanceService | None = None,
    ) -> None:
        self.taunt_application_service = (
            taunt_application_service or RotationAssignmentTauntObligationService()
        )
        self.taunt_maintenance_service = (
            taunt_maintenance_service or RotationAssignmentTauntMaintenanceService()
        )

    def compose(
        self,
        *,
        build: CharacterBuild,
        member_id: str,
        encounter_id: str,
        assignments: tuple[ProviderAssignment, ...],
        taunt_policies: tuple[RotationAssignmentTauntPolicy, ...] = (),
        taunt_maintenance_policies: tuple[
            RotationAssignmentTauntMaintenancePolicy, ...
        ] = (),
        defensive_obligations: tuple[RotationTankDefensiveObligation, ...] = (),
    ) -> RotationTankAssignmentObligationBundle:
        resolved_encounter = str(encounter_id or "").strip()
        resolved_member = str(member_id or "").strip()
        if not resolved_encounter:
            raise ValueError("Tank assignment obligation composition requires encounter_id")
        if not resolved_member:
            raise ValueError("Tank assignment obligation composition requires member_id")

        encounter_assignments = tuple(
            assignment
            for assignment in assignments
            if str(assignment.encounter_id or "").strip().casefold()
            == resolved_encounter.casefold()
        )
        foreign_taunt = tuple(
            policy.requirement_id
            for policy in taunt_policies
            if policy.encounter_id.casefold() != resolved_encounter.casefold()
        )
        foreign_maintenance = tuple(
            policy.requirement_id
            for policy in taunt_maintenance_policies
            if policy.encounter_id.casefold() != resolved_encounter.casefold()
        )
        if foreign_taunt or foreign_maintenance:
            labels = foreign_taunt + foreign_maintenance
            raise ValueError(
                "Tank assignment obligation policy encounter does not match selected encounter: "
                + ", ".join(labels)
            )

        taunt_projection = self.taunt_application_service.derive(
            build=build,
            member_id=resolved_member,
            assignments=encounter_assignments,
            policies=tuple(taunt_policies),
        )
        maintenance_projection = self.taunt_maintenance_service.derive(
            build=build,
            member_id=resolved_member,
            assignments=encounter_assignments,
            policies=tuple(taunt_maintenance_policies),
        )

        return RotationTankAssignmentObligationBundle(
            encounter_id=resolved_encounter,
            member_id=resolved_member,
            taunt_application_requirements=taunt_projection.requirements,
            taunt_maintenance_requirements=maintenance_projection.requirements,
            defensive_obligations=tuple(defensive_obligations),
        )


__all__ = [
    "RotationTankAssignmentObligationBundle",
    "RotationTankAssignmentObligationBundleService",
]
