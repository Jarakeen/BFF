from __future__ import annotations

from dataclasses import dataclass, field, asdict

from models.scribing_recipe import ScribedSkillRecipe

ARMOR_SLOTS: list[str] = ["Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"]
ARMOR_TRAITS: list[str] = ["", "Divines", "Reinforced", "Well-Fitted", "Impenetrable", "Infused", "Training", "Nirnhoned", "Sturdy", "Invigorating"]
WEAPON_TRAITS: list[str] = ["", "Precise", "Charged", "Powered", "Defending", "Training", "Sharpened", "Decisive", "Infused", "Nirnhoned"]
JEWELRY_TRAITS: list[str] = ["", "Arcane", "Healthy", "Robust", "Bloodthirsty", "Harmony", "Protective", "Swift", "Triune", "Infused", "Nirnhoned"]
MUNDUS_CHOICES: list[str] = [
    "",
    "The Apprentice",
    "The Atronach",
    "The Lady",
    "The Lord",
    "The Lover",
    "The Mage",
    "The Ritual",
    "The Serpent",
    "The Shadow",
    "The Steed",
    "The Thief",
    "The Tower",
    "The Warrior",
]
WEAPON_TYPES: list[str] = [
    "",
    "Bow",
    "Inferno Staff",
    "Lightning Staff",
    "Ice Staff",
    "Restoration Staff",
    "Two-Handed",
    "Sword",
    "Axe",
    "Mace",
    "Dagger",
    "Shield",
    # Legacy aggregate bar types retained for saved-build compatibility.
    "One Hand and Shield",
    "Dual Wield",
]
BAR_SKILL_COUNT = 5
MAX_ATTRIBUTE_POINTS = 64


def _empty_bar() -> list[str]:
    return [""] * (BAR_SKILL_COUNT + 1)


def _empty_armor() -> dict[str, dict[str, str]]:
    return {slot: {"Set": "", "Set2": "", "Quality": "", "Trait": "", "Enchant": "", "EnchantTier": "", "Level": "", "Weight": ""} for slot in ARMOR_SLOTS}


def _int_value(value, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


@dataclass
class GearSlot:
    Set: str = ""
    Trait: str = ""
    Enchant: str = ""
    Weight: str = ""
    Set2: str = ""
    Quality: str = ""
    EnchantTier: str = ""
    Level: str = ""
    WeaponType: str = ""

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
            WeaponType=str(data.get("WeaponType", "") or ""),
        )

    @property
    def is_empty(self) -> bool:
        return not any(
            str(value or "").strip()
            for value in (
                self.Set,
                self.Set2,
                self.Trait,
                self.Enchant,
                self.Weight,
                self.Quality,
                self.EnchantTier,
                self.Level,
                self.WeaponType,
            )
        )


@dataclass
class ChampionPointEntry:
    Name: str = ""
    Points: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "ChampionPointEntry":
        data = data or {}
        return cls(Name=str(data.get("Name", "") or ""), Points=str(data.get("Points", "") or ""))


@dataclass
class BossLoadout:
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
            FrontBarSkills=list(data.get("FrontBarSkills") or _empty_bar()),
            BackBarSkills=list(data.get("BackBarSkills") or _empty_bar()),
            Food=str(data.get("Food", "") or ""),
            Potion=str(data.get("Potion", "") or ""),
            Notes=str(data.get("Notes", "") or ""),
        )


