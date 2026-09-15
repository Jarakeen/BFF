from __future__ import annotations

"""Deliver selected-team Tank provider evidence into Rotation Builder.

MainWindow owns both Team Optimization and Rotation Builder, so this bridge reuses
those existing stateful pages instead of creating another global selected-team store.
The authoritative Team Optimization prescription is resolved back to exact saved
builds through its structured assignment identities; UI tables are not scraped.
Provider ownership remains service-layer truth; this module only transfers that result
into RotationGenerateTankAssignmentEvidence.

Reviewed encounter Tank responsibility lanes are bound only through exact prescription
slot identities declared by the reviewed lane registry. Main/Off Tank is never inferred
from roster order, build names, or role labels. When a reviewed lane responsibility
matches a canonical raid-Tank provider requirement, the bound member may resolve only
provider-selection ambiguity among already-proven viable providers.
"""

from dataclasses import dataclass

from services.encounter_build_capability_adapter import SavedBuildEncounterCapabilityAdapter
from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterResponsibilityBindingService,
)
from services.raid_tank_responsibility_encounter_adapter import (
    RaidTankResponsibilityEncounterAdapter,
)
from services.raid_tank_responsibility_profile import (
    DEFAULT_RAID_TANK_RESPONSIBILITY_PROFILE,
)
from services.rotation_tank_provider_scope_service import RotationTankProviderScopeService
from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentEvidence,
)


_INSTALLED = False

def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


def _saved_build_player_identity(build) -> str:
    return (
        str(getattr(build, "Name", "") or "").strip()
        or str(getattr(build, "Gamertag", "") or "").strip()
    ).casefold()


def _prescription_slot_saved_builds(
    optimization_page,
) -> tuple[dict[str, object], tuple, tuple[str, ...]]:
    """Resolve authoritative prescription slots to exact persisted saved builds."""

    prescription = getattr(optimization_page, "current_prescription", None)
    if prescription is None:
        return {}, (), ("Team Optimization has no authoritative current prescription",)

    roster = tuple(
        getattr(getattr(optimization_page, "roster", None), "Members", ()) or ()
    )
    if not roster:
        return {}, (), ("Team Optimization has no saved builds available for the prescription",)

    by_slot: dict[str, object] = {}
    resolved = []
    unresolved: list[str] = []
    seen: set[tuple[str, str]] = set()
    for assignment in tuple(getattr(prescription, "assignments", ()) or ()):
        slot_name = str(getattr(assignment, "slot_name", "") or "Unnamed slot").strip()
        player_name = str(getattr(assignment, "player_name", "") or "").strip()
        source_build_name = str(
            getattr(assignment, "source_build_name", "") or ""
        ).strip()
        if not player_name:
            unresolved.append(
                f"{slot_name}: prescription does not identify an exact saved player"
            )
            continue

        target_player = player_name.casefold()
        target_build = source_build_name.casefold()
        matches = [
            build
            for build in roster
            if _saved_build_player_identity(build) == target_player
            and (
                not target_build
                or str(getattr(build, "BuildName", "") or "").strip().casefold()
                == target_build
            )
        ]
        if len(matches) != 1:
            detail = source_build_name or "an unambiguous saved build"
            unresolved.append(
                f"{slot_name}: could not resolve {player_name} / {detail} to exactly one saved build"
            )
            continue

        build = matches[0]
        key = (
            _saved_build_player_identity(build),
            str(getattr(build, "BuildName", "") or "").strip().casefold(),
        )
        if key in seen:
            unresolved.append(
                f"{slot_name}: saved build {player_name} / {getattr(build, 'BuildName', '')} is assigned more than once"
            )
            continue
        if slot_name.casefold() in {value.casefold() for value in by_slot}:
            unresolved.append(f"{slot_name}: prescription slot identity is duplicated")
            continue
        seen.add(key)
        by_slot[slot_name] = build
        resolved.append(build)

    if unresolved:
        return {}, (), tuple(unresolved)
    if not resolved:
        return {}, (), ("Team Optimization prescription contains no exact saved-build team",)
    return by_slot, tuple(resolved), ()


def _prescription_saved_builds(optimization_page) -> tuple[tuple, tuple[str, ...]]:
    """Resolve the authoritative prescription to exact persisted saved builds."""

    _by_slot, resolved, unresolved = _prescription_slot_saved_builds(optimization_page)
    return resolved, unresolved


