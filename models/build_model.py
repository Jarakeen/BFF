from __future__ import annotations

from dataclasses import dataclass, field, asdict


ARMOR_SLOTS: list[str] = [
    "Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet",
]

ARMOR_TRAITS: list[str] = [
    "", "Divines", "Reinforced", "Well-Fitted", "Impenetrable",
    "Infused", "Training", "Nirnhoned", "Sturdy", "Prosperous",
]

WEAPON_TRAITS: list[str] = [
    "", "Precise", "Charged", "Powered", "Defending", "Training",
    "Sharpened", "Decisive", "Infused", "Nirnhoned",
]

JEWELRY_TRAITS: list[str] = [
    "", "Arcane", "Healthy", "Robust", "Bloodthirsty", "Harmony",
    "Protective", "Swift", "Triune", "Infused", "Nirnhoned",
]

BAR_SKILL_COUNT = 5


def _empty_bar() -> list[str]:
    return [""] * (BAR_SKILL_COUNT + 1)


def _empty_armor() -> dict[str, dict[str, str]]:
    return {
        slot: {
            "Set": "",
            "Set2": "",
            "Quality": "",
            "Trait": "",
            "Enchant": "",
            "EnchantTier": "",
            "Level": "",
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
    Set2: str = ""
    Quality: str = ""
    EnchantTier: str = ""
    Level: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "GearSlot":
        data = data or {}
        return cls(
            Set=str(data.get("Set", "") or ""),
            Trait=str(data.get("Trait", "") or ""),
            Enchant=str(data.get("Enchant", "") or ""),
            Weight=str(data.get("Weight", "") or ""),
            Set2=str(data.get("Set2", "") or ""),
            Quality=str(data.get("Quality", "") or ""),
            EnchantTier=str(data.get("EnchantTier", "") or ""),
            Level=str(data.get("Level", "") or ""),
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
            Name=str(data.get("Name", "") or ""),
            Points=str(data.get("Points", "") or ""),
        )


@dataclass
class BossLoadout:
    """An alternate loadout for one boss in the trial."""

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
        return cls(
            BossName=str(data.get("BossName", data.get("Boss", "")) or ""),
            FrontBarSkills=data.get("FrontBarSkills") or _empty_bar(),
            BackBarSkills=data.get("BackBarSkills") or _empty_bar(),
            Food=str(data.get("Food", "") or ""),
            Potion=str(data.get("Potion", "") or ""),
            Notes=str(data.get("Notes", "") or ""),
        )


@dataclass
class PlayerBuild:
    """A single raid member's character build."""

    Name: str = ""
    Gamertag: str = ""
    ImagePath: str = ""
    Race: str = ""
    EsoClass: str = ""
    Role: str = ""
    Alliance: str = ""

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

    def to_dict(self) -> dict:
        return {
            "Name": self.Name,
            "Gamertag": self.Gamertag,
            "ImagePath": self.ImagePath,
            "Race": self.Race,
            "EsoClass": self.EsoClass,
            "Role": self.Role,
            "Alliance": self.Alliance,
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

        # Preserve the stored shape of populated armor entries. Older build
        # files may not contain the newer fields. Injecting empty keys here
        # would make a save/load round-trip mutate otherwise valid user data.
        for slot, value in (data.get("Armor") or {}).items():
            if slot in armor and isinstance(value, dict):
                armor[slot] = {
                    str(key): str(item or "")
                    for key, item in value.items()
                }

        return cls(
            Name=str(data.get("Name", "") or ""),
            Gamertag=str(data.get("Gamertag", "") or ""),
            ImagePath=str(data.get("ImagePath", "") or ""),
            Race=str(data.get("Race", "") or ""),
            EsoClass=str(data.get("EsoClass", "") or ""),
            Role=str(data.get("Role", "") or ""),
            Alliance=str(data.get("Alliance", "") or ""),
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
            Food=str(data.get("Food", "") or ""),
            Potion=str(data.get("Potion", "") or ""),
            Notes=str(data.get("Notes", "") or ""),
            BossLoadouts=[
                BossLoadout.from_dict(b)
                for b in data.get("BossLoadouts", [])
            ],
        )

    def display_label(self, fallback: str) -> str:
        return self.Name.strip() or fallback


@dataclass
class BuildRoster:
    """Up to 12 PlayerBuilds."""

    Members: list[PlayerBuild] = field(default_factory=lambda: [PlayerBuild()])
    MAX_MEMBERS = 12

    def to_dict(self) -> dict:
        return {"Members": [m.to_dict() for m in self.Members]}

    @classmethod
    def from_dict(cls, data: dict | None) -> "BuildRoster":
        members = [
            PlayerBuild.from_dict(m)
            for m in (data or {}).get("Members", [])
        ]
        return cls(Members=members[: cls.MAX_MEMBERS] or [PlayerBuild()])
