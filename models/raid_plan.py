from __future__ import annotations

"""Planning-layer ownership contracts for one team in one trial.

Raid plans own raid decisions. They do not own reusable player, character, or saved-build
identity. A member may intentionally be incomplete while the raid lead is still assembling
the group: gamertag can be known before character, class, role, or build selection.

Triggered responsibilities are planning instructions, not scheduled Rotation actions. They
record who owns a response when a reviewed runtime condition becomes true without inventing
a wall-clock timestamp. A later resolver may bind a proven runtime condition to an exact
execution time; this model deliberately does not do that itself.

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
class RaidPlanTriggeredResponsibility:
    """One seat-owned response activated by an opaque reviewed runtime condition.

    ``trigger_key`` is caller-owned condition identity. The planning model does not
    interpret it, convert it to seconds, or claim that observing the condition proves an
    exact spawn/cast timestamp. ``directive`` describes raid intent; downstream execution
    still needs a separate resolver before producing a clock-scheduled RotationAction.
    """

    responsibility_id: str
    seat_id: str
    encounter_id: str
    trigger_key: str
    directive: str
    target_key: str | None = None
    required_capability_type: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "responsibility_id",
            "seat_id",
            "encounter_id",
            "trigger_key",
            "directive",
        ):
            value = _clean(getattr(self, name))
            if not value:
                raise ValueError(
                    f"raid plan triggered responsibility {name} must be non-empty"
                )
            object.__setattr__(self, name, value)
        object.__setattr__(self, "target_key", _optional(self.target_key))
        capability = _optional(self.required_capability_type)
        object.__setattr__(
            self,
            "required_capability_type",
            capability.casefold() if capability is not None else None,
        )
        object.__setattr__(self, "source", _optional(self.source))


@dataclass(frozen=True)
class RaidPlan:
    """One mutable-in-concept raid plan represented as an immutable domain snapshot.

    ``team_name`` is optional because ad-hoc friend groups are legal. A persistent Team
    may seed a plan, but the plan remains the owner of trial-specific selections,
    assignments, and runtime-triggered responsibilities.
    """

    plan_id: str
    trial_id: str
    name: str
    team_name: str | None = None
    difficulty: str | None = None
    status: str = "planning"
    members: tuple[RaidPlanMember, ...] = field(default_factory=tuple)
    triggered_responsibilities: tuple[RaidPlanTriggeredResponsibility, ...] = field(
        default_factory=tuple
    )

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

        triggered_responsibilities = tuple(self.triggered_responsibilities)
        responsibility_ids = [
            row.responsibility_id.casefold() for row in triggered_responsibilities
        ]
        if len(responsibility_ids) != len(set(responsibility_ids)):
            raise ValueError(
                "raid plan triggered responsibility_id values must be unique"
            )
        member_seat_ids = set(seat_ids)
        for row in triggered_responsibilities:
            if row.seat_id.casefold() not in member_seat_ids:
                raise ValueError(
                    "raid plan triggered responsibility references unknown seat_id: "
                    f"{row.seat_id!r}"
                )

        object.__setattr__(self, "plan_id", plan_id)
        object.__setattr__(self, "trial_id", trial_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "team_name", _optional(self.team_name))
        object.__setattr__(self, "difficulty", _optional(self.difficulty))
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "members", members)
        object.__setattr__(
            self,
            "triggered_responsibilities",
            triggered_responsibilities,
        )

    def member(self, seat_id: str) -> RaidPlanMember | None:
        key = _clean(seat_id).casefold()
        return next(
            (member for member in self.members if member.seat_id.casefold() == key),
            None,
        )

    def triggered_for_seat(
        self,
        seat_id: str,
        *,
        encounter_id: str | None = None,
    ) -> tuple[RaidPlanTriggeredResponsibility, ...]:
        seat_key = _clean(seat_id).casefold()
        encounter_key = _optional(encounter_id)
        if encounter_key is not None:
            encounter_key = encounter_key.casefold()
        return tuple(
            row
            for row in self.triggered_responsibilities
            if row.seat_id.casefold() == seat_key
            and (
                encounter_key is None
                or row.encounter_id.casefold() == encounter_key
            )
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
        owned = tuple(
            row
            for row in self.triggered_responsibilities
            if row.seat_id.casefold() == key
        )
        if owned:
            raise ValueError(
                "cannot remove raid plan member while triggered responsibilities still reference the seat"
            )
        return replace(
            self,
            members=tuple(
                member for member in self.members if member.seat_id.casefold() != key
            ),
        )


__all__ = [
    "RaidPlan",
    "RaidPlanMember",
    "RaidPlanTriggeredResponsibility",
]
