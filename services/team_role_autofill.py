from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamAutofillAssignment:
    slot_label: str
    build_index: int | None


def normalize_team_role(value: object) -> str | None:
    """Map explicit saved-build role labels onto Team Builder slot families.

    Unknown or blank roles remain unresolved rather than being silently assigned
    to an incompatible slot.
    """

    role = str(value or "").strip().casefold()
    if role in {"tank", "main tank", "off tank", "mt", "ot"}:
        return "tank"
    if role in {"healer", "heal"}:
        return "healer"
    if role in {
        "dd",
        "dps",
        "damage",
        "damage dealer",
        "support dd",
        "support dps",
    }:
        return "dd"
    return None


def slot_role_family(slot_label: str) -> str:
    slot = str(slot_label or "").strip().casefold()
    if "tank" in slot:
        return "tank"
    if "healer" in slot:
        return "healer"
    if slot.startswith("dd"):
        return "dd"
    raise ValueError(f"unsupported Team Builder role slot: {slot_label!r}")


def build_role_compatible_autofill(
    *,
    slot_labels: tuple[str, ...],
    build_roles: tuple[object, ...],
) -> tuple[TeamAutofillAssignment, ...]:
    """Assign each saved build at most once to the first compatible role slot.

    Saved-build ordering remains deterministic within a role family. A healer is
    never used to fill a tank or DD slot, a tank is never used to fill healer or
    DD, and unknown roles remain unassigned.
    """

    unused = set(range(len(build_roles)))
    normalized = tuple(normalize_team_role(role) for role in build_roles)
    assignments: list[TeamAutofillAssignment] = []

    for slot_label in slot_labels:
        required = slot_role_family(slot_label)
        selected: int | None = None
        for index, role in enumerate(normalized):
            if index in unused and role == required:
                selected = index
                unused.remove(index)
                break
        assignments.append(
            TeamAutofillAssignment(slot_label=slot_label, build_index=selected)
        )

    return tuple(assignments)
