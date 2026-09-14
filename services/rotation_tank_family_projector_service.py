from __future__ import annotations

"""Compose explicit Tank candidate projection without inventing strategy.

Tank obligation evidence and Tank strategy remain separate truths. This composer only
activates a projection lane when the caller supplied the exact strategy evidence for
that lane: discrete taunt action claims, continuous-taunt refresh policy, or defensive
action claims. Missing strategy never causes this service to choose a timestamp,
refresh lead, bar, target, or replacement action.
"""

from pathlib import Path

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_defensive_candidate_service import RotationTankDefensiveActionClaim
from services.rotation_tank_defensive_family_projector_service import (
    RotationTankDefensiveFamilyProjectorService,
)
from services.rotation_tank_defensive_obligation_service import RotationTankDefensiveObligation
from services.rotation_tank_taunt_candidate_service import RotationTankTauntActionClaim
from services.rotation_tank_taunt_family_projector_service import (
    RotationTankTauntFamilyProjectorService,
)
from services.rotation_tank_taunt_maintenance_candidate_service import (
    RotationTankTauntMaintenanceRefreshPolicy,
)
from services.rotation_tank_taunt_maintenance_family_projector_service import (
    RotationTankTauntMaintenanceFamilyProjectorService,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
)


class RotationTankFamilyProjectorService:
    """Apply only caller-authorized Tank strategy to one generated candidate."""

    def __init__(
        self,
        *,
        database_path: str | Path,
        taunt_application_requirements: tuple[RotationTankTauntApplicationRequirement, ...] = (),
        taunt_application_claims: tuple[RotationTankTauntActionClaim, ...] = (),
        taunt_maintenance_requirements: tuple[RotationTankTauntMaintenanceRequirement, ...] = (),
        taunt_maintenance_policies: tuple[RotationTankTauntMaintenanceRefreshPolicy, ...] = (),
        defensive_obligations: tuple[RotationTankDefensiveObligation, ...] = (),
        defensive_claims: tuple[RotationTankDefensiveActionClaim, ...] = (),
        slot_requirements: tuple[RotationActionSlotRequirement, ...] = (),
        taunt_projector: object | None = None,
        maintenance_projector: object | None = None,
        defensive_projector: object | None = None,
    ) -> None:
        self.projectors: list[object] = []

        if taunt_application_claims:
            if not taunt_application_requirements:
                raise ValueError("Tank taunt action claims require taunt application requirements")
            self.projectors.append(
                taunt_projector
                or RotationTankTauntFamilyProjectorService(
                    requirements=tuple(taunt_application_requirements),
                    claims=tuple(taunt_application_claims),
                    slot_requirements=tuple(slot_requirements),
                    database_path=database_path,
                )
            )

        if taunt_maintenance_policies:
            if not taunt_maintenance_requirements:
                raise ValueError("Tank taunt maintenance policy requires maintenance requirements")
            self.projectors.append(
                maintenance_projector
                or RotationTankTauntMaintenanceFamilyProjectorService(
                    requirements=tuple(taunt_maintenance_requirements),
                    policies=tuple(taunt_maintenance_policies),
                    slot_requirements=tuple(slot_requirements),
                    database_path=database_path,
                )
            )

        if defensive_claims:
            if not defensive_obligations:
                raise ValueError("Tank defensive claims require defensive obligations")
            self.projectors.append(
                defensive_projector
                or RotationTankDefensiveFamilyProjectorService(
                    obligations=tuple(defensive_obligations),
                    claims=tuple(defensive_claims),
                )
            )

    @property
    def active(self) -> bool:
        return bool(self.projectors)

    def __call__(self, candidate: GeneratedRotationCandidate) -> GeneratedRotationCandidate:
        current = candidate
        for projector in self.projectors:
            projected = projector(current)
            if not isinstance(projected, GeneratedRotationCandidate):
                raise TypeError("Tank family projector stage must return GeneratedRotationCandidate")
            if projected.candidate_id.casefold() != current.candidate_id.casefold():
                raise ValueError(
                    "Tank family projector stage must preserve candidate identity: "
                    f"expected {current.candidate_id!r}, got {projected.candidate_id!r}"
                )
            current = projected
        return current


__all__ = ["RotationTankFamilyProjectorService"]
