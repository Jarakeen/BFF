from __future__ import annotations

"""Resolve selected-team provider ownership for Tank Rotation Generate.

This service does not invent assignment or rotation policy. It reuses the existing
Phase 10/11 provider-scope authority for the exact selected roster builds and selected
encounter, including the configured raid Tank responsibility overlay, then asks
``RotationAssignmentPolicyResolver`` whether every assignment owned by the selected
Tank has an explicit executable disposition.

When callers do not supply explicit policy tuples, reviewed policy is loaded from the
shared read-only assignment-policy registry. Provider ownership and rotation policy
remain separate truths. Symbolic encounter-end maintenance policy is preserved on the
resolution but deliberately does not make ``ready`` true until Generate-time horizon
materialization produces an ordinary executable maintenance policy.

An optional explicit requirement-to-member preference may resolve a Phase 11
``UNRESOLVED_SELECTION`` only when that member is already a proven viable provider.
This is the seam used by reviewed encounter responsibility-lane binding; it never turns
an unsupported or unresolved candidate into a provider and never uses roster order as a
tie-break.

Exact taunt skill/bar identity is build evidence, not encounter policy. The selected
Tank's canonical structural-utility source is therefore carried separately and used to
bind skill-agnostic reviewed symbolic ownership policy before it crosses into Generate.
No mechanic is reconstructed from explanatory strings.
"""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from engine.config import get_data_dir
from minmax.build_candidate_provider_scope import build_default_raid_tank_provider_scope
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.encounter_build_capability_adapter import SavedBuildEncounterCapabilityAdapter
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.rotation_assignment_effect_obligation_service import RotationAssignmentEffectPolicy
from services.rotation_assignment_policy_registry_service import (
    RotationAssignmentPolicyRegistryService,
)
from services.rotation_assignment_policy_resolver import (
    RotationAssignmentNonEffectPolicy,
    RotationAssignmentPolicyResolution,
    RotationAssignmentPolicyResolver,
)
from services.rotation_assignment_taunt_maintenance_horizon_policy_service import (
    RotationAssignmentTauntMaintenanceHorizonPolicy,
)
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
)
from services.rotation_assignment_taunt_obligation_service import RotationAssignmentTauntPolicy
from services.saved_build_capability_service import SavedBuildCapabilityService
from services.saved_build_utility_capability_service import (
    SavedBuildUtilityCapabilityService,
    SavedBuildUtilityProviderSource,
)


ProviderScopeFactory = Callable[..., object]


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


def _apply_preferred_assignments(
    assignments: tuple[ProviderAssignment, ...],
    preferred_member_by_requirement: dict[str, str],
) -> tuple[ProviderAssignment, ...]:
    """Resolve only evidence-backed provider-selection ambiguity from explicit strategy."""

    preferences = {
        str(requirement_id or "").strip().casefold(): str(member_id or "").strip()
        for requirement_id, member_id in preferred_member_by_requirement.items()
    }
    if any(not key or not member for key, member in preferences.items()):
        raise ValueError("Tank provider assignment preferences require non-empty identities")
    if not preferences:
        return tuple(assignments)

    known = {assignment.requirement_id.casefold() for assignment in assignments}
    unknown = tuple(sorted(key for key in preferences if key not in known))
    if unknown:
        raise ValueError(
            "Tank provider assignment preference references unknown requirement(s): "
            + ", ".join(unknown)
        )

    resolved: list[ProviderAssignment] = []
    for assignment in assignments:
        preferred = preferences.get(assignment.requirement_id.casefold())
        if preferred is None:
            resolved.append(assignment)
            continue

        if assignment.status not in {
            ProviderAssignmentStatus.ASSIGNED,
            ProviderAssignmentStatus.UNRESOLVED_SELECTION,
        }:
            raise ValueError(
                f"{assignment.requirement_id}: explicit Tank responsibility cannot override provider state {assignment.status.value!r}"
            )

        viable = tuple(
            dict.fromkeys((*assignment.primary_providers, *assignment.backup_providers))
        )
        matches = tuple(
            candidate
            for candidate in viable
            if str(candidate.member_id).casefold() == preferred.casefold()
        )
        if len(matches) != 1:
            raise ValueError(
                f"{assignment.requirement_id}: reviewed Tank responsibility member {preferred!r} is not exactly one proven viable provider"
            )
        chosen = matches[0]

        if assignment.status is ProviderAssignmentStatus.ASSIGNED:
            if len(assignment.primary_providers) != 1:
                raise ValueError(
                    f"{assignment.requirement_id}: reviewed Tank responsibility currently supports one explicit primary provider"
                )
            existing = assignment.primary_providers[0]
            if existing.member_id.casefold() != preferred.casefold():
                raise ValueError(
                    f"{assignment.requirement_id}: existing evidence-backed provider {existing.member_id!r} conflicts with reviewed Tank responsibility member {preferred!r}"
                )
            resolved.append(assignment)
            continue

        backups = tuple(candidate for candidate in viable if candidate != chosen)
        resolved.append(
            replace(
                assignment,
                status=ProviderAssignmentStatus.ASSIGNED,
                primary_providers=(chosen,),
                backup_providers=backups,
                explanation=(
                    "Reviewed encounter Tank responsibility lane explicitly selects this "
                    "already-proven viable provider; no roster-order tie-break is used."
                ),
            )
        )

    return tuple(resolved)


