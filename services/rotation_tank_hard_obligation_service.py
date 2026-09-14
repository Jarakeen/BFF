from __future__ import annotations

"""Compose canonical Tank hard obligations for one generated rotation candidate.

Tank responsibilities are deliberately modeled by separate authoritative services:
source-backed taunt applications, continuous target-specific taunt maintenance, and
reviewed defensive responses. Rotation Candidate evaluation exposes one role-hard-
obligation channel, so this service composes those independent truths without
collapsing them into a scalar Tank score.

A resolved failure dominates unresolved evidence because the candidate is already
known to violate a hard obligation. Otherwise unresolved evidence remains unresolved;
only candidates that pass every supplied Tank obligation receive a resolved pass.
"""

from pathlib import Path

from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleHardObligationEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
    RotationTankDefensiveObligationService,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
    RotationTankTauntMaintenanceService,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
    RotationTankTauntObligationService,
)


class RotationTankHardObligationService:
    """Expose all supplied Tank hard obligations through one canonical evidence lane."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        taunt_application_requirements: tuple[
            RotationTankTauntApplicationRequirement, ...
        ] = (),
        taunt_maintenance_requirements: tuple[
            RotationTankTauntMaintenanceRequirement, ...
        ] = (),
        defensive_obligations: tuple[RotationTankDefensiveObligation, ...] = (),
        taunt_application_service: RotationTankTauntObligationService | object | None = None,
        taunt_maintenance_service: RotationTankTauntMaintenanceService | object | None = None,
        defensive_service: RotationTankDefensiveObligationService | object | None = None,
    ) -> None:
        self.taunt_application_requirements = tuple(taunt_application_requirements)
        self.taunt_maintenance_requirements = tuple(taunt_maintenance_requirements)
        self.defensive_obligations = tuple(defensive_obligations)
        self.taunt_application_service = (
            taunt_application_service
            or RotationTankTauntObligationService(database_path)
        )
        self.taunt_maintenance_service = (
            taunt_maintenance_service
            or RotationTankTauntMaintenanceService(database_path)
        )
        self.defensive_service = defensive_service or RotationTankDefensiveObligationService()

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRoleHardObligationEvidence:
        if not (
            self.taunt_application_requirements
            or self.taunt_maintenance_requirements
            or self.defensive_obligations
        ):
            return RotationCandidateRoleHardObligationEvidence(
                candidate_id=candidate.candidate_id,
                satisfied=None,
                reasons=(
                    "tank hard obligation unavailable: no explicit taunt application, taunt maintenance, or defensive obligation supplied",
                ),
            )

        states: list[bool | None] = []
        reasons: list[str] = []

        for requirement in self.taunt_application_requirements:
            assessment = self.taunt_application_service.assess(
                plan=candidate.plan,
                requirement=requirement,
            )
            if not bool(getattr(assessment, "resolved", False)):
                states.append(None)
                unresolved = tuple(getattr(assessment, "unresolved", ())) or (
                    f"{requirement.requirement_id}: taunt application evidence unresolved",
                )
                reasons.extend(str(item) for item in unresolved)
                continue

            applications = tuple(getattr(assessment, "applications", ()))
            if not bool(getattr(assessment, "satisfied", False)):
                states.append(False)
                reasons.append(
                    f"{requirement.requirement_id}: scheduled {len(applications)} of "
                    f"{requirement.minimum_applications} required taunt applications"
                )
                continue

            states.append(True)
            reasons.append(
                f"{requirement.requirement_id}: scheduled {len(applications)} required taunt applications"
            )

        if self.taunt_maintenance_requirements:
            maintenance = self.taunt_maintenance_service.evaluate_candidate(
                candidate=candidate,
                requirements=self.taunt_maintenance_requirements,
            )
            self._validate_candidate_identity(candidate, maintenance, "taunt maintenance")
            states.append(maintenance.satisfied)
            reasons.extend(maintenance.reasons)

        if self.defensive_obligations:
            defensive = self.defensive_service.evaluate_candidate(
                candidate=candidate,
                obligations=self.defensive_obligations,
            )
            self._validate_candidate_identity(candidate, defensive, "defensive obligation")
            states.append(defensive.satisfied)
            reasons.extend(defensive.reasons)

        if False in states:
            satisfied: bool | None = False
        elif None in states:
            satisfied = None
        else:
            satisfied = True

        return RotationCandidateRoleHardObligationEvidence(
            candidate_id=candidate.candidate_id,
            satisfied=satisfied,
            reasons=self._dedupe(tuple(reasons)),
        )

    @staticmethod
    def _validate_candidate_identity(candidate, evidence, lane: str) -> None:
        if str(evidence.candidate_id).casefold() != candidate.candidate_id.casefold():
            raise ValueError(
                f"tank {lane} evidence candidate mismatch: expected "
                f"{candidate.candidate_id!r}, got {evidence.candidate_id!r}"
            )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = ["RotationTankHardObligationService"]