@dataclass(frozen=True)
class RotationTankProviderScopeTransferResult:
    transferred: bool
    encounter_id: str = ""
    member_id: str = ""
    unresolved: tuple[str, ...] = ()


def _clear_tank_assignment_evidence(rotation_page) -> None:
    setter = getattr(rotation_page, "set_rotation_generate_tank_assignment_evidence", None)
    if callable(setter):
        setter(())


def _bind_encounter_responsibilities(
    *,
    encounter_id: str,
    optimization_page,
    provider_scope_service,
    binding_service: RaidTankEncounterResponsibilityBindingService,
):
    plan = binding_service.lane_service.for_encounter(encounter_id)
    if plan is None:
        return None, ()

    slot_builds, _roster, unresolved = _prescription_slot_saved_builds(optimization_page)
    if unresolved:
        return None, unresolved

    required_capabilities = tuple(
        dict.fromkeys(
            responsibility.required_capability_type
            for lane in plan.lanes
            for responsibility in lane.responsibilities
            if responsibility.required_capability_type is not None
        )
    )
    slot_members: dict[str, str] = {}
    member_capabilities: dict[str, tuple[str, ...]] = {}
    capability_unresolved: list[str] = []

    for slot_name, build in slot_builds.items():
        lane = plan.lane_for_prescription_slot(slot_name)
        if lane is None:
            continue
        audit = provider_scope_service.capability_service.audit_build(build)
        member_id = SavedBuildEncounterCapabilityAdapter.member_id(audit)
        slot_members[slot_name] = member_id
        supported: list[str] = []
        for capability_type in required_capabilities:
            resolution = provider_scope_service.utility_capability_service.provider_sources_for(
                build=build,
                capability_type=capability_type,
            )
            if tuple(getattr(resolution, "sources", ())):
                supported.append(capability_type)
            elif tuple(getattr(resolution, "unresolved", ())):
                detail = "; ".join(str(item) for item in resolution.unresolved)
                capability_unresolved.append(
                    f"{encounter_id}:{lane.lane_id}:{member_id}: canonical {capability_type} capability is unresolved: {detail}"
                )
        member_capabilities[member_id] = tuple(supported)

    if capability_unresolved:
        return None, tuple(dict.fromkeys(capability_unresolved))

    binding = binding_service.bind(
        encounter_id=encounter_id,
        prescription_slot_members=slot_members,
        member_capabilities=member_capabilities,
    )
    if not binding.resolved:
        return binding, tuple(binding.unresolved)
    return binding, ()


def _provider_preferences_for_binding(encounter_id: str, binding) -> dict[str, str]:
    if binding is None:
        return {}
    adapter = RaidTankResponsibilityEncounterAdapter(
        DEFAULT_RAID_TANK_RESPONSIBILITY_PROFILE
    )
    canonical_by_suffix = {
        requirement.requirement_id.rsplit(":tank:", 1)[-1].casefold(): requirement.requirement_id
        for requirement in adapter.requirements(encounter_id)
    }
    preferred: dict[str, str] = {}
    for row in binding.responsibilities:
        canonical_id = canonical_by_suffix.get(
            row.responsibility.responsibility_id.casefold()
        )
        if canonical_id is None:
            continue
        prior = preferred.get(canonical_id)
        if prior is not None and prior.casefold() != row.member_id.casefold():
            raise ValueError(
                f"{canonical_id}: reviewed Tank lanes assign the same provider requirement to multiple members"
            )
        preferred[canonical_id] = row.member_id
    return preferred