def _bind_horizon_policies_to_taunt_source(
    policies: tuple[RotationAssignmentTauntMaintenanceHorizonPolicy, ...],
    sources: tuple[SavedBuildUtilityProviderSource, ...],
) -> tuple[
    tuple[RotationAssignmentTauntMaintenanceHorizonPolicy, ...],
    tuple[str, ...],
]:
    """Bind build-owned taunt source identity into reviewed symbolic encounter policy."""

    bound: list[RotationAssignmentTauntMaintenanceHorizonPolicy] = []
    unresolved: list[str] = []
    taunt_sources = tuple(source for source in sources if source.capability_type == "taunt")

    for policy in policies:
        reviewed_skill = str(policy.source_skill_name or "").strip()
        candidates = taunt_sources
        if reviewed_skill:
            candidates = tuple(
                source
                for source in taunt_sources
                if source.skill_name.casefold() == reviewed_skill.casefold()
            )
            if len(candidates) != 1:
                unresolved.append(
                    f"{policy.requirement_id}: reviewed taunt skill {reviewed_skill!r} is not exactly one canonical slotted taunt source"
                )
                continue
        elif len(candidates) != 1:
            detail = (
                "none"
                if not candidates
                else ", ".join(f"{row.skill_name} ({row.bar})" for row in candidates)
            )
            unresolved.append(
                f"{policy.requirement_id}: symbolic taunt-maintenance policy requires exactly one canonical saved-build taunt source; found {detail}"
            )
            continue

        source = candidates[0]
        windows = []
        mismatch = False
        for window in policy.windows:
            if window.bar is not None and window.bar != source.bar:
                unresolved.append(
                    f"{policy.requirement_id}:{window.occurrence_id}: reviewed taunt bar {window.bar!r} does not match canonical saved-build taunt bar {source.bar!r}"
                )
                mismatch = True
                break
            windows.append(replace(window, bar=window.bar or source.bar))
        if mismatch:
            continue

        bound.append(
            replace(
                policy,
                source_skill_name=source.skill_name,
                windows=tuple(windows),
            )
        )

    return tuple(bound), tuple(dict.fromkeys(unresolved))


@dataclass(frozen=True)
class RotationTankProviderScopeResolution:
    """Canonical Phase 11 ownership plus explicit policy-readiness for one Tank."""

    encounter_id: str
    member_id: str
    assignments: tuple[ProviderAssignment, ...]
    policy_resolution: RotationAssignmentPolicyResolution
    taunt_maintenance_horizon_policies: tuple[
        RotationAssignmentTauntMaintenanceHorizonPolicy, ...
    ] = ()
    taunt_provider_sources: tuple[SavedBuildUtilityProviderSource, ...] = ()
    taunt_provider_source_unresolved: tuple[str, ...] = ()

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
        object.__setattr__(
            self,
            "taunt_maintenance_horizon_policies",
            tuple(self.taunt_maintenance_horizon_policies),
        )
        object.__setattr__(self, "taunt_provider_sources", tuple(self.taunt_provider_sources))
        object.__setattr__(
            self,
            "taunt_provider_source_unresolved",
            tuple(
                str(value).strip()
                for value in self.taunt_provider_source_unresolved
                if str(value).strip()
            ),
        )

    @property
    def ready(self) -> bool:
        return bool(self.policy_resolution.ready) and not self.taunt_provider_source_unresolved

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (
                    *tuple(self.policy_resolution.unresolved),
                    *self.taunt_provider_source_unresolved,
                )
            )
        )


