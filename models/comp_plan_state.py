from __future__ import annotations

"""Canonical working state for the Phase 14 Comp Maker rebuild.

The UI, adviser, Team Health, Auto-Fill, and Save flow must all read/write this
single model rather than maintaining parallel dictionaries or presentation text.
"""

from dataclasses import dataclass, field, replace


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _optional(value: object) -> str | None:
    text = _clean(value)
    return text or None


_ALLOWED_LOCK_FIELDS = frozenset(
    {
        "player",
        "character",
        "role",
        "class",
        "build",
        "gear",
        "skills",
        "mundus",
        "primary_assignment",
        "secondary_assignment",
        "utility_assignments",
    }
)


@dataclass(frozen=True)
class CompChairState:
    seat_id: str
    player_name: str = ""
    roster_member_id: int | None = None
    player_id: str | None = None
    character_id: str | None = None
    character_name: str | None = None
    role: str | None = None
    eso_class: str | None = None
    selected_build_id: str | None = None
    selected_build_name: str | None = None
    build_source_kind: str | None = None
    build_source_name: str | None = None
    build_source_url: str | None = None
    candidate_id: str | None = None
    planned_gear_sets: tuple[str, ...] = field(default_factory=tuple)
    planned_skills: tuple[str, ...] = field(default_factory=tuple)
    planned_mundus: str | None = None
    primary_assignment: str | None = None
    secondary_assignment: str | None = None
    utility_assignments: tuple[str, ...] = field(default_factory=tuple)
    locked_fields: tuple[str, ...] = field(default_factory=tuple)
    notes: str | None = None

    def __post_init__(self) -> None:
        seat = _clean(self.seat_id)
        if not seat:
            raise ValueError("Comp chair seat_id must be non-empty")
        object.__setattr__(self, "seat_id", seat)
        object.__setattr__(self, "player_name", _clean(self.player_name))
        if self.roster_member_id is not None:
            value = int(self.roster_member_id)
            if value <= 0:
                raise ValueError("roster_member_id must be positive when supplied")
            object.__setattr__(self, "roster_member_id", value)

        for name in (
            "player_id",
            "character_id",
            "character_name",
            "role",
            "eso_class",
            "selected_build_id",
            "selected_build_name",
            "build_source_kind",
            "build_source_name",
            "build_source_url",
            "candidate_id",
            "planned_mundus",
            "primary_assignment",
            "secondary_assignment",
            "notes",
        ):
            object.__setattr__(self, name, _optional(getattr(self, name)))

        for name in ("planned_gear_sets", "planned_skills", "utility_assignments"):
            values = tuple(
                dict.fromkeys(
                    _clean(value)
                    for value in getattr(self, name)
                    if _clean(value)
                )
            )
            object.__setattr__(self, name, values)

        locks = tuple(
            dict.fromkeys(
                _clean(value).casefold()
                for value in self.locked_fields
                if _clean(value)
            )
        )
        unknown = tuple(value for value in locks if value not in _ALLOWED_LOCK_FIELDS)
        if unknown:
            raise ValueError(
                "unknown Comp chair lock field(s): " + ", ".join(unknown)
            )
        object.__setattr__(self, "locked_fields", locks)

    def is_locked(self, field_name: str) -> bool:
        return _clean(field_name).casefold() in self.locked_fields

    def with_changes(self, **changes) -> "CompChairState":
        return replace(self, **changes)

    @property
    def is_open_player(self) -> bool:
        return not self.player_name or self.player_name.casefold().startswith("recruit")

    @property
    def has_planned_build(self) -> bool:
        return bool(
            self.selected_build_id
            or self.selected_build_name
            or self.planned_gear_sets
            or self.planned_skills
            or self.planned_mundus
        )


@dataclass(frozen=True)
class CompPlanState:
    raid_plan_id: str
    raid_plan_name: str
    trial_id: str
    team_name: str | None = None
    difficulty: str | None = None
    status: str = "planning"
    plan_note: str | None = None
    achievement_goal: str | None = None
    chairs: tuple[CompChairState, ...] = field(default_factory=tuple)
    dirty: bool = False

    def __post_init__(self) -> None:
        plan_id = _clean(self.raid_plan_id)
        plan_name = _clean(self.raid_plan_name)
        trial_id = _clean(self.trial_id)
        if not plan_id:
            raise ValueError("Comp plan raid_plan_id must be non-empty")
        if not plan_name:
            raise ValueError("Comp plan raid_plan_name must be non-empty")
        if not trial_id:
            raise ValueError("Comp plan trial_id must be non-empty")
        chairs = tuple(self.chairs)
        keys = [chair.seat_id.casefold() for chair in chairs]
        if len(keys) != len(set(keys)):
            raise ValueError("Comp plan chair seat_id values must be unique")
        object.__setattr__(self, "raid_plan_id", plan_id)
        object.__setattr__(self, "raid_plan_name", plan_name)
        object.__setattr__(self, "trial_id", trial_id)
        object.__setattr__(self, "team_name", _optional(self.team_name))
        object.__setattr__(self, "difficulty", _optional(self.difficulty))
        object.__setattr__(self, "plan_note", _optional(self.plan_note))
        object.__setattr__(self, "achievement_goal", _optional(self.achievement_goal))
        object.__setattr__(self, "chairs", chairs)
        object.__setattr__(self, "dirty", bool(self.dirty))

    def chair(self, seat_id: str) -> CompChairState | None:
        key = _clean(seat_id).casefold()
        return next(
            (chair for chair in self.chairs if chair.seat_id.casefold() == key),
            None,
        )

    def with_chair(self, chair: CompChairState) -> "CompPlanState":
        key = chair.seat_id.casefold()
        updated: list[CompChairState] = []
        replaced = False
        for existing in self.chairs:
            if existing.seat_id.casefold() == key:
                updated.append(chair)
                replaced = True
            else:
                updated.append(existing)
        if not replaced:
            updated.append(chair)
        return replace(self, chairs=tuple(updated), dirty=True)

    def mark_saved(self) -> "CompPlanState":
        return replace(self, dirty=False)


__all__ = [
    "CompChairState",
    "CompPlanState",
]
