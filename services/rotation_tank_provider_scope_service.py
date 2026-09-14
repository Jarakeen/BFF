from __future__ import annotations

"""Resolve selected-team provider ownership for Tank Rotation Generate.

This service does not invent assignment or rotation policy. It reuses the existing
Phase 10/11 provider-scope authority for the exact selected roster builds and selected
encounter, then asks ``RotationAssignmentPolicyResolver`` whether every assignment
owned by the selected Tank has an explicit executable disposition.

When callers do not supply explicit policy tuples, reviewed policy is loaded from the
shared read-only assignment-policy registry. Provider ownership and rotation policy
remain separate truths. A caller may only treat the result as Rotation-ready when
``ready`` is true.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from engine.config import get_data_dir
from minmax.build_candidate_provider_scope import build_default_raid_provider_scope
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.encounter_build_capability_adapter import SavedBuildEncounterCapabilityAdapter
from services.encounter_provider_assignment import ProviderAssignment
from services.rotation_assignment_effect_obligation_service import RotationAssignmentEffectPolicy
from services.rotation_assignment_policy_registry_service import (
    RotationAssignmentPolicyRegistryService,
)
from services.rotation_assignment_policy_resolver import (
    RotationAssignmentNonEffectPolicy,
    RotationAssignmentPolicyResolution,
    RotationAssignmentPolicyResolver,
)
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
)
from services.rotation_assignment_taunt_obligation_service import RotationAssignmentTauntPolicy
from services.saved_build_capability_service import SavedBuildCapabilityService


ProviderScopeFactory = Callable[..., object]


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


@dataclass(frozen=True)
class RotationTankProviderScopeResolution:
    """Canonical Phase 11 ownership plus explicit policy-readiness for one Tank."""

    encounter_id: str
    member_id: str
    assignments: tuple[ProviderAssignment, ...]
    policy_resolution: RotationAssignmentPolicyResolution

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        member_id = str(self.member_id or "").strip()
        if not encounter_id:
            raise ValueError("Tank provider-scope resolution requires encounter_id")
        if not member_id:
            raise ValueError("Tank provider-scope resolution requires member_id")
        object.__setattr__(self, "encounter_id", encounter_id)
        object.__setattr__(self, "member_id", member_id)
        object.__setattr__(self, "assignments", tuple(self.assignments))

    @property
    def ready(self) -> bool:
        return bool(self.policy_resolution.ready)

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(self.policy_resolution.unresolved)


class RotationTankProviderScopeService:
    """Recompute exact team provider ownership and require explicit rotation policy."""

    def __init__(
        self,
        *,
        data_root: str | Path | None = None,
        database_path: str | Path | None = None,
        build_service: BuildService | None = None,
        capability_service: SavedBuildCapabilityService | object | None = None,
        scope_factory: ProviderScopeFactory | None = None,
        policy_resolver: RotationAssignmentPolicyResolver | object | None = None,
        policy_registry: RotationAssignmentPolicyRegistryService | object | None = None,
    ) -> None:
        self.data_root = Path(data_root) if data_root is not None else get_data_dir()
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else self.data_root / "eso.db"
        )
        self.build_service = build_service or BuildService(self.data_root / "builds.json")
        self.capability_service = capability_service or SavedBuildCapabilityService(
            self.build_service,
            self.database_path,
        )
        self.scope_factory = scope_factory or build_default_raid_provider_scope
        self.policy_resolver = policy_resolver or RotationAssignmentPolicyResolver()
        self.policy_registry = policy_registry or RotationAssignmentPolicyRegistryService(
            self.data_root / "rotation_assignment_policy" / "reviewed.json"
        )

    def resolve(
        self,
        *,
        player_build: PlayerBuild,
        roster_builds: tuple[PlayerBuild, ...],
        encounter_id: str,
        effect_policies: tuple[RotationAssignmentEffectPolicy, ...] = (),
        taunt_policies: tuple[RotationAssignmentTauntPolicy, ...] = (),
        taunt_maintenance_policies: tuple[
            RotationAssignmentTauntMaintenancePolicy, ...
        ] = (),
        non_effect_policies: tuple[RotationAssignmentNonEffectPolicy, ...] = (),
    ) -> RotationTankProviderScopeResolution:
        resolved_encounter = str(encounter_id or "").strip()
        if not resolved_encounter:
            raise ValueError("Tank provider scope requires encounter_id")
        if _canonical_role(getattr(player_build, "Role", "")) != "tank":
            raise ValueError("Tank provider scope requires an explicit Tank saved-build role")

        roster = tuple(roster_builds)
        if not roster:
            raise ValueError("Tank provider scope requires exact selected-team saved builds")

        tank_audit = self.capability_service.audit_build(player_build)
        member_id = SavedBuildEncounterCapabilityAdapter.member_id(tank_audit)
        if not member_id:
            raise ValueError("Tank provider scope could not resolve canonical member identity")

        scope = self.scope_factory(
            encounter_id=resolved_encounter,
            member_id=member_id,
            roster_builds=roster,
            capability_service=self.capability_service,
            data_root=self.data_root,
            database_path=self.database_path,
        )
        assignments = tuple(getattr(scope, "baseline_assignments", ()))

        explicit_policy = bool(
            effect_policies
            or taunt_policies
            or taunt_maintenance_policies
            or non_effect_policies
        )
        if explicit_policy:
            resolved_effect_policies = tuple(effect_policies)
            resolved_taunt_policies = tuple(taunt_policies)
            resolved_taunt_maintenance_policies = tuple(taunt_maintenance_policies)
            resolved_non_effect_policies = tuple(non_effect_policies)
        else:
            reviewed = self.policy_registry.for_encounter(resolved_encounter)
            resolved_effect_policies = tuple(reviewed.effect_policies)
            resolved_taunt_policies = tuple(reviewed.taunt_policies)
            resolved_taunt_maintenance_policies = tuple(
                reviewed.taunt_maintenance_policies
            )
            resolved_non_effect_policies = tuple(reviewed.non_effect_policies)

        policy_resolution = self.policy_resolver.resolve(
            member_id=member_id,
            assignments=assignments,
            effect_policies=resolved_effect_policies,
            taunt_policies=resolved_taunt_policies,
            taunt_maintenance_policies=resolved_taunt_maintenance_policies,
            non_effect_policies=resolved_non_effect_policies,
        )
        if policy_resolution.member_id.casefold() != member_id.casefold():
            raise ValueError(
                "Tank provider-scope policy resolution member mismatch: "
                f"expected {member_id!r}, got {policy_resolution.member_id!r}"
            )

        return RotationTankProviderScopeResolution(
            encounter_id=resolved_encounter,
            member_id=member_id,
            assignments=assignments,
            policy_resolution=policy_resolution,
        )


__all__ = [
    "RotationTankProviderScopeResolution",
    "RotationTankProviderScopeService",
]
