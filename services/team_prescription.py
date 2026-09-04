from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PrescriptionDimension(str, Enum):
    ROLE = "role"
    CLASS = "class"
    RACE = "race"
    BUILD = "build"
    GEAR = "gear"
    SKILLS = "skills"
    MORPHS = "morphs"
    CHAMPION_POINTS = "champion_points"
    MUNDUS = "mundus"
    FOOD = "food"
    POTION = "potion"


@dataclass(frozen=True)
class TeamPrescriptionScope:
    """Explicit permission boundary for one generated roster prescription."""

    dimensions: tuple[PrescriptionDimension, ...] = ()

    def __post_init__(self) -> None:
        normalized: list[PrescriptionDimension] = []
        seen: set[PrescriptionDimension] = set()
        for value in self.dimensions:
            dimension = (
                value
                if isinstance(value, PrescriptionDimension)
                else PrescriptionDimension(str(value))
            )
            if dimension in seen:
                raise ValueError(f"duplicate prescription dimension: {dimension.value}")
            seen.add(dimension)
            normalized.append(dimension)
        object.__setattr__(self, "dimensions", tuple(normalized))

    def allows(self, dimension: PrescriptionDimension) -> bool:
        return dimension in self.dimensions


@dataclass(frozen=True)
class PrescribedBuildChange:
    """One proposed change that remains separate from the saved build."""

    dimension: PrescriptionDimension
    current_value: str | None
    prescribed_value: str
    reason: str

    def __post_init__(self) -> None:
        dimension = (
            self.dimension
            if isinstance(self.dimension, PrescriptionDimension)
            else PrescriptionDimension(str(self.dimension))
        )
        prescribed = str(self.prescribed_value or "").strip()
        reason = str(self.reason or "").strip()
        current = None if self.current_value is None else str(self.current_value).strip()
        if not prescribed:
            raise ValueError("prescribed roster change requires a prescribed value")
        if not reason:
            raise ValueError("prescribed roster change requires an explicit reason")
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "prescribed_value", prescribed)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "current_value", current)


@dataclass(frozen=True)
class PrescribedRosterAssignment:
    """One player/slot recommendation in a generated team prescription."""

    slot_name: str
    player_name: str | None
    source_build_name: str | None
    prescribed_role: str
    changes: tuple[PrescribedBuildChange, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        slot = str(self.slot_name or "").strip()
        role = str(self.prescribed_role or "").strip()
        if not slot:
            raise ValueError("prescribed roster assignment requires a slot name")
        if not role:
            raise ValueError("prescribed roster assignment requires a prescribed role")
        player = None if self.player_name is None else str(self.player_name).strip() or None
        source = (
            None
            if self.source_build_name is None
            else str(self.source_build_name).strip() or None
        )
        changes = tuple(self.changes)
        dimensions = [change.dimension for change in changes]
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("prescribed roster assignment cannot change a dimension twice")
        object.__setattr__(self, "slot_name", slot)
        object.__setattr__(self, "player_name", player)
        object.__setattr__(self, "source_build_name", source)
        object.__setattr__(self, "prescribed_role", role)
        object.__setattr__(self, "changes", changes)
        object.__setattr__(
            self,
            "unresolved",
            tuple(str(value).strip() for value in self.unresolved if str(value).strip()),
        )

    def change_for(self, dimension: PrescriptionDimension) -> PrescribedBuildChange | None:
        return next((change for change in self.changes if change.dimension is dimension), None)


@dataclass(frozen=True)
class PrescribedRoster:
    """A non-destructive generated team recommendation.

    The prescription is intentionally not a BuildRoster and does not mutate
    saved builds. Acceptance/promotion into persistent roster/build storage is a
    separate operation so experimentation cannot silently overwrite canonical
    user configuration.
    """

    name: str
    goal: str
    scope: TeamPrescriptionScope
    assignments: tuple[PrescribedRosterAssignment, ...]
    assumptions: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = str(self.name or "").strip()
        goal = str(self.goal or "").strip()
        if not name:
            raise ValueError("prescribed roster requires a name")
        if not goal:
            raise ValueError("prescribed roster requires a goal")

        assignments = tuple(self.assignments)
        seen_slots: set[str] = set()
        seen_players: set[str] = set()
        for assignment in assignments:
            slot_key = assignment.slot_name.casefold()
            if slot_key in seen_slots:
                raise ValueError(f"duplicate prescribed roster slot: {assignment.slot_name}")
            seen_slots.add(slot_key)
            if assignment.player_name:
                player_key = assignment.player_name.casefold()
                if player_key in seen_players:
                    raise ValueError(
                        f"player prescribed to multiple roster slots: {assignment.player_name}"
                    )
                seen_players.add(player_key)
            for change in assignment.changes:
                if not self.scope.allows(change.dimension):
                    raise ValueError(
                        "prescribed roster change exceeds optimization scope: "
                        f"{change.dimension.value}"
                    )

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "goal", goal)
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(
            self,
            "assumptions",
            tuple(str(value).strip() for value in self.assumptions if str(value).strip()),
        )
        object.__setattr__(
            self,
            "unresolved",
            tuple(str(value).strip() for value in self.unresolved if str(value).strip()),
        )
