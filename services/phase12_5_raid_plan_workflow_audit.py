from __future__ import annotations

"""Canonical Phase 12.5 Raid Plan workflow integrity audit.

This service is deliberately read-only.  It verifies that the planning snapshot which
Comp Maker/Raid Plan hands to downstream consumers still refers to the same reusable
Roster/Character/Build identities and preserves explicit locks, assignments, recruit
state, and unresolved evidence.  It does not judge encounter outcome or invent missing
build state.
"""

from dataclasses import dataclass
from typing import Iterable

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan
from models.roster_model import RosterMember, normalize_roster_role
from services.raid_plan_saved_build_resolution_service import (
    RaidPlanSavedBuildResolutionService,
)


_ALLOWED_LOCKS = frozenset(
    {
        "player",
        "character",
        "class",
        "role",
        "build",
        "gear",
        "skills",
        "mundus",
        "assignments",
    }
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _clean(value).casefold()


def _team_names(member: RosterMember) -> set[str]:
    return {
        _key(value)
        for value in str(getattr(member, "Team", "") or "").split(",")
        if _clean(value)
    }


@dataclass(frozen=True)
class Phase125RaidPlanWorkflowAudit:
    plan_id: str
    plan_name: str
    team_name: str
    chair_count: int
    assigned_player_count: int
    recruit_count: int
    selected_build_count: int
    resolved_build_count: int
    unresolved_chair_count: int
    team_identity_preserved: bool
    chair_identity_preserved: bool
    player_identity_preserved: bool
    recruit_state_preserved: bool
    character_identity_preserved: bool
    build_identity_preserved: bool
    class_constraints_preserved: bool
    role_constraints_preserved: bool
    gear_constraints_preserved: bool
    provider_assignment_preserved: bool
    unresolved_state_preserved: bool
    problems: tuple[str, ...]
    boundaries: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.problems


class Phase125RaidPlanWorkflowAuditService:
    """Verify the current canonical Phase 12.5 planning handoff without mutation."""

    def __init__(
        self,
        resolver: RaidPlanSavedBuildResolutionService | None = None,
    ) -> None:
        self._resolver = resolver or RaidPlanSavedBuildResolutionService()

    @staticmethod
    def _find_roster_member(
        members: tuple[RosterMember, ...],
        raid_member,
    ) -> RosterMember | None:
        if raid_member.roster_member_id is not None:
            matches = tuple(
                member
                for member in members
                if getattr(member, "Id", None) == raid_member.roster_member_id
            )
            return matches[0] if len(matches) == 1 else None

        if raid_member.player_id:
            matches = tuple(
                member
                for member in members
                if _key(getattr(member, "CanonicalPlayerId", "")) == _key(raid_member.player_id)
            )
            if len(matches) == 1:
                return matches[0]

        if raid_member.character_id:
            matches = tuple(
                member
                for member in members
                if _key(getattr(member, "CanonicalCharacterId", "")) == _key(raid_member.character_id)
            )
            if len(matches) == 1:
                return matches[0]

        wanted_player = _key(raid_member.gamertag)
        wanted_character = _key(raid_member.character_name)
        matches = []
        for member in members:
            if wanted_player and _key(getattr(member, "PlayerName", "")) != wanted_player:
                continue
            if wanted_character and _key(getattr(member, "CharacterName", "")) != wanted_character:
                continue
            if wanted_player or wanted_character:
                matches.append(member)
        return matches[0] if len(matches) == 1 else None

    def audit(
        self,
        *,
        raid_plan: RaidPlan,
        saved_builds: Iterable[PlayerBuild],
        roster_members: Iterable[RosterMember] = (),
    ) -> Phase125RaidPlanWorkflowAudit:
        if not isinstance(raid_plan, RaidPlan):
            raise TypeError("Phase 12.5 workflow audit requires RaidPlan")

        saved = tuple(build for build in saved_builds if isinstance(build, PlayerBuild))
        roster = tuple(member for member in roster_members if isinstance(member, RosterMember))
        problems: list[str] = []
        boundaries: list[str] = []

        seen_seats: set[str] = set()
        assigned_player_count = 0
        recruit_count = 0
        selected_build_count = 0
        resolved_build_count = 0
        unresolved_chair_count = 0

        team_ok = True
        chair_ok = True
        player_ok = True
        recruit_ok = True
        character_ok = True
        build_ok = True
        class_ok = True
        role_ok = True
        gear_ok = True
        assignment_ok = True
        unresolved_ok = True

        team_key = _key(raid_plan.team_name)

        for member in raid_plan.members:
            seat = _clean(member.seat_id)
            seat_key = seat.casefold()
            if not seat or seat_key in seen_seats:
                chair_ok = False
                problems.append(f"Duplicate or empty Raid Plan chair identity: {seat or '<empty>'}")
                continue
            seen_seats.add(seat_key)

            invalid_locks = tuple(
                value
                for value in member.comp_locked_fields
                if _key(value) not in _ALLOWED_LOCKS
            )
            if invalid_locks:
                problems.append(
                    f"{seat}: unknown Comp lock field(s): {', '.join(invalid_locks)}"
                )

            has_player = bool(
                _clean(member.gamertag)
                or _clean(member.player_id)
                or member.roster_member_id is not None
            )
            if not has_player:
                recruit_count += 1
                if member.selected_build_id:
                    recruit_ok = False
                    problems.append(
                        f"{seat}: recruit/open chair carries stable selected_build_id "
                        f"{member.selected_build_id!r} without an assigned player."
                    )
                if member.character_id:
                    recruit_ok = False
                    problems.append(
                        f"{seat}: recruit/open chair carries character_id "
                        f"{member.character_id!r} without an assigned player."
                    )
                boundaries.append(
                    f"{seat}: recruit/open chair remains explicit; planned class/gear/skills "
                    "are requirements, not a fabricated saved player or Build."
                )
            else:
                assigned_player_count += 1
                roster_member = self._find_roster_member(roster, member)
                if roster and roster_member is None:
                    player_ok = False
                    problems.append(
                        f"{seat}: assigned player/character identity does not resolve "
                        "to exactly one Roster member."
                    )
                elif roster_member is not None:
                    if member.player_id and _key(roster_member.CanonicalPlayerId) != _key(member.player_id):
                        player_ok = False
                        problems.append(f"{seat}: canonical player identity drifted.")
                    if member.character_id and _key(roster_member.CanonicalCharacterId) != _key(member.character_id):
                        character_ok = False
                        problems.append(f"{seat}: canonical character identity drifted.")
                    if team_key and team_key not in _team_names(roster_member):
                        team_ok = False
                        problems.append(
                            f"{seat}: assigned Roster member is no longer on team "
                            f"{raid_plan.team_name!r}."
                        )

            if member.selected_build_id or member.selected_build_name:
                selected_build_count += 1
                resolution = self._resolver.resolve(
                    raid_plan=raid_plan,
                    seat_id=seat,
                    saved_builds=saved,
                )
                if not resolution.resolved or resolution.build is None:
                    build_ok = False
                    problems.extend(f"{seat}: {value}" for value in resolution.unresolved)
                else:
                    resolved_build_count += 1
                    build = resolution.build
                    if member.player_id and _key(build.PlayerId) != _key(member.player_id):
                        player_ok = False
                        problems.append(f"{seat}: selected Build belongs to a different player_id.")
                    if member.character_id and _key(build.CharacterId) != _key(member.character_id):
                        character_ok = False
                        problems.append(f"{seat}: selected Build belongs to a different character_id.")
                    if member.eso_class and _key(member.eso_class) != _key(build.EsoClass):
                        class_ok = False
                        problems.append(
                            f"{seat}: class constraint drifted: plan={member.eso_class!r}, "
                            f"build={build.EsoClass!r}."
                        )
                    plan_role = normalize_roster_role(member.role)
                    build_role = normalize_roster_role(build.Role)
                    if plan_role and build_role and _key(plan_role) != _key(build_role):
                        role_ok = False
                        problems.append(
                            f"{seat}: role constraint drifted: plan={plan_role!r}, "
                            f"build={build_role!r}."
                        )

            if "gear" in member.comp_locked_fields and not member.planned_gear_sets and not member.build_selected:
                gear_ok = False
                problems.append(
                    f"{seat}: gear is locked but neither planned gear nor a selected Build "
                    "exists to define the locked state."
                )

            if (
                member.primary_assignment
                or member.secondary_assignment
                or member.assignment_source
                or member.utility_assignments
            ):
                if not (
                    member.primary_assignment
                    or member.secondary_assignment
                    or member.utility_assignments
                ):
                    assignment_ok = False
                    problems.append(
                        f"{seat}: assignment_source exists without an owned buff/debuff "
                        "or utility assignment."
                    )

            unresolved_markers = [
                value
                for value in (
                    member.notes,
                    member.build_source_kind if _key(member.build_source_kind) == "unresolved" else None,
                )
                if value and "unresolved" in _key(value)
            ]
            if unresolved_markers:
                unresolved_chair_count += 1
                boundaries.append(
                    f"{seat}: unresolved planning evidence remains explicit and is not "
                    "converted into a complete Build or encounter-safe claim."
                )

            if member.build_source_kind and _key(member.build_source_kind) != "saved_build":
                if not (member.build_source_name or member.build_source_url or member.candidate_id):
                    unresolved_ok = False
                    problems.append(
                        f"{seat}: non-saved build source kind {member.build_source_kind!r} "
                        "lost its structured provenance."
                    )
                if member.selected_build_id:
                    problems.append(
                        f"{seat}: non-saved candidate evidence is paired with a stable "
                        "selected_build_id; draft/review provenance is ambiguous."
                    )

        if raid_plan.team_name and not roster:
            boundaries.append(
                "Roster membership was not supplied; team-membership integrity could not "
                "be independently rechecked."
            )
        if not saved:
            boundaries.append(
                "Saved Build library was empty; selected Build identities can only remain "
                "explicitly unresolved."
            )

        boundaries.append(
            "Encounter compliance, temporal uptime, rotation execution, sustain under "
            "rotation, and combat outcome remain later-phase responsibilities."
        )

        return Phase125RaidPlanWorkflowAudit(
            plan_id=raid_plan.plan_id,
            plan_name=raid_plan.name,
            team_name=raid_plan.team_name or "",
            chair_count=len(raid_plan.members),
            assigned_player_count=assigned_player_count,
            recruit_count=recruit_count,
            selected_build_count=selected_build_count,
            resolved_build_count=resolved_build_count,
            unresolved_chair_count=unresolved_chair_count,
            team_identity_preserved=team_ok,
            chair_identity_preserved=chair_ok,
            player_identity_preserved=player_ok,
            recruit_state_preserved=recruit_ok,
            character_identity_preserved=character_ok,
            build_identity_preserved=build_ok,
            class_constraints_preserved=class_ok,
            role_constraints_preserved=role_ok,
            gear_constraints_preserved=gear_ok,
            provider_assignment_preserved=assignment_ok,
            unresolved_state_preserved=unresolved_ok,
            problems=tuple(dict.fromkeys(problems)),
            boundaries=tuple(dict.fromkeys(boundaries)),
        )


__all__ = [
    "Phase125RaidPlanWorkflowAudit",
    "Phase125RaidPlanWorkflowAuditService",
]
