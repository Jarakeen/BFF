from __future__ import annotations

"""Compose canonical Tank hard-obligation evidence at Generate time.

The selected saved build proves role/build identity. Encounter-specific Tank
responsibilities remain explicit caller-owned context: source-backed taunt
applications, continuous target-specific taunt maintenance, reviewed defensive
responses, and reviewed encounter actions that may be contextual rather than directly
rotation-evaluable. Optional strategy evidence is kept separate from those obligations
and is used only to build a candidate-family projector when the caller supplied exact
taunt, refresh, or defensive placement policy. This bridge never infers
responsibilities or strategy from role, boss name, UI labels, or timing windows.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from engine.config import get_data_dir
from models.build_model import PlayerBuild
from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterBoundResponsibility,
)
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_saved_build_action_slot_service import (
    RotationSavedBuildActionSlotService,
)
from services.rotation_tank_defensive_candidate_service import (
    RotationTankDefensiveActionClaim,
)
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)
from services.rotation_tank_family_projector_service import (
    RotationTankFamilyProjectorService,
)
from services.rotation_tank_hard_obligation_service import (
    RotationTankHardObligationService,
)
from services.rotation_tank_taunt_candidate_service import (
    RotationTankTauntActionClaim,
)
from services.rotation_tank_taunt_maintenance_candidate_service import (
    RotationTankTauntMaintenanceRefreshPolicy,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle


PlanEvidenceFactory = Callable[..., object]
TankFamilyProjectorFactory = Callable[..., object]


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class RotationGenerateTankObligationContext:
    """Exact encounter-scoped Tank obligations plus optional explicit strategy."""

    encounter_id: str
    encounter_responsibilities: tuple[RaidTankEncounterBoundResponsibility, ...] = ()
    taunt_application_requirements: tuple[RotationTankTauntApplicationRequirement, ...] = ()
    taunt_maintenance_requirements: tuple[RotationTankTauntMaintenanceRequirement, ...] = ()
    defensive_obligations: tuple[RotationTankDefensiveObligation, ...] = ()
    taunt_application_claims: tuple[RotationTankTauntActionClaim, ...] = ()
    taunt_maintenance_policies: tuple[RotationTankTauntMaintenanceRefreshPolicy, ...] = ()
    defensive_claims: tuple[RotationTankDefensiveActionClaim, ...] = ()

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        if not encounter_id:
            raise ValueError("Tank Generate obligation context requires encounter_id")
        object.__setattr__(self, "encounter_id", encounter_id)
        for field_name in (
            "encounter_responsibilities",
            "taunt_application_requirements",
            "taunt_maintenance_requirements",
            "defensive_obligations",
            "taunt_application_claims",
            "taunt_maintenance_policies",
            "defensive_claims",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        if any(
            row.encounter_id.casefold() != encounter_id.casefold()
            for row in self.encounter_responsibilities
        ):
            raise ValueError(
                "Tank Generate contextual responsibility encounter does not match obligation context"
            )

    @property
    def has_obligations(self) -> bool:
        return bool(
            self.taunt_application_requirements
            or self.taunt_maintenance_requirements
            or self.defensive_obligations
        )

    @property
    def has_contextual_responsibilities(self) -> bool:
        return bool(self.encounter_responsibilities)

    @property
    def has_strategy(self) -> bool:
        return bool(
            self.taunt_application_claims
            or self.taunt_maintenance_policies
            or self.defensive_claims
        )


TankObligationContextProvider = Callable[
    [PlayerBuild, RotationCanonicalEvidenceBundle],
    RotationGenerateTankObligationContext | None,
]


class RotationGenerateTankRoleEvidenceSupport:
    """Join one selected Tank build to explicit obligations and optional strategy."""

    def __init__(
        self,
        *,
        obligation_context_provider: TankObligationContextProvider,
        database_path: str | Path | None = None,
        plan_evidence_factory: PlanEvidenceFactory | None = None,
        hard_obligation_factory: Callable[..., object] | None = None,
        family_projector_factory: TankFamilyProjectorFactory | None = None,
        action_slot_service: RotationSavedBuildActionSlotService | object | None = None,
        reliable_group_healing: bool | None = None,
        exception_contexts: tuple[str, ...] = (),
        role_output_label: str = "tank role output unresolved",
        assigned_support_label: str = "assigned support coverage",
    ) -> None:
        if obligation_context_provider is None:
            raise ValueError("Tank Generate role evidence requires obligation_context_provider")
        self.obligation_context_provider = obligation_context_provider
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.plan_evidence_factory = (
            plan_evidence_factory or RotationCandidateCanonicalPlanEvidenceService
        )
        self.hard_obligation_factory = (
            hard_obligation_factory or RotationTankHardObligationService
        )
        self.family_projector_factory = (
            family_projector_factory or RotationTankFamilyProjectorService
        )
        self.action_slot_service = action_slot_service or RotationSavedBuildActionSlotService()
        self.reliable_group_healing = reliable_group_healing
        self.exception_contexts = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in exception_contexts
                if str(item).strip()
            )
        )
        self.role_output_label = self._required_label(role_output_label, "role_output_label")
        self.assigned_support_label = self._required_label(
            assigned_support_label,
            "assigned_support_label",
        )

    def compose(
        self,
        *,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationCanonicalRoleEvidence:
        role_key = _canonical_role(getattr(player_build, "Role", ""))
        if role_key not in {"tank"}:
            raise ValueError(
                "automatic Tank role evidence requires an explicit Tank saved-build role"
            )

        context = self.obligation_context_provider(player_build, evidence_bundle)
        if context is None:
            raise ValueError(
                "canonical Tank role evidence is unavailable: no explicit encounter-scoped Tank obligation context supplied"
            )
        if context.encounter_id.casefold() != evidence_bundle.encounter_id.casefold():
            raise ValueError(
                "canonical Tank obligation context encounter does not match selected encounter: "
                f"context={context.encounter_id!r}, selected={evidence_bundle.encounter_id!r}"
            )
        if not context.has_obligations:
            raise ValueError(
                "canonical Tank role evidence is unavailable: encounter-scoped Tank context contains no explicit obligations"
            )

        hard_obligation = self.hard_obligation_factory(
            self.database_path,
            taunt_application_requirements=context.taunt_application_requirements,
            taunt_maintenance_requirements=context.taunt_maintenance_requirements,
            defensive_obligations=context.defensive_obligations,
        )
        plan_evidence = self.plan_evidence_factory(
            build=player_build,
            resource=evidence_bundle.resource,
            role_hard_obligation_evidence_provider=hard_obligation,
        )

        if context.has_contextual_responsibilities:
            try:
                setattr(
                    plan_evidence,
                    "tank_encounter_responsibilities",
                    tuple(context.encounter_responsibilities),
                )
            except (AttributeError, TypeError) as exc:
                raise TypeError(
                    "Tank plan evidence provider cannot carry encounter responsibility metadata"
                ) from exc

        if context.has_strategy:
            slot_evidence = self.action_slot_service.resolve(player_build)
            unresolved_slots = tuple(
                str(item).strip()
                for item in getattr(slot_evidence, "unresolved", ())
                if str(item).strip()
            )
            if unresolved_slots:
                raise ValueError(
                    "canonical Tank candidate projection is unavailable because saved-build "
                    "slot identity is unresolved: " + "; ".join(unresolved_slots)
                )
            projector = self.family_projector_factory(
                database_path=self.database_path,
                taunt_application_requirements=context.taunt_application_requirements,
                taunt_application_claims=context.taunt_application_claims,
                taunt_maintenance_requirements=context.taunt_maintenance_requirements,
                taunt_maintenance_policies=context.taunt_maintenance_policies,
                defensive_obligations=context.defensive_obligations,
                defensive_claims=context.defensive_claims,
                slot_requirements=tuple(
                    getattr(slot_evidence, "slot_requirements", ())
                ),
            )
            if bool(getattr(projector, "active", True)):
                try:
                    setattr(plan_evidence, "candidate_projector", projector)
                except (AttributeError, TypeError) as exc:
                    raise TypeError(
                        "Tank plan evidence provider cannot carry candidate projector metadata"
                    ) from exc

        return RotationCanonicalRoleEvidence(
            plan_evidence_provider=plan_evidence,
            role_output_label=self.role_output_label,
            assigned_support_label=self.assigned_support_label,
            content_type=str(evidence_bundle.content_type or "").strip(),
            reliable_group_healing=self.reliable_group_healing,
            exception_contexts=self.exception_contexts,
            role_key=role_key,
        )

    @staticmethod
    def _required_label(value: object, field_name: str) -> str:
        label = str(value or "").strip()
        if not label:
            raise ValueError(f"{field_name} must be non-empty")
        return label


def install_rotation_generate_tank_obligation_context(page) -> None:
    """Install explicit encounter-scoped Tank obligation storage on Rotation Builder."""

    if hasattr(page, "set_rotation_generate_tank_obligation_context"):
        return

    page._rotation_generate_tank_obligation_context = None

    def set_context(context: RotationGenerateTankObligationContext | None) -> None:
        if context is not None and not isinstance(context, RotationGenerateTankObligationContext):
            raise TypeError("Tank obligation context must be RotationGenerateTankObligationContext or None")
        page._rotation_generate_tank_obligation_context = context

    def get_context() -> RotationGenerateTankObligationContext | None:
        return page._rotation_generate_tank_obligation_context

    page.set_rotation_generate_tank_obligation_context = set_context
    page.rotation_generate_tank_obligation_context = get_context


__all__ = [
    "RotationGenerateTankObligationContext",
    "RotationGenerateTankRoleEvidenceSupport",
    "install_rotation_generate_tank_obligation_context",
]