@dataclass
class PlayerBuild:
    """A single raid member's character build."""
    Name: str = ""
    Gamertag: str = ""
    BuildName: str = ""
    ImagePath: str = ""
    Race: str = ""
    EsoClass: str = ""
    Role: str = ""
    Alliance: str = ""
    Mundus: str = ""
    Vampire: bool = False
    Werewolf: bool = False
    AttributeHealth: int = 0
    AttributeMagicka: int = 0
    AttributeStamina: int = 0

    Armor: dict[str, dict[str, str]] = field(default_factory=_empty_armor)
    # FrontBarWeapon / BackBarWeapon remain the primary/main-hand fields so
    # existing saved builds continue to load unchanged. Explicit offhands are
    # additive and empty for legacy two-slot weapon representations.
    FrontBarWeapon: GearSlot = field(default_factory=GearSlot)
    FrontBarOffHand: GearSlot = field(default_factory=GearSlot)
    BackBarWeapon: GearSlot = field(default_factory=GearSlot)
    BackBarOffHand: GearSlot = field(default_factory=GearSlot)
    Necklace: GearSlot = field(default_factory=GearSlot)
    Ring1: GearSlot = field(default_factory=GearSlot)
    Ring2: GearSlot = field(default_factory=GearSlot)
    ChampionPoints: list[ChampionPointEntry] = field(default_factory=list)
    FrontBarSkills: list[str] = field(default_factory=_empty_bar)
    BackBarSkills: list[str] = field(default_factory=_empty_bar)
    # ScribedSkills remains the compatibility mirror used by older builds/UI.
    ScribedSkills: list[str] = field(default_factory=list)
    # Complete recipe configuration belongs in the core model so CLI services
    # see the same evidence the desktop editor persists.
    ScribedSkillRecipes: list[ScribedSkillRecipe] = field(default_factory=list)
    Food: str = ""
    Potion: str = ""
    Notes: str = ""
    BossLoadouts: list[BossLoadout] = field(default_factory=list)

    @property
    def attribute_points_total(self) -> int:
        return self.AttributeHealth + self.AttributeMagicka + self.AttributeStamina

    def active_weapon_slots(self, active_bar: str = "front") -> tuple[GearSlot, GearSlot]:
        if str(active_bar or "front").casefold() == "back":
            return self.BackBarWeapon, self.BackBarOffHand
        return self.FrontBarWeapon, self.FrontBarOffHand

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.Vampire and self.Werewolf:
            errors.append("A character cannot be both Vampire and Werewolf.")
        if any(value < 0 for value in (self.AttributeHealth, self.AttributeMagicka, self.AttributeStamina)):
            errors.append("Attribute points cannot be negative.")
        if self.attribute_points_total > MAX_ATTRIBUTE_POINTS:
            errors.append(f"Attribute points cannot exceed {MAX_ATTRIBUTE_POINTS}.")
        return errors

    def to_dict(self) -> dict:
        recipes = [recipe for recipe in self.ScribedSkillRecipes if recipe.ResultName.strip()]
        scribed_names = [recipe.ResultName.strip() for recipe in recipes] or list(self.ScribedSkills)
        return {
            "Name": self.Name, "Gamertag": self.Gamertag, "BuildName": self.BuildName,
            "ImagePath": self.ImagePath, "Race": self.Race, "EsoClass": self.EsoClass,
            "Role": self.Role, "Alliance": self.Alliance, "Mundus": self.Mundus,
            "Vampire": self.Vampire, "Werewolf": self.Werewolf,
            "AttributeHealth": self.AttributeHealth, "AttributeMagicka": self.AttributeMagicka,
            "AttributeStamina": self.AttributeStamina,
            "Armor": {slot: dict(values) for slot, values in self.Armor.items()},
            "FrontBarWeapon": self.FrontBarWeapon.to_dict(), "FrontBarOffHand": self.FrontBarOffHand.to_dict(),
            "BackBarWeapon": self.BackBarWeapon.to_dict(), "BackBarOffHand": self.BackBarOffHand.to_dict(),
            "Necklace": self.Necklace.to_dict(), "Ring1": self.Ring1.to_dict(), "Ring2": self.Ring2.to_dict(),
            "ChampionPoints": [cp.to_dict() for cp in self.ChampionPoints],
            "FrontBarSkills": list(self.FrontBarSkills), "BackBarSkills": list(self.BackBarSkills),
            "ScribedSkills": scribed_names,
            "Food": self.Food, "Potion": self.Potion, "Notes": self.Notes,
            "BossLoadouts": [b.to_dict() for b in self.BossLoadouts],
            "ScribedSkillRecipes": [recipe.to_dict() for recipe in recipes],
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "PlayerBuild":
        data = dict(data or {})
        armor = _empty_armor()
        for slot, value in (data.get("Armor") or {}).items():
            if slot in armor and isinstance(value, dict):
                armor[slot] = {str(key): str(item or "") for key, item in value.items()}
        scribed_names = [str(name).strip() for name in (data.get("ScribedSkills") or []) if str(name).strip()]
        raw_recipes = data.get("ScribedSkillRecipes")
        if raw_recipes is None:
            recipes = [ScribedSkillRecipe.from_legacy_name(name) for name in scribed_names]
        else:
            recipes = [
                ScribedSkillRecipe.from_dict(value)
                for value in raw_recipes
                if isinstance(value, dict) and ScribedSkillRecipe.from_dict(value).ResultName
            ]
        return cls(
            Name=str(data.get("Name", "") or ""), Gamertag=str(data.get("Gamertag", "") or ""),
            BuildName=str(data.get("BuildName", "") or ""), ImagePath=str(data.get("ImagePath", "") or ""),
            Race=str(data.get("Race", "") or ""), EsoClass=str(data.get("EsoClass", "") or ""),
            Role=str(data.get("Role", "") or ""), Alliance=str(data.get("Alliance", "") or ""),
            Mundus=str(data.get("Mundus", "") or ""),
            Vampire=bool(data.get("Vampire", False)), Werewolf=bool(data.get("Werewolf", False)),
            AttributeHealth=_int_value(data.get("AttributeHealth", 0)),
            AttributeMagicka=_int_value(data.get("AttributeMagicka", 0)),
            AttributeStamina=_int_value(data.get("AttributeStamina", 0)),
            Armor=armor,
            FrontBarWeapon=GearSlot.from_dict(data.get("FrontBarWeapon")),
            FrontBarOffHand=GearSlot.from_dict(data.get("FrontBarOffHand")),
            BackBarWeapon=GearSlot.from_dict(data.get("BackBarWeapon")),
            BackBarOffHand=GearSlot.from_dict(data.get("BackBarOffHand")),
            Necklace=GearSlot.from_dict(data.get("Necklace")), Ring1=GearSlot.from_dict(data.get("Ring1")), Ring2=GearSlot.from_dict(data.get("Ring2")),
            ChampionPoints=[ChampionPointEntry.from_dict(cp) for cp in data.get("ChampionPoints", [])],
            FrontBarSkills=list(data.get("FrontBarSkills") or _empty_bar()),
            BackBarSkills=list(data.get("BackBarSkills") or _empty_bar()),
            ScribedSkills=scribed_names,
            ScribedSkillRecipes=recipes,
            Food=str(data.get("Food", "") or ""), Potion=str(data.get("Potion", "") or ""), Notes=str(data.get("Notes", "") or ""),
            BossLoadouts=[BossLoadout.from_dict(b) for b in data.get("BossLoadouts", [])],
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
        members = [PlayerBuild.from_dict(m) for m in (data or {}).get("Members", [])]
        return cls(Members=members[: cls.MAX_MEMBERS] or [PlayerBuild()])
