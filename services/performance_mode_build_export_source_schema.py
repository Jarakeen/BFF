from __future__ import annotations

"""Strict source snapshot for Performance Mode Build Matrix exports.

The application Build domain intentionally remains dataclass-based. This module is
an export boundary: it copies only data the PDF feature is allowed to consume,
validates it strictly with Pydantic, then reconstructs an isolated PlayerBuild.
Malformed saved state therefore fails closed before variant resolution, comparison,
or ReportLab rendering.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.build_model import (
    ARMOR_SLOTS,
    MAX_ATTRIBUTE_POINTS,
    BuildContextVariant,
    ChampionPointEntry,
    GearSlot,
    PlayerBuild,
)


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


class PerformanceModeGearSlotSource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    Set: str = Field(default="", max_length=240)
    Trait: str = Field(default="", max_length=120)
    Enchant: str = Field(default="", max_length=240)
    Weight: str = Field(default="", max_length=80)
    Set2: str = Field(default="", max_length=240)
    Quality: str = Field(default="", max_length=80)
    EnchantTier: str = Field(default="", max_length=80)
    Level: str = Field(default="", max_length=80)
    WeaponType: str = Field(default="", max_length=120)
    EnchantQuality: str = Field(default="", max_length=80)

    @field_validator("*")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _clean_text(value)

    @classmethod
    def from_gear_slot(cls, slot: GearSlot) -> "PerformanceModeGearSlotSource":
        if not isinstance(slot, GearSlot):
            raise TypeError("Build Matrix gear source must be a GearSlot")
        return cls.model_validate(slot.to_dict())

    def to_gear_slot(self) -> GearSlot:
        return GearSlot.from_dict(self.model_dump(mode="python"))


class PerformanceModeChampionPointSource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    Name: str = Field(default="", max_length=240)
    Points: str = Field(default="", max_length=40)

    @field_validator("Name", "Points")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _clean_text(value)

    @classmethod
    def from_entry(cls, entry: ChampionPointEntry) -> "PerformanceModeChampionPointSource":
        if not isinstance(entry, ChampionPointEntry):
            raise TypeError("Build Matrix Champion Point source must be a ChampionPointEntry")
        return cls.model_validate(entry.to_dict())

    def to_entry(self) -> ChampionPointEntry:
        return ChampionPointEntry.from_dict(self.model_dump(mode="python"))


class PerformanceModeVariantSource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    ContextType: str = Field(default="Boss", max_length=80)
    TeamName: str = Field(default="", max_length=240)
    BossName: str = Field(default="", max_length=240)
    TransformedForm: str = Field(default="", max_length=40)
    Mundus: str = Field(default="", max_length=120)
    SecondMundus: str = Field(default="", max_length=120)
    Armor: dict[str, PerformanceModeGearSlotSource] = Field(default_factory=dict)
    FrontBarWeapon: PerformanceModeGearSlotSource = Field(default_factory=PerformanceModeGearSlotSource)
    FrontBarOffHand: PerformanceModeGearSlotSource = Field(default_factory=PerformanceModeGearSlotSource)
    BackBarWeapon: PerformanceModeGearSlotSource = Field(default_factory=PerformanceModeGearSlotSource)
    BackBarOffHand: PerformanceModeGearSlotSource = Field(default_factory=PerformanceModeGearSlotSource)
    Necklace: PerformanceModeGearSlotSource = Field(default_factory=PerformanceModeGearSlotSource)
    Ring1: PerformanceModeGearSlotSource = Field(default_factory=PerformanceModeGearSlotSource)
    Ring2: PerformanceModeGearSlotSource = Field(default_factory=PerformanceModeGearSlotSource)
    ChampionPoints: tuple[PerformanceModeChampionPointSource, ...] = ()
    FrontBarSkills: tuple[str, str, str, str, str, str] = ("", "", "", "", "", "")
    BackBarSkills: tuple[str, str, str, str, str, str] = ("", "", "", "", "", "")
    Food: str = Field(default="", max_length=240)
    Potion: str = Field(default="", max_length=240)
    FrontBarPoison: str = Field(default="", max_length=240)
    BackBarPoison: str = Field(default="", max_length=240)
    Notes: str = Field(default="", max_length=4000)

    @field_validator(
        "ContextType", "TeamName", "BossName", "TransformedForm", "Mundus",
        "SecondMundus", "Food", "Potion", "FrontBarPoison", "BackBarPoison",
    )
    @classmethod
    def normalize_short_text(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("Notes")
    @classmethod
    def normalize_notes(cls, value: str) -> str:
        return value.strip()

    @field_validator("FrontBarSkills", "BackBarSkills")
    @classmethod
    def validate_bar(cls, values: tuple[str, str, str, str, str, str]):
        cleaned = tuple(_clean_text(value) for value in values)
        if any(len(value) > 240 for value in cleaned):
            raise ValueError("skill names must be 240 characters or fewer")
        return cleaned

    @field_validator("Armor")
    @classmethod
    def validate_armor_slots(cls, value: dict[str, PerformanceModeGearSlotSource]):
        unknown = sorted(set(value) - set(ARMOR_SLOTS))
        if unknown:
            raise ValueError(f"unknown armor slots: {', '.join(unknown)}")
        return value

    @field_validator("TransformedForm")
    @classmethod
    def validate_form(cls, value: str) -> str:
        normalized = value.casefold()
        if normalized not in {"", "vampire", "werewolf"}:
            raise ValueError("transformed form must be blank, vampire, or werewolf")
        return normalized

    @classmethod
    def from_variant(cls, variant: BuildContextVariant) -> "PerformanceModeVariantSource":
        if not isinstance(variant, BuildContextVariant):
            raise TypeError("Build Matrix Context Variant source must be a BuildContextVariant")
        armor = {
            slot: PerformanceModeGearSlotSource.model_validate(dict(values))
            for slot, values in variant.Armor.items()
        }
        return cls(
            ContextType=variant.ContextType,
            TeamName=variant.TeamName,
            BossName=variant.BossName,
            TransformedForm=variant.TransformedForm,
            Mundus=variant.Mundus,
            SecondMundus=variant.SecondMundus,
            Armor=armor,
            FrontBarWeapon=PerformanceModeGearSlotSource.from_gear_slot(variant.FrontBarWeapon),
            FrontBarOffHand=PerformanceModeGearSlotSource.from_gear_slot(variant.FrontBarOffHand),
            BackBarWeapon=PerformanceModeGearSlotSource.from_gear_slot(variant.BackBarWeapon),
            BackBarOffHand=PerformanceModeGearSlotSource.from_gear_slot(variant.BackBarOffHand),
            Necklace=PerformanceModeGearSlotSource.from_gear_slot(variant.Necklace),
            Ring1=PerformanceModeGearSlotSource.from_gear_slot(variant.Ring1),
            Ring2=PerformanceModeGearSlotSource.from_gear_slot(variant.Ring2),
            ChampionPoints=tuple(
                PerformanceModeChampionPointSource.from_entry(entry)
                for entry in variant.ChampionPoints
            ),
            FrontBarSkills=tuple(variant.FrontBarSkills),
            BackBarSkills=tuple(variant.BackBarSkills),
            Food=variant.Food,
            Potion=variant.Potion,
            FrontBarPoison=variant.FrontBarPoison,
            BackBarPoison=variant.BackBarPoison,
            Notes=variant.Notes,
        )

    def to_variant(self) -> BuildContextVariant:
        return BuildContextVariant(
            ContextType=self.ContextType,
            TeamName=self.TeamName,
            BossName=self.BossName,
            TransformedForm=self.TransformedForm,
            Mundus=self.Mundus,
            SecondMundus=self.SecondMundus,
            Armor={
                slot: gear.model_dump(mode="python")
                for slot, gear in self.Armor.items()
            },
            FrontBarWeapon=self.FrontBarWeapon.to_gear_slot(),
            FrontBarOffHand=self.FrontBarOffHand.to_gear_slot(),
            BackBarWeapon=self.BackBarWeapon.to_gear_slot(),
            BackBarOffHand=self.BackBarOffHand.to_gear_slot(),
            Necklace=self.Necklace.to_gear_slot(),
            Ring1=self.Ring1.to_gear_slot(),
            Ring2=self.Ring2.to_gear_slot(),
            ChampionPoints=[entry.to_entry() for entry in self.ChampionPoints],
            FrontBarSkills=list(self.FrontBarSkills),
            BackBarSkills=list(self.BackBarSkills),
            Food=self.Food,
            Potion=self.Potion,
            FrontBarPoison=self.FrontBarPoison,
            BackBarPoison=self.BackBarPoison,
            Notes=self.Notes,
        )


class PerformanceModeBuildExportSource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    Name: str = Field(default="", max_length=240)
    Gamertag: str = Field(default="", max_length=240)
    BuildName: str = Field(default="", max_length=240)
    Race: str = Field(default="", max_length=120)
    EsoClass: str = Field(default="", max_length=120)
    Role: str = Field(default="", max_length=120)
    Mundus: str = Field(default="", max_length=120)
    SecondMundus: str = Field(default="", max_length=120)
    Vampire: bool = False
    Werewolf: bool = False
    AttributeHealth: int = Field(default=0, ge=0, le=MAX_ATTRIBUTE_POINTS)
    AttributeMagicka: int = Field(default=0, ge=0, le=MAX_ATTRIBUTE_POINTS)
    AttributeStamina: int = Field(default=0, ge=0, le=MAX_ATTRIBUTE_POINTS)
    ClassSkillLines: tuple[str, ...] = ()
    ClassMasteryAbilityIds: tuple[int, ...] = ()
    Armor: dict[str, PerformanceModeGearSlotSource]
    FrontBarWeapon: PerformanceModeGearSlotSource
    FrontBarOffHand: PerformanceModeGearSlotSource
    BackBarWeapon: PerformanceModeGearSlotSource
    BackBarOffHand: PerformanceModeGearSlotSource
    Necklace: PerformanceModeGearSlotSource
    Ring1: PerformanceModeGearSlotSource
    Ring2: PerformanceModeGearSlotSource
    ChampionPoints: tuple[PerformanceModeChampionPointSource, ...] = ()
    FrontBarSkills: tuple[str, str, str, str, str, str]
    BackBarSkills: tuple[str, str, str, str, str, str]
    Food: str = Field(default="", max_length=240)
    Potion: str = Field(default="", max_length=240)
    Notes: str = Field(default="", max_length=4000)
    ContextVariants: tuple[PerformanceModeVariantSource, ...] = ()
    TransformedForm: str = Field(default="", max_length=40)
    FrontBarPoison: str = Field(default="", max_length=240)
    BackBarPoison: str = Field(default="", max_length=240)

    @field_validator(
        "Name", "Gamertag", "BuildName", "Race", "EsoClass", "Role", "Mundus",
        "SecondMundus", "Food", "Potion", "TransformedForm", "FrontBarPoison",
        "BackBarPoison",
    )
    @classmethod
    def normalize_short_text(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("Notes")
    @classmethod
    def normalize_notes(cls, value: str) -> str:
        return value.strip()

    @field_validator("ClassSkillLines")
    @classmethod
    def validate_class_skill_lines(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(_clean_text(value) for value in values)
        if any(not value or len(value) > 120 for value in cleaned):
            raise ValueError("class skill-line ids must be nonblank and bounded")
        if len({value.casefold() for value in cleaned}) != len(cleaned):
            raise ValueError("class skill-line ids must be unique")
        return cleaned

    @field_validator("ClassMasteryAbilityIds")
    @classmethod
    def validate_masteries(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if len(values) > 2:
            raise ValueError("a Build may select at most two Class Masteries")
        if any(value <= 0 for value in values):
            raise ValueError("Class Mastery ids must be positive")
        if len(set(values)) != len(values):
            raise ValueError("Class Mastery ids must be unique")
        return values

    @field_validator("Armor")
    @classmethod
    def validate_armor(cls, value: dict[str, PerformanceModeGearSlotSource]):
        if set(value) != set(ARMOR_SLOTS):
            missing = sorted(set(ARMOR_SLOTS) - set(value))
            unknown = sorted(set(value) - set(ARMOR_SLOTS))
            details: list[str] = []
            if missing:
                details.append(f"missing: {', '.join(missing)}")
            if unknown:
                details.append(f"unknown: {', '.join(unknown)}")
            raise ValueError("armor slots must match the canonical seven slots (" + "; ".join(details) + ")")
        return value

    @field_validator("FrontBarSkills", "BackBarSkills")
    @classmethod
    def validate_bar(cls, values: tuple[str, str, str, str, str, str]):
        cleaned = tuple(_clean_text(value) for value in values)
        if any(len(value) > 240 for value in cleaned):
            raise ValueError("skill names must be 240 characters or fewer")
        return cleaned

    @field_validator("TransformedForm")
    @classmethod
    def validate_form(cls, value: str) -> str:
        normalized = value.casefold()
        if normalized not in {"", "vampire", "werewolf"}:
            raise ValueError("transformed form must be blank, vampire, or werewolf")
        return normalized

    @model_validator(mode="after")
    def validate_world_state(self):
        if self.Vampire and self.Werewolf:
            raise ValueError("a Build cannot be both Vampire and Werewolf")
        total = self.AttributeHealth + self.AttributeMagicka + self.AttributeStamina
        if total > MAX_ATTRIBUTE_POINTS:
            raise ValueError(f"attribute points cannot exceed {MAX_ATTRIBUTE_POINTS}")
        if self.SecondMundus and self.SecondMundus.casefold() == self.Mundus.casefold():
            raise ValueError("primary and secondary Mundus boons must be distinct")
        if self.TransformedForm == "vampire" and not self.Vampire:
            raise ValueError("Vampire transformed form requires Vampire affiliation")
        if self.TransformedForm == "werewolf" and not self.Werewolf:
            raise ValueError("Werewolf transformed form requires Werewolf affiliation")

        for variant in self.ContextVariants:
            if variant.TransformedForm == "vampire" and not self.Vampire:
                raise ValueError(
                    "Vampire Context Variant requires Vampire affiliation on the parent Build"
                )
            if variant.TransformedForm == "werewolf" and not self.Werewolf:
                raise ValueError(
                    "Werewolf Context Variant requires Werewolf affiliation on the parent Build"
                )
        return self

    @classmethod
    def from_build(cls, build: PlayerBuild) -> "PerformanceModeBuildExportSource":
        if not isinstance(build, PlayerBuild):
            raise TypeError("Performance Mode Build Matrix export requires a PlayerBuild")

        unknown_armor_slots = sorted(set(build.Armor) - set(ARMOR_SLOTS))
        if unknown_armor_slots:
            raise ValueError(
                "Build Matrix source contains unknown armor slots: "
                + ", ".join(unknown_armor_slots)
            )

        armor: dict[str, PerformanceModeGearSlotSource] = {}
        for slot in ARMOR_SLOTS:
            raw = build.Armor.get(slot)
            if not isinstance(raw, dict):
                raise TypeError(f"Build Matrix armor slot {slot!r} must be a mapping")
            armor[slot] = PerformanceModeGearSlotSource.model_validate(dict(raw))

        return cls(
            Name=build.Name,
            Gamertag=build.Gamertag,
            BuildName=build.BuildName,
            Race=build.Race,
            EsoClass=build.EsoClass,
            Role=build.Role,
            Mundus=build.Mundus,
            SecondMundus=build.SecondMundus,
            Vampire=build.Vampire,
            Werewolf=build.Werewolf,
            AttributeHealth=build.AttributeHealth,
            AttributeMagicka=build.AttributeMagicka,
            AttributeStamina=build.AttributeStamina,
            ClassSkillLines=tuple(build.ClassSkillLines),
            ClassMasteryAbilityIds=tuple(build.ClassMasteryAbilityIds),
            Armor=armor,
            FrontBarWeapon=PerformanceModeGearSlotSource.from_gear_slot(build.FrontBarWeapon),
            FrontBarOffHand=PerformanceModeGearSlotSource.from_gear_slot(build.FrontBarOffHand),
            BackBarWeapon=PerformanceModeGearSlotSource.from_gear_slot(build.BackBarWeapon),
            BackBarOffHand=PerformanceModeGearSlotSource.from_gear_slot(build.BackBarOffHand),
            Necklace=PerformanceModeGearSlotSource.from_gear_slot(build.Necklace),
            Ring1=PerformanceModeGearSlotSource.from_gear_slot(build.Ring1),
            Ring2=PerformanceModeGearSlotSource.from_gear_slot(build.Ring2),
            ChampionPoints=tuple(
                PerformanceModeChampionPointSource.from_entry(entry)
                for entry in build.ChampionPoints
            ),
            FrontBarSkills=tuple(build.FrontBarSkills),
            BackBarSkills=tuple(build.BackBarSkills),
            Food=build.Food,
            Potion=build.Potion,
            Notes=build.Notes,
            ContextVariants=tuple(
                PerformanceModeVariantSource.from_variant(variant)
                for variant in (
                    list(build.ContextVariants)
                    if build.ContextVariants
                    else [
                        BuildContextVariant.from_boss_loadout(loadout)
                        for loadout in build.BossLoadouts
                    ]
                )
            ),
            TransformedForm=build.TransformedForm,
            FrontBarPoison=build.FrontBarPoison,
            BackBarPoison=build.BackBarPoison,
        )

    def to_build(self) -> PlayerBuild:
        """Return an isolated dataclass Build containing only validated export state."""
        return PlayerBuild(
            Name=self.Name,
            Gamertag=self.Gamertag,
            BuildName=self.BuildName,
            Race=self.Race,
            EsoClass=self.EsoClass,
            Role=self.Role,
            Mundus=self.Mundus,
            Vampire=self.Vampire,
            Werewolf=self.Werewolf,
            AttributeHealth=self.AttributeHealth,
            AttributeMagicka=self.AttributeMagicka,
            AttributeStamina=self.AttributeStamina,
            ClassSkillLines=list(self.ClassSkillLines),
            ClassMasteryAbilityIds=list(self.ClassMasteryAbilityIds),
            Armor={
                slot: gear.model_dump(mode="python")
                for slot, gear in self.Armor.items()
            },
            FrontBarWeapon=self.FrontBarWeapon.to_gear_slot(),
            FrontBarOffHand=self.FrontBarOffHand.to_gear_slot(),
            BackBarWeapon=self.BackBarWeapon.to_gear_slot(),
            BackBarOffHand=self.BackBarOffHand.to_gear_slot(),
            Necklace=self.Necklace.to_gear_slot(),
            Ring1=self.Ring1.to_gear_slot(),
            Ring2=self.Ring2.to_gear_slot(),
            ChampionPoints=[entry.to_entry() for entry in self.ChampionPoints],
            FrontBarSkills=list(self.FrontBarSkills),
            BackBarSkills=list(self.BackBarSkills),
            Food=self.Food,
            Potion=self.Potion,
            Notes=self.Notes,
            SecondMundus=self.SecondMundus,
            ContextVariants=[variant.to_variant() for variant in self.ContextVariants],
            TransformedForm=self.TransformedForm,
            FrontBarPoison=self.FrontBarPoison,
            BackBarPoison=self.BackBarPoison,
        )


def validate_performance_mode_export_source(build: PlayerBuild) -> PlayerBuild:
    """Fail closed on malformed Build state and return a validated isolated copy."""
    return PerformanceModeBuildExportSource.from_build(build).to_build()


__all__ = [
    "PerformanceModeBuildExportSource",
    "PerformanceModeChampionPointSource",
    "PerformanceModeGearSlotSource",
    "PerformanceModeVariantSource",
    "validate_performance_mode_export_source",
]