def refresh_rotation_tank_provider_scope(
    window,
    *,
    provider_scope_service: RotationTankProviderScopeService | object | None = None,
    responsibility_binding_service: (
        RaidTankEncounterResponsibilityBindingService | object | None
    ) = None,
) -> RotationTankProviderScopeTransferResult:
    """Refresh Rotation Builder's Tank assignment evidence from the selected team."""

    pages = getattr(window, "pages", {}) or {}
    rotation_page = pages.get("rotations")
    if rotation_page is None:
        return RotationTankProviderScopeTransferResult(
            False,
            unresolved=("Rotation Builder page is unavailable",),
        )

    setter = getattr(rotation_page, "set_rotation_generate_tank_assignment_evidence", None)
    if not callable(setter):
        return RotationTankProviderScopeTransferResult(
            False,
            unresolved=("Rotation Builder Tank assignment evidence setter is unavailable",),
        )

    selected_build_fn = getattr(rotation_page, "_selected_build", None)
    selected_build = selected_build_fn() if callable(selected_build_fn) else None
    if selected_build is None:
        _clear_tank_assignment_evidence(rotation_page)
        return RotationTankProviderScopeTransferResult(
            False,
            unresolved=("Rotation Builder has no selected saved build",),
        )
    if _canonical_role(getattr(selected_build, "Role", "")) != "tank":
        _clear_tank_assignment_evidence(rotation_page)
        return RotationTankProviderScopeTransferResult(False)

    selected_encounter_fn = getattr(rotation_page, "_selected_encounter_id", None)
    encounter_id = (
        str(selected_encounter_fn() or "").strip()
        if callable(selected_encounter_fn)
        else ""
    )
    if not encounter_id:
        _clear_tank_assignment_evidence(rotation_page)
        return RotationTankProviderScopeTransferResult(
            False,
            unresolved=("Rotation Builder has no selected encounter",),
        )

    optimization_page = pages.get("console:6")
    if optimization_page is None:
        _clear_tank_assignment_evidence(rotation_page)
        return RotationTankProviderScopeTransferResult(
            False,
            encounter_id=encounter_id,
            unresolved=("Team Optimization page is unavailable",),
        )

    roster_builds, team_unresolved = _prescription_saved_builds(optimization_page)
    if team_unresolved:
        _clear_tank_assignment_evidence(rotation_page)
        return RotationTankProviderScopeTransferResult(
            False,
            encounter_id=encounter_id,
            unresolved=team_unresolved,
        )

    service = provider_scope_service
    if service is None:
        service = getattr(window, "_rotation_tank_provider_scope_service", None)
        if service is None:
            service = RotationTankProviderScopeService()
            window._rotation_tank_provider_scope_service = service

    binding_service = responsibility_binding_service
    if binding_service is None:
        binding_service = getattr(
            window,
            "_rotation_tank_responsibility_binding_service",
            None,
        )
        if binding_service is None:
            binding_service = RaidTankEncounterResponsibilityBindingService()
            window._rotation_tank_responsibility_binding_service = binding_service

    try:
        binding, lane_unresolved = _bind_encounter_responsibilities(
            encounter_id=encounter_id,
            optimization_page=optimization_page,
            provider_scope_service=service,
            binding_service=binding_service,
        )
        if lane_unresolved:
            _clear_tank_assignment_evidence(rotation_page)
            return RotationTankProviderScopeTransferResult(
                False,
                encounter_id=encounter_id,
                unresolved=lane_unresolved,
            )
        preferences = _provider_preferences_for_binding(encounter_id, binding)
        scope = service.resolve(
            player_build=selected_build,
            roster_builds=roster_builds,
            encounter_id=encounter_id,
            preferred_member_by_requirement=preferences,
        )
    except (LookupError, ValueError) as exc:
        _clear_tank_assignment_evidence(rotation_page)
        return RotationTankProviderScopeTransferResult(
            False,
            encounter_id=encounter_id,
            unresolved=(str(exc),),
        )

    contextual = () if binding is None else binding.for_member(scope.member_id)
    policy = scope.policy_resolution
    evidence = RotationGenerateTankAssignmentEvidence(
        encounter_id=scope.encounter_id,
        member_id=scope.member_id,
        assignments=tuple(scope.assignments),
        encounter_responsibilities=tuple(contextual),
        taunt_policies=tuple(getattr(policy, "taunt_policies", ())),
        taunt_maintenance_policies=tuple(
            getattr(policy, "taunt_maintenance_policies", ())
        ),
        taunt_maintenance_horizon_policies=tuple(
            getattr(scope, "taunt_maintenance_horizon_policies", ())
        ),
    )
    setter((evidence,))
    return RotationTankProviderScopeTransferResult(
        True,
        encounter_id=scope.encounter_id,
        member_id=scope.member_id,
        unresolved=tuple(getattr(scope, "unresolved", ())),
    )


def prepare_rotation_tank_provider_scope(window) -> RotationTankProviderScopeTransferResult:
    """Bind a fresh provider-scope callback to Rotation and refresh it now."""
    rotation_page = (getattr(window, "pages", {}) or {}).get("rotations")
    if rotation_page is not None:
        rotation_page._refresh_rotation_tank_provider_scope = (
            lambda: refresh_rotation_tank_provider_scope(window)
        )
    return refresh_rotation_tank_provider_scope(window)


__all__ = [
    "RotationTankProviderScopeTransferResult",
    "prepare_rotation_tank_provider_scope",
    "refresh_rotation_tank_provider_scope",
]
