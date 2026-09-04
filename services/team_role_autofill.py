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
    build_player_keys: tuple[object, ...] | None = None,
) -> tuple[TeamAutofillAssignment, ...]:
    """Assign compatible saved builds while consuming each real player once.

    ``build_player_keys`` is optional for backwards compatibility with callers that
    truly operate on independent build templates. Team/roster callers should pass a
    stable player identity for each build so a person with twelve saved loadouts does
    not become twelve raid members, a feat even ESO has declined to support.
    """

    if build_player_keys is not None and len(build_player_keys) != len(build_roles):
        raise ValueError("build_player_keys must align one-to-one with build_roles")

    unused = set(range(len(build_roles)))
    normalized = tuple(normalize_team_role(role) for role in build_roles)
    player_keys = (
        tuple(
            str(value or "").strip().casefold() or f"build:{index}"
            for index, value in enumerate(build_player_keys)
        )
        if build_player_keys is not None
        else tuple(f"build:{index}" for index in range(len(build_roles)))
    )
    used_players: set[str] = set()
    assignments: list[TeamAutofillAssignment] = []

    for slot_label in slot_labels:
        required = slot_role_family(slot_label)
        selected: int | None = None
        for index, role in enumerate(normalized):
            if (
                index in unused
                and role == required
                and player_keys[index] not in used_players
            ):
                selected = index
                unused.remove(index)
                used_players.add(player_keys[index])
                break
        assignments.append(
            TeamAutofillAssignment(slot_label=slot_label, build_index=selected)
        )

    return tuple(assignments)