class RotationTankProviderScopeService:
    """Recompute exact team provider ownership and require explicit rotation policy."""

    def __init__(
        self,
        *,
        data_root: str | Path | None = None,
        database_path: str | Path | None = None,
        build_service: BuildService | None = None,
        capability_service: SavedBuildCapabilityService | object | None = None,
        utility_capability_service: SavedBuildUtilityCapabilityService | object | None = None,
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
        self.utility_capability_service = (
            utility_capability_service
            or SavedBuildUtilityCapabilityService(self.database_path)
        )
        self.scope_factory = scope_factory or build_default_raid_tank_provider_scope
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
        taunt_maintenance_horizon_policies: tuple[
            RotationAssignmentTauntMaintenanceHorizonPolicy, ...
        ] = (),
        non_effect_policies: tuple[RotationAssignmentNonEffectPolicy, ...] = (),
        preferred_member_by_requirement: dict[str, str] | None = None,
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
        assignments = _apply_preferred_assignments(
            tuple(getattr(scope, "baseline_assignments", ())),
            preferred_member_by_requirement or {},
        )

        explicit_policy = bool(
            effect_policies
            or taunt_policies
            or taunt_maintenance_policies
            or taunt_maintenance_horizon_policies
            or non_effect_policies
        )
        if explicit_policy:
            resolved_effect_policies = tuple(effect_policies)
            resolved_taunt_policies = tuple(taunt_policies)
            resolved_taunt_maintenance_policies = tuple(taunt_maintenance_policies)
            resolved_horizon_policies = tuple(taunt_maintenance_horizon_policies)
            resolved_non_effect_policies = tuple(non_effect_policies)
        else:
            reviewed = self.policy_registry.for_encounter(resolved_encounter)
            resolved_effect_policies = tuple(reviewed.effect_policies)
            resolved_taunt_policies = tuple(reviewed.taunt_policies)
            resolved_taunt_maintenance_policies = tuple(reviewed.taunt_maintenance_policies)
            resolved_horizon_policies = tuple(
                getattr(reviewed, "taunt_maintenance_horizon_policies", ())
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

        owned_requirement_ids = {
            assignment.requirement_id.casefold()
            for assignment in assignments
            if assignment.status is ProviderAssignmentStatus.ASSIGNED
            and any(
                candidate.member_id.casefold() == member_id.casefold()
                for candidate in assignment.primary_providers
            )
        }
        resolved_horizon_policies = tuple(
            policy
            for policy in resolved_horizon_policies
            if policy.requirement_id.casefold() in owned_requirement_ids
        )

        taunt_sources: tuple[SavedBuildUtilityProviderSource, ...] = ()
        bound_horizon_policies: tuple[
            RotationAssignmentTauntMaintenanceHorizonPolicy, ...
        ] = ()
        source_unresolved: tuple[str, ...] = ()
        binding_unresolved: tuple[str, ...] = ()
        if resolved_horizon_policies:
            taunt_source_resolution = self.utility_capability_service.provider_sources_for(
                build=player_build,
                capability_type="taunt",
            )
            taunt_sources = tuple(getattr(taunt_source_resolution, "sources", ()))
            # Once a concrete taunt source is proven, unrelated unresolved slotted
            # skills must not poison that exact utility identity. If no taunt source
            # is proven, the unresolved discovery evidence remains a blocker.
            source_unresolved = (
                ()
                if taunt_sources
                else tuple(getattr(taunt_source_resolution, "unresolved", ()))
            )
            bound_horizon_policies, binding_unresolved = (
                _bind_horizon_policies_to_taunt_source(
                    resolved_horizon_policies,
                    taunt_sources,
                )
            )

        return RotationTankProviderScopeResolution(
            encounter_id=resolved_encounter,
            member_id=member_id,
            assignments=assignments,
            policy_resolution=policy_resolution,
            taunt_maintenance_horizon_policies=bound_horizon_policies,
            taunt_provider_sources=taunt_sources,
            taunt_provider_source_unresolved=tuple(
                dict.fromkeys((*source_unresolved, *binding_unresolved))
            ),
        )


__all__ = [
    "RotationTankProviderScopeResolution",
    "RotationTankProviderScopeService",
]
