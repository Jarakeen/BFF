# models/build_model.py
#
# Data model for a single raid member's character build,
# used by the Builds page (ui/builds_page.py).
#
# A PlayerBuild holds the "always true" loadout for a
# character -- identity, race/class, gear, CP, and a
# default skill/food/potion setup -- plus a list of
# BossLoadout overrides for fights in a trial where the
# member runs something different (e.g. a burst DPS skill
# swap on a single-target boss, or a different food for an
# execute phase).

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


ARMOR_SLOTS: list[str] = [
    "Head",
    "Shoulders",
    "Chest",
    "Hands",
    "Waist",
    "Legs",
    "Feet",
]

ARMOR_TRAITS: list[str] = [
    "",
    "Divines",
    "Reinforced",
    "Well-Fitted",
    "Impenetrable",
    "Infused",
    "Training",
    "Nirnhoned",
    "Sturdy",
    "Prosperous",
]

WEAPON_TRAITS: list[str] = [
    "",
    "Precise",
    "Charged",
    "Powered",
    "Defending",
    "Training",
    "Sharpened",
    "Decisive",
    "Infused",
    "Nirnhoned",
]

JEWELRY_TRAITS: list[str] = [
    "",
    "Arcane",
    "Healthy",
    "Robust",
    "Bloodthirsty",
    "Harmony",
    "Protective",
    "Swift",
    "Triune",
    "Infused",
    "Nirnhoned",
]

BAR_SKILL_COUNT = 5


def _empty_bar() -> list[str]:
    # 5 active skills + 1 ultimate.
    return ["" for _ in range(BAR_SKILL_COUNT)] + [""]


def _empty_armor() -> dict[str, dict[str, str]]:
    return {
        slot: {
            "Set": "",
            "Trait": "",
            "Enchant": "",
            "Weight": "",
        }
        for slot in ARMOR_SLOTS
    }


@dataclass
class GearSlot:
    """A single weapon, armor, or jewelry slot."""

    Set: str = ""
    Trait: str = ""
    Enchant: str = ""
    Weight: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "GearSlot":
        data = data or {}

        return cls(
            Set=data.get("Set", ""),
            Trait=data.get("Trait", ""),
            Enchant=data.get("Enchant", ""),
            Weight=data.get("Weight", ""),
        )


@dataclass
class ChampionPointEntry:
    """One slotted Champion Point star."""

    Name: str = ""
    Points: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "ChampionPointEntry":
        data = data or {}
        return cls(
            Name=data.get("Name", ""),
            Points=data.get("Points", ""),
        )


