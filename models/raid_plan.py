from __future__ import annotations

"""Planning-layer ownership contracts for one team in one trial.

Raid plans own raid decisions. They do not own reusable player, character, or saved-build
identity. A member may intentionally be incomplete while the raid lead is still assembling
the group: gamertag can be known before character, class, role, or build selection.

This module is deliberately persistence-neutral. Existing roster/team/assignment services
remain authoritative until a later migration explicitly adopts RaidPlan persistence.
"""

from dataclasses import dataclass, field, replace


_ALLOWED_STATUSES = frozenset({"planning", "active", "archived"})


def _clean(value: object) -> str:
    return str(value or "").strip()


def _optional(value: object) -> str | None:
    text = _clean(value)
    return text or None


@dataclass(frozen=True)
class RaidPlanMember:
    """One chair in a raid plan, allowed to remain partially specified."""

    seat_id: str
    gamertag: str
    roster_member_id: int | None = None
    character_id: str | None = None
    character_name: str | None = None
    role: str | None = None
    eso_class: str | None = None
    selected_build_name: str | None = None
    primary_assignment: str | None = None
    secondary_assignment: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        seat_id = _clean(self.seat_id)
        gamertag = _clean(self.gamertag)
        if not seat_id:
            raise ValueError("raid plan member seat_id must be non-empty")
        if not gamertag:
            raise ValueError("raid plan member gamertag must be non-empty")
        object.__setattr__(self, "seat_id", seat_id)
        object.__setattr__(self, "gamertag", gamertag)
        if self.roster_member_id is not None:
            roster_member_id = int(self.roster_member_id)
            if roster_member_id <= 0:
                raise ValueError("roster_member_id must be positive when supplied")
            object.__setattr__(self, "roster_member_id", roster_member_id)
        for name in (
            "character_id",
            "character_name",
            "role",
            "eso_class",
            "selected_build_name",
            "primary_assignment",
            "secondary_assignment",
            "notes",
        ):
            object.__setattr__(self, name, _optional(getattr(self, name)))

    @property
    def build_selected(self) -> bool:
        return self.selected_build_name is not None

    @property
    def character_selected(self) -> bool:
        return self.character_id is not None or self.character_name is not None

    def with_selection(self, **changes) -> "RaidPlanMember":
        """Return a revised chair without mutating reusable identity elsewhere."""
        return replace(self, **changes)


@dataclass(frozen=True)
class RaidPlan:
    """One mutable-in-concept raid plan represented as an immutable domain snapshot.

    ``team_name`` is optional because ad-hoc friend groups are legal. A persistent Team
    may seed a plan, but the plan remains the owner of trial-specific selections and
    assignments.
    """

    plan_id: str
    trial_id: str
    name: str
    team_name: str | None = None
    difficulty: str | None = None
    status: str = "planning"
    members: tuple[RaidPlanMember, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        plan_id = _clean(self.plan_id)
        trial_id = _clean(self.trial_id)
        name = _clean(self.name)
        status = _clean(self.status).casefold()
        if not plan_id:
            raise ValueError("raid plan plan_id must be non-empty")
        if not trial_id:
            raise ValueError("raid plan trial_id must be non-empty")
        if not name:
            raise ValueError("raid plan name must be non-empty")
        if status not in _ALLOWED_STATUSES:
            raise ValueError("raid plan status must be planning, active, or archived")

        members = tuple(self.members)
        seat_ids = [member.seat_id.casefold() for member in members]
        if len(seat_ids) != len(set(seat_ids)):
            raise ValueError("raid plan seat_id values must be unique")

        object.__setattr__(self, "plan_id", plan_id)
        object.__setattr__(self, "trial_id", trial_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "team_name", _optional(self.team_name))
        object.__setattr__(self, "difficulty", _optional(self.difficulty))
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "members", members)

    def member(self, seat_id: str) -> RaidPlanMember | None:
        key = _clean(seat_id).casefold()
        return next(
            (member for member in self.members if member.seat_id.casefold() == key),
            None,
        )

    def with_member(self, member: RaidPlanMember) -> "RaidPlan":
        """Add or replace one chair by seat identity."""
        if not isinstance(member, RaidPlanMember):
            raise TypeError("raid plan member must be a RaidPlanMember")
        key = member.seat_id.casefold()
        replaced = False
        updated: list[RaidPlanMember] = []
        for existing in self.members:
            if existing.seat_id.casefold() == key:
                updated.append(member)
                replaced = True
            else:
                updated.append(existing)
        if not replaced:
            updated.append(member)
        return replace(self, members=tuple(updated))

    def without_member(self, seat_id: str) -> "RaidPlan":
        key = _clean(seat_id).casefold()
        return replace(
            self,
            members=tuple(
                member for member in self.members if member.seat_id.casefold() != key
            ),
        )


__all__ = ["RaidPlan", "RaidPlanMember"]
