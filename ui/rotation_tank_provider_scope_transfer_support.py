from __future__ import annotations

"""Deliver selected-team Tank provider evidence into Rotation Builder.

MainWindow owns both Team Optimization and Rotation Builder, so this bridge reuses
those existing stateful pages instead of creating another global selected-team store.
The authoritative Team Optimization prescription is resolved back to exact saved
builds through its structured assignment identities; UI tables are not scraped.
Provider ownership remains service-layer truth; this module only transfers that result
into RotationGenerateTankAssignmentEvidence.
"""

from dataclasses import dataclass

from services.rotation_tank_provider_scope_service import RotationTankProviderScopeService
from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentEvidence,
)


_INSTALLED = False
_ORIGINAL_SHOW_PAGE = None
_ORIGINAL_GENERATE = None


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


def _saved_build_player_identity(build) -> str:
    return (
        str(getattr(build, "Name", "") or "").strip()
        or str(getattr(build, "Gamertag", "") or "").strip()
    ).casefold()


def _prescription_saved_builds(optimization_page) -> tuple[tuple, tuple[str, ...]]:
    """Resolve the authoritative prescription to exact persisted saved builds.

    A prescription may contain recruit/open chairs or an ambiguous saved-player source.
    Either case is unresolved for provider ownership: Phase 11 must see the exact team,
    not a favorable partial reconstruction.
    """

    prescription = getattr(optimization_page, "current_prescription", None)
    if prescription is None:
        return (), ("Team Optimization has no authoritative current prescription",)

    roster = tuple(
        getattr(getattr(optimization_page, "roster", None), "Members", ()) or ()
    )
    if not roster:
        return (), ("Team Optimization has no saved builds available for the prescription",)

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
        seen.add(key)
        resolved.append(build)

    if unresolved:
        return (), tuple(unresolved)
    if not resolved:
        return (), ("Team Optimization prescription contains no exact saved-build team",)
    return tuple(resolved), ()


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


def refresh_rotation_tank_provider_scope(
    window,
    *,
    provider_scope_service: RotationTankProviderScopeService | object | None = None,
) -> RotationTankProviderScopeTransferResult:
    """Refresh Rotation Builder's Tank assignment evidence from the selected team.

    Non-Tank Rotation selections deliberately clear Tank evidence so stale assignment
    ownership cannot leak across role/build changes. Missing or ambiguous team state
    also clears evidence and returns an explicit unresolved reason rather than guessing.
    """

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

    try:
        scope = service.resolve(
            player_build=selected_build,
            roster_builds=roster_builds,
            encounter_id=encounter_id,
        )
    except (LookupError, ValueError) as exc:
        _clear_tank_assignment_evidence(rotation_page)
        return RotationTankProviderScopeTransferResult(
            False,
            encounter_id=encounter_id,
            unresolved=(str(exc),),
        )

    policy = scope.policy_resolution
    evidence = RotationGenerateTankAssignmentEvidence(
        encounter_id=scope.encounter_id,
        member_id=scope.member_id,
        assignments=tuple(scope.assignments),
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


def _show_page_with_tank_provider_scope(self, page_name: str, *args, **kwargs):
    assert _ORIGINAL_SHOW_PAGE is not None
    result = _ORIGINAL_SHOW_PAGE(self, page_name, *args, **kwargs)
    if page_name == "rotations":
        rotation_page = (getattr(self, "pages", {}) or {}).get("rotations")
        if rotation_page is not None:
            rotation_page._rotation_tank_provider_scope_transfer_owner = self
        refresh_rotation_tank_provider_scope(self)
    return result


def _generate_with_fresh_tank_provider_scope(self, page) -> None:
    assert _ORIGINAL_GENERATE is not None
    owner = getattr(page, "_rotation_tank_provider_scope_transfer_owner", None)
    if owner is not None:
        refresh_rotation_tank_provider_scope(owner)
    return _ORIGINAL_GENERATE(self, page)


def install() -> None:
    global _INSTALLED, _ORIGINAL_SHOW_PAGE, _ORIGINAL_GENERATE
    if _INSTALLED:
        return

    from ui.main_window import MainWindow
    from ui.rotation_generate_action_support import RotationGenerateActionSupport

    _ORIGINAL_SHOW_PAGE = MainWindow.show_page
    MainWindow.show_page = _show_page_with_tank_provider_scope
    _ORIGINAL_GENERATE = RotationGenerateActionSupport.generate
    RotationGenerateActionSupport.generate = _generate_with_fresh_tank_provider_scope
    _INSTALLED = True


__all__ = [
    "RotationTankProviderScopeTransferResult",
    "install",
    "refresh_rotation_tank_provider_scope",
]
