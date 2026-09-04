from __future__ import annotations

from models.build_model import PlayerBuild

from .team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    TeamPrescriptionScope,
)
from .team_role_autofill import build_role_compatible_autofill, slot_role_family


def _player_name(build: PlayerBuild) -> str:
    return (
        str(getattr(build, "Name", "") or "").strip()
        or str(getattr(build, "Gamertag", "") or "").strip()
        or "Unnamed Player"
    )


def _player_key(build: PlayerBuild, index: int) -> str:
    identity = (
        str(getattr(build, "Name", "") or "").strip()
        or str(getattr(build, "Gamertag", "") or "").strip()
    )
    return identity or f"unnamed-build:{index}"


def _build_name(build: PlayerBuild) -> str:
    return str(getattr(build, "BuildName", "") or "").strip() or "Current Build"


def _prescribed_role(slot_label: str) -> str:
    family = slot_role_family(slot_label)
    if family == "tank":
        return "Tank"
    if family == "healer":
        return "Healer"
    return "DD"


def generate_prescribed_roster_from_saved_builds(
    *,
    name: str,
    goal: str,
    slot_labels: tuple[str, ...],
    builds: tuple[PlayerBuild, ...],
    scope: TeamPrescriptionScope,
) -> PrescribedRoster:
    """Create a non-destructive roster prescription from known saved anchors.

    Existing builds are assigned only to compatible role families and each named
    saved player can occupy at most one chair even when that player owns many saved
    builds. Open slots become explicit requirements instead of fabricated players.
    """

    slots = tuple(str(value or "").strip() for value in slot_labels)
    if not slots or any(not value for value in slots):
        raise ValueError("prescribed roster generation requires non-empty slot labels")

    saved_builds = tuple(builds)
    autofill = build_role_compatible_autofill(
        slot_labels=slots,
        build_roles=tuple(getattr(build, "Role", "") for build in saved_builds),
        build_player_keys=tuple(
            _player_key(build, index) for index, build in enumerate(saved_builds)
        ),
    )

    assignments: list[PrescribedRosterAssignment] = []
    unresolved: list[str] = []

    for autofill_assignment in autofill:
        slot = autofill_assignment.slot_label
        role = _prescribed_role(slot)
        build_index = autofill_assignment.build_index
        if build_index is None:
            requirement = (
                f"{slot}: no compatible saved player is available; "
                "candidate/recruitment prescription is required"
            )
            assignments.append(
                PrescribedRosterAssignment(
                    slot_name=slot,
                    player_name=None,
                    source_build_name=None,
                    prescribed_role=role,
                    unresolved=(
                        requirement,
                        (
                            f"{slot}: class, race, build, gear, skills, CP, Mundus, "
                            "food, and potion remain unresolved until canonical "
                            "optimization evidence is evaluated"
                        ),
                    ),
                )
            )
            unresolved.append(requirement)
            continue

        build = saved_builds[build_index]
        assignments.append(
            PrescribedRosterAssignment(
                slot_name=slot,
                player_name=_player_name(build),
                source_build_name=_build_name(build),
                prescribed_role=role,
            )
        )

    return PrescribedRoster(
        name=name,
        goal=goal,
        scope=scope,
        assignments=tuple(assignments),
        assumptions=(
            "Saved builds are role-compatible anchors, not proof that their current class, race, gear, or loadout is optimal for the selected goal.",
            "A saved player may occupy only one roster slot even when multiple builds are available.",
            "Open slots are left unresolved until canonical build/provider candidate evidence can prescribe them.",
        ),
        unresolved=tuple(unresolved),
    )