@dataclass
class BossLoadout:
    """
    An alternate loadout for one boss in the trial.

    Anything left blank falls back to the member's default
    loadout when exported/displayed, so a member only needs
    to fill in what's actually different for that pull.
    """

    BossName: str = ""
    FrontBarSkills: list[str] = field(default_factory=_empty_bar)
    BackBarSkills: list[str] = field(default_factory=_empty_bar)
    Food: str = ""
    Potion: str = ""
    Notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "BossLoadout":
        data = dict(data or {})
        data.setdefault("FrontBarSkills", _empty_bar())
        data.setdefault("BackBarSkills", _empty_bar())
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class PlayerBuild:
    """A single raid member's character build."""

    Name: str = ""
    Gamertag: str = ""
    ImagePath: str = ""

    # Stable human-facing name for this configuration. Character identity
    # remains Name/Gamertag; multiple BuildName values may belong to one
    # character in the canonical catalog.
    BuildName: str = ""

    Race: str = ""
    EsoClass: str = ""

    Armor: dict[str, dict[str, str]] = field(default_factory=_empty_armor)

    FrontBarWeapon: GearSlot = field(default_factory=GearSlot)
    BackBarWeapon: GearSlot = field(default_factory=GearSlot)

    Necklace: GearSlot = field(default_factory=GearSlot)
    Ring1: GearSlot = field(default_factory=GearSlot)
    Ring2: GearSlot = field(default_factory=GearSlot)

    ChampionPoints: list[ChampionPointEntry] = field(default_factory=list)

    FrontBarSkills: list[str] = field(default_factory=_empty_bar)
    BackBarSkills: list[str] = field(default_factory=_empty_bar)

    Food: str = ""
    Potion: str = ""

    Notes: str = ""

    BossLoadouts: list[BossLoadout] = field(default_factory=list)

    # --------------------------------------------------
    # Serialization
    # --------------------------------------------------

    def to_dict(self) -> dict:

        return {
            "Name": self.Name,
            "Gamertag": self.Gamertag,
            "ImagePath": self.ImagePath,
            "BuildName": self.BuildName,
            "Race": self.Race,
            "EsoClass": self.EsoClass,
            "Armor": self.Armor,
            "FrontBarWeapon": self.FrontBarWeapon.to_dict(),
            "BackBarWeapon": self.BackBarWeapon.to_dict(),
            "Necklace": self.Necklace.to_dict(),
            "Ring1": self.Ring1.to_dict(),
            "Ring2": self.Ring2.to_dict(),
            "ChampionPoints": [cp.to_dict() for cp in self.ChampionPoints],
            "FrontBarSkills": self.FrontBarSkills,
            "BackBarSkills": self.BackBarSkills,
            "Food": self.Food,
            "Potion": self.Potion,
            "Notes": self.Notes,
            "BossLoadouts": [b.to_dict() for b in self.BossLoadouts],
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "PlayerBuild":

        data = dict(data or {})

        armor = _empty_armor()

        for slot, value in (data.get("Armor") or {}).items():
            if slot in armor and isinstance(value, dict):
                armor[slot] = {
                    "Set": value.get("Set", ""),
                    "Trait": value.get("Trait", ""),
                    "Enchant": value.get("Enchant", ""),
                    "Weight": value.get("Weight", ""),
                }

        return cls(
            Name=data.get("Name", ""),
            Gamertag=data.get("Gamertag", ""),
            ImagePath=data.get("ImagePath", ""),
            BuildName=data.get("BuildName", ""),
            Race=data.get("Race", ""),
            EsoClass=data.get("EsoClass", ""),
            Armor=armor,
            FrontBarWeapon=GearSlot.from_dict(data.get("FrontBarWeapon")),
            BackBarWeapon=GearSlot.from_dict(data.get("BackBarWeapon")),
            Necklace=GearSlot.from_dict(data.get("Necklace")),
            Ring1=GearSlot.from_dict(data.get("Ring1")),
            Ring2=GearSlot.from_dict(data.get("Ring2")),
            ChampionPoints=[
                ChampionPointEntry.from_dict(cp)
                for cp in data.get("ChampionPoints", [])
            ],
            FrontBarSkills=data.get("FrontBarSkills") or _empty_bar(),
            BackBarSkills=data.get("BackBarSkills") or _empty_bar(),
            Food=data.get("Food", ""),
            Potion=data.get("Potion", ""),
            Notes=data.get("Notes", ""),
            BossLoadouts=[
                BossLoadout.from_dict(b)
                for b in data.get("BossLoadouts", [])
            ],
        )

    def display_label(self, fallback: str) -> str:
        """Tab label: the character name if set, else a fallback like 'Member 3'."""

        return self.Name.strip() or fallback


@dataclass
class BuildRoster:
    """Up to 12 PlayerBuilds, one per raid team member tab."""

    Members: list[PlayerBuild] = field(default_factory=lambda: [PlayerBuild()])

    MAX_MEMBERS = 12

    def to_dict(self) -> dict:
        return {"Members": [m.to_dict() for m in self.Members]}

    @classmethod
    def from_dict(cls, data: dict | None) -> "BuildRoster":

        data = data or {}

        members = [
            PlayerBuild.from_dict(m)
            for m in data.get("Members", [])
        ]

        if not members:
            members = [PlayerBuild()]

        return cls(Members=members[: cls.MAX_MEMBERS])
