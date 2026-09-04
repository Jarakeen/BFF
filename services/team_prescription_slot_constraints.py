from __future__ import annotations

from dataclasses import dataclass, replace
import unicodedata

from models.build_model import PlayerBuild
from services.team_prescription import (
    PrescribedBuildChange,
    PrescribedRoster,
    PrescriptionDimension,
)


def _identity(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "").strip())
    text = text.replace("’", "'").replace("`", "'")
    return " ".join(text.casefold().split())


def _gear_identity(value: object) -> str:
    identity = _identity(value)
    if identity.startswith("perfected "):
        return identity[len("perfected ") :]
    return identity


def build_gear_set_names(build: PlayerBuild) -> tuple[str, ...]:
    """Return the distinct named sets represented by a complete build snapshot."""

    names: list[str] = []
    seen: set[str] = set()

    def add(value: object) -> None:
        text = str(value or "").strip()
        identity = _gear_identity(text)
        if text and identity and identity not in seen:
            seen.add(identity)
            names.append(text)

    for slot in build.Armor.values():
        add(slot.get("Set"))
        add(slot.get("Set2"))
    for slot in (
        build.FrontBarWeapon,
        build.FrontBarOffHand,
        build.BackBarWeapon,
        build.BackBarOffHand,
        build.Necklace,
        build.Ring1,
        build.Ring2,
    ):
        add(slot.Set)
        add(slot.Set2)
    return tuple(names)


def parse_required_gear_sets(value: str) -> tuple[str, ...]:
    """Parse a comma/semicolon separated UI value without fuzzy set matching."""

    normalized = str(value or "").replace(";", ",")
    values: list[str] = []
    seen: set[str] = set()
    for raw in normalized.split(","):
        name = raw.strip()
        identity = _gear_identity(name)
        if not name or not identity or identity in seen:
            continue
        seen.add(identity)
        values.append(name)
    return tuple(values)


@dataclass(frozen=True)
class PrescribedSlotBuildConstraint:
    """User-required ingredients for one prescribed roster chair.

    These are hard eligibility constraints, not scoring bonuses. A higher modeled
    objective can never displace a candidate that satisfies an injected class or
    gear requirement.
    """

    slot_name: str
    required_class: str | None = None
    required_gear_sets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        slot_name = str(self.slot_name or "").strip()
        required_class = str(self.required_class or "").strip() or None
        if not slot_name:
            raise ValueError("slot build constraint requires a slot_name")
        gear_sets = parse_required_gear_sets(",".join(self.required_gear_sets))
        if not required_class and not gear_sets:
            raise ValueError("slot build constraint requires a class or gear set")
        object.__setattr__(self, "slot_name", slot_name)
        object.__setattr__(self, "required_class", required_class)
        object.__setattr__(self, "required_gear_sets", gear_sets)

    def mismatch_reasons(self, build: PlayerBuild) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.required_class and _identity(build.EsoClass) != _identity(
            self.required_class
        ):
            reasons.append(f"requires class {self.required_class}")

        available = {_gear_identity(name) for name in build_gear_set_names(build)}
        missing = tuple(
            name
            for name in self.required_gear_sets
            if _gear_identity(name) not in available
        )
        if missing:
            reasons.append("missing required gear set(s): " + ", ".join(missing))
        return tuple(reasons)

    def matches(self, build: PlayerBuild) -> bool:
        return not self.mismatch_reasons(build)

    @property
    def summary(self) -> str:
        parts: list[str] = []
        if self.required_class:
            parts.append(self.required_class)
        if self.required_gear_sets:
            parts.append(" + ".join(self.required_gear_sets))
        return " / ".join(parts)


def constraints_by_slot(
    constraints: tuple[PrescribedSlotBuildConstraint, ...],
) -> dict[str, PrescribedSlotBuildConstraint]:
    result: dict[str, PrescribedSlotBuildConstraint] = {}
    for constraint in constraints:
        key = constraint.slot_name.casefold()
        if key in result:
            raise ValueError(
                f"duplicate slot build constraint: {constraint.slot_name}"
            )
        result[key] = constraint
    return result


def project_slot_build_constraints(
    *,
    roster: PrescribedRoster,
    constraints: tuple[PrescribedSlotBuildConstraint, ...],
) -> PrescribedRoster:
    """Show user-injected ingredients on open slots without inventing a build."""

    indexed = constraints_by_slot(constraints)
    assignments = []
    for assignment in roster.assignments:
        constraint = indexed.get(assignment.slot_name.casefold())
        if constraint is None or assignment.player_name is not None:
            assignments.append(assignment)
            continue

        changes = list(assignment.changes)
        unresolved = list(assignment.unresolved)
        reason = "User-required team-slot ingredient; candidate ranking must preserve it."
        proposed = (
            (
                PrescriptionDimension.CLASS,
                constraint.required_class,
            ),
            (
                PrescriptionDimension.GEAR,
                " + ".join(constraint.required_gear_sets),
            ),
        )
        for dimension, value in proposed:
            if not value:
                continue
            if not roster.scope.allows(dimension):
                unresolved.append(
                    f"{assignment.slot_name}: required {dimension.value} conflicts "
                    "with the current optimization locks"
                )
                continue
            changes = [item for item in changes if item.dimension is not dimension]
            changes.append(
                PrescribedBuildChange(
                    dimension=dimension,
                    current_value=None,
                    prescribed_value=value,
                    reason=reason,
                )
            )
        assignments.append(
            replace(
                assignment,
                changes=tuple(changes),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )
        )
    return replace(roster, assignments=tuple(assignments))
