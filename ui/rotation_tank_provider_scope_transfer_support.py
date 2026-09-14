from __future__ import annotations

"""Deliver selected-team Tank provider evidence into Rotation Builder.

MainWindow owns both Team Optimization and Rotation Builder, so this bridge reuses
those existing stateful pages instead of creating another global selected-team store.
Exact saved builds are resolved through the same Team Optimization helper already used
by provider workload analysis. Provider ownership remains service-layer truth; this
module only transfers that result into RotationGenerateTankAssignmentEvidence.
"""

from dataclasses import dataclass

from services.rotation_tank_provider_scope_service import RotationTankProviderScopeService
from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentEvidence,
)
from ui.team_provider_workload_support import _optimization_selected_saved_builds


_INSTALLED = False
_ORIGINAL_SHOW_PAGE = None


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


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

    roster_builds = tuple(_optimization_selected_saved_builds(optimization_page))
    if not roster_builds:
        _clear_tank_assignment_evidence(rotation_page)
        return RotationTankProviderScopeTransferResult(
            False,
            encounter_id=encounter_id,
            unresolved=("Team Optimization has no exact selected saved-build team",),
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
        refresh_rotation_tank_provider_scope(self)
    return result


def install() -> None:
    global _INSTALLED, _ORIGINAL_SHOW_PAGE
    if _INSTALLED:
        return

    from ui.main_window import MainWindow

    _ORIGINAL_SHOW_PAGE = MainWindow.show_page
    MainWindow.show_page = _show_page_with_tank_provider_scope
    _INSTALLED = True


__all__ = [
    "RotationTankProviderScopeTransferResult",
    "install",
    "refresh_rotation_tank_provider_scope",
]
