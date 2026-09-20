from __future__ import annotations

from dataclasses import dataclass, asdict


ROLES = [
    "",
    "Tank",
    "Healer",
    "DD",
]


def normalize_roster_role(value: object) -> str:
    """Return the canonical user-facing roster role label."""
    raw = " ".join(str(value or "").strip().split())
    folded = raw.casefold().replace("_", " ")
    if folded in {"dd", "dps", "damage", "damage dealer"}:
        return "DD"
    if folded in {"support dd", "support dps", "support damage", "support damage dealer"}:
        return "DD"
    if folded == "tank":
        return "Tank"
    if folded in {"healer", "heal", "heals", "healing"}:
        return "Healer"
    return raw

STATUSES = [
    "Active",
    "Sub",
    "Inactive",
    "Archived",
]

ESO_CLASSES = [
    "",
    "Dragonknight",
    "Sorcerer",
    "Nightblade",
    "Templar",
    "Warden",
    "Necromancer",
    "Arcanist",
]


@dataclass
class RosterMember:
    Id: int | None = None
    PlayerName: str = ""
    CharacterName: str = ""
    EsoClass: str = ""
    PrimaryRole: str = ""
    SecondaryRole: str = ""
    Status: str = "Active"
    Team: str = ""
    CanonicalPlayerId: str = ""
    CanonicalCharacterId: str = ""
    DiscordName: str = ""
    YouTube: str = ""
    Twitch: str = ""
    PersonnelNotes: str = ""

    def __post_init__(self) -> None:
        self.PrimaryRole = normalize_roster_role(self.PrimaryRole)
        self.SecondaryRole = normalize_roster_role(self.SecondaryRole)

    def to_dict(self) -> dict:
        return asdict(self)
