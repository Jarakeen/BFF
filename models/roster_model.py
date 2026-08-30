from __future__ import annotations

from dataclasses import dataclass, asdict


ROLES = [
    "",
    "Tank",
    "Healer",
    "Damage Dealer",
]

STATUSES = [
    "Active",
    "Bench",
    "Inactive",
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

    def to_dict(self) -> dict:
        return asdict(self)
