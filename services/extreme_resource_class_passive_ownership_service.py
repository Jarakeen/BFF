from __future__ import annotations

"""Reviewed ownership boundaries for class passives in Extreme max-resource audits.

This service is deliberately not a passive calculator. It records exact class
passives whose shared canonical resolver or reviewed U50 tooltip defines their
effect family well enough to prove whether they can alter Max Health, Max Magicka,
or Max Stamina.

Rows are conservative and explicit. A passive is never treated as irrelevant just
because its tooltip fails to mention the requested resource; its effect family must
be reviewed first. Objective-specific canonical ownership is recorded explicitly so
a passive can be accounted for one maximum resource and proven irrelevant to the
others without duplicating mechanic math here.
"""

from dataclasses import dataclass
from enum import Enum

from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceClassPassiveOwnershipStatus(str, Enum):
    CANONICALLY_ACCOUNTED = "canonically_accounted"
    PROVEN_IRRELEVANT = "proven_irrelevant"


@dataclass(frozen=True)
class ExtremeResourceClassPassiveOwnership:
    skill_line: str
    passive_name: str
    source: str
    effect_family: str
    affected_objectives: tuple[str, ...] = ()

    @property
    def identity(self) -> tuple[str, str]:
        return (self.skill_line, self.passive_name)

    def status_for(self, objective_key: str) -> ExtremeResourceClassPassiveOwnershipStatus:
        return (
            ExtremeResourceClassPassiveOwnershipStatus.CANONICALLY_ACCOUNTED
            if objective_key in self.affected_objectives
            else ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT
        )


_REVIEWED_TOOLTIP_IRRELEVANT: tuple[tuple[str, str, str], ...] = (
    ("Aedric Spear", "Burning Light", "damage proc only"),
    ("Aedric Spear", "Spear Wall", "Minor Berserk and Minor Protection only"),
    ("Animal Companions", "Bond with Nature", "flat self-heal when an Animal Companions skill ends only"),
    ("Animal Companions", "Savage Beast", "Ultimate generation after casting an Animal Companions ability only"),
    ("Ardent Flame", "Combustion", "current Magicka/Stamina restoration when Burning or Poisoned is applied only"),
    ("Ardent Flame", "Fan the Flames", "Burning application chance and Burning damage only"),
    ("Ardent Flame", "Traumatic Burns", "enemy Flame Damage Taken and movement-speed modification only"),
    ("Assassination", "Executioner", "current Magicka/Stamina restoration after a recently damaged enemy dies only"),
    ("Assassination", "Master Assassin", "conditional Critical Chance rating only"),
    ("Assassination", "Pressure Points", "Critical Chance rating per slotted Nightblade ability only"),
    ("Bone Tyrant", "Death Gleaning", "current Magicka/Stamina restoration when a nearby combat enemy dies only"),
    ("Bone Tyrant", "Disdain Harm", "damage-over-time mitigation only"),
    ("Curative Runeforms", "Healing Tides", "Healing Done per active Crux only"),
    ("Curative Runeforms", "Hideous Clarity", "current Magicka/Stamina restoration when Crux is generated only"),
    ("Curative Runeforms", "Erudition", "Magicka and Stamina Recovery only"),
    ("Curative Runeforms", "Intricate Runeforms", "Curative Runeforms ability cost reduction and damage-shield strength only"),
    ("Daedric Summoning", "Daedric Protection", "damage-taken mitigation while a Daedric Summoning ability is active only"),
    ("Daedric Summoning", "Rebate", "current Magicka or Stamina restoration when a summon ends only"),
    ("Daedric Summoning", "Power Stone", "Ultimate cost reduction only"),
    ("Dark Magic", "Unholy Knowledge", "Health, Magicka, and Stamina ability-cost reduction only"),
    ("Dark Magic", "Persistence", "next Health/Magicka/Stamina ability cost reduction after blocking only"),
    ("Dark Magic", "Exploitation", "Minor Prophecy / Spell Critical chance only"),
    ("Draconic Power", "Burnished Scales", "block mitigation only"),
    ("Draconic Power", "World in Ruin", "area and damage-over-time damage only"),
    ("Draconic Power", "Elder Dragon", "Minor Brutality plus missing-Health-scaled Health Recovery only"),
    ("Draconic Power", "The Storm Voice", "current-resource restoration after casting an Ultimate only"),
    ("Earthen Heart", "Heart of Stone", "Armor only"),
    ("Earthen Heart", "Landslide", "damage-done stacking from dealing damage only"),
    ("Earthen Heart", "Mountain Giant", "fully charged Heavy Attack Off Balance and current Stamina restoration only"),
    ("Grave Lord", "Death Knell", "conditional Critical Strike Chance only"),
    ("Grave Lord", "Dismember", "Spell and Physical Penetration only"),
    ("Grave Lord", "Rapid Rot", "damage-over-time damage only"),
    ("Grave Lord", "Reusable Parts", "qualifying summon ability cost reduction only"),
    ("Green Balance", "Accelerated Growth", "Major Mending / Healing Done only"),
    ("Green Balance", "Emerald Moss", "Green Balance Healing Done per active-bar slot only"),
    ("Green Balance", "Nature's Gift", "current Magicka/Stamina restoration after qualifying overhealing only"),
    ("Herald of the Tome", "Fated Fortune", "Critical Healing bonus only"),
    ("Herald of the Tome", "Harnessed Quintessence", "temporary flat Weapon/Spell Damage only"),
    ("Herald of the Tome", "Psychic Lesion", "Status Effect damage and application chance only"),
    ("Herald of the Tome", "Splintered Secrets", "Physical and Spell Penetration per Herald ability slotted only"),
    ("Living Death", "Corpse Consumption", "Ultimate generation after consuming a corpse only"),
    ("Living Death", "Curative Curse", "conditional Healing Done only"),
    ("Living Death", "Near-Death Experience", "healing Critical Strike Chance only"),
    ("Living Death", "Undead Confederate", "Health, Magicka, and Stamina Recovery only"),
    ("Restoring Light", "Light Weaver", "Ultimate generation and temporary automatic blocking only"),
    ("Restoring Light", "Master Ritualist", "resurrection speed, resurrected ally Health, and Soul Gem behavior only"),
    ("Restoring Light", "Mending", "missing-target-Health-scaled Healing Done only"),
    ("Restoring Light", "Sacred Ground", "Minor Mending / Healing Done only"),
    ("Shadow", "Refreshing Shadows", "Health, Magicka, and Stamina Recovery only"),
    ("Shadow", "Shadow Barrier", "Major Resolve / resistance state only"),
    ("Shadow", "Dark Veil", "Shadow ability duration only"),
    ("Siphoning", "Catalyst", "Ultimate generation after drinking a potion only"),
    ("Siphoning", "Soul Siphoner", "Healing Done per slotted Siphoning ability only"),
    ("Siphoning", "Transfer", "Ultimate generation after casting a Siphoning ability only"),
    ("Soldier of Apocrypha", "Aegis of the Unseen", "Armor while a beneficial Soldier ability is active only"),
    ("Soldier of Apocrypha", "Circumvented Fate", "Minor Evasion / area-damage mitigation only"),
    ("Soldier of Apocrypha", "Implacable Outcome", "Ultimate generation when Crux is consumed only"),
    ("Soldier of Apocrypha", "Wellspring of the Abyss", "Health, Magicka, and Stamina Recovery per slotted Soldier ability only"),
    ("Storm Calling", "Amplitude", "damage against high-Health targets only"),
    ("Storm Calling", "Capacitor", "Magicka Recovery only"),
    ("Storm Calling", "Energized", "Shock and Physical damage only"),
    ("Winter's Embrace", "Glacial Presence", "Chilled application and Chilled damage only"),
    ("Winter's Embrace", "Icy Aura", "incoming-melee trigger for Bite of Winter / Major Maim only"),
    ("Winter's Embrace", "Piercing Cold", "block amount and Frost Damage only"),
    ("Dawn's Wrath", "Enduring Rays", "selected Dawn's Wrath ability duration only"),
    ("Dawn's Wrath", "Prism", "Ultimate generation only"),
    ("Dawn's Wrath", "Illuminate", "Minor Sorcery / Spell Damage only"),
    ("Dawn's Wrath", "Restoring Spirit", "Health, Magicka, Stamina, and Ultimate ability-cost reduction only"),
    ("Class Mastery", "Above and Beyond", "Critical Damage and Healing cap/bonus only"),
    ("Class Mastery", "Abyssal Emergence", "Crux generation and Weapon/Spell Damage only"),
    ("Class Mastery", "An Eye for Exploitation", "target-health-scaled Weapon/Spell Damage and damage reduction only"),
    ("Class Mastery", "Bountiful Harvest", "Major Heroism and current Magicka/Stamina restoration only"),
    ("Class Mastery", "Bright Harbinger", "Weapon/Spell Damage only"),
    ("Class Mastery", "Glacial Obstinance", "self-heal trigger and Weapon/Spell Damage only"),
    ("Class Mastery", "Malevolent Promise", "corpse-state and combat-effect behavior only"),
    ("Class Mastery", "Share the Spoils", "current-resource restoration/distribution only"),
    ("Class Mastery", "Sphere of Influence", "recovery and damage shield scaled from maximum resources, without changing maxima"),
    ("Class Mastery", "Steadfast Candescence", "Sacred Ground activation and block amount only"),
    ("Class Mastery", "Tundra's Maw", "Chilled-triggered Major Brittle only"),
    ("Class Mastery", "Unbound Potential", "damage-done bonus only"),
    ("Class Mastery", "Bastion of Light", "healing scaled from Max Health and Ultimate generation only; does not modify Max Health"),
    ("Class Mastery", "Booming Voice", "Health, Magicka, and Stamina Recovery only"),
    ("Class Mastery", "Calculated Defense", "damage shield scaled from Max Health and Weapon/Spell Damage only; does not modify Max Health"),
    ("Class Mastery", "Conservation of Energy", "current Magicka/Stamina restoration only"),
    ("Class Mastery", "Cutthroat's Focus", "combat-effect behavior only"),
    ("Class Mastery", "Cycle Unending", "current-Health-relative damage potency only"),
    ("Class Mastery", "Devout Guardian", "damage shield scaled from Max Health, recovery, and Ultimate generation only"),
    ("Class Mastery", "Erudite's Rigor", "Minor Cowardice, Major Vitality, and Ultimate generation only"),
    ("Class Mastery", "Fate Realigned", "Crux generation and Weapon/Spell Damage only"),
    ("Class Mastery", "Font of Power", "Weapon/Spell Damage scaled from the higher Max Magicka/Stamina value; does not modify either maximum"),
    ("Class Mastery", "Green-Keeper's Hide", "damage-taken reduction only"),
    ("Class Mastery", "Inexorable Descent", "damage/healing/shield potency only"),
    ("Class Mastery", "Ink-Scribe's Verve", "Crux generation and Major Force only"),
    ("Class Mastery", "Judgment's Brand", "Templar ability damage only"),
    ("Class Mastery", "Lead from the Front", "Major Berserk and Major Protection only"),
    ("Class Mastery", "Nocturnal Inspiration", "Ultimate generation based on Weapon Critical only"),
    ("Class Mastery", "Pound of Flesh", "current Health and missing-Stamina restoration only"),
    ("Class Mastery", "Resolute Defense", "block amount and current Stamina restoration only"),
    ("Class Mastery", "Static Reverberation", "conditional Shock Damage only"),
    ("Class Mastery", "Veil's Forfeit", "corpse-consumption access and Major Vulnerability duration only"),
    ("Class Mastery", "Wild Adaptation", "status-count-scaled Weapon/Spell Damage only"),
    ("Class Mastery", "Wildfire Embers", "damage scaled from Weapon/Spell Damage and Max Magicka/Stamina; does not modify maxima"),
)


def _reviewed_tooltip_rows() -> tuple[ExtremeResourceClassPassiveOwnership, ...]:
    return tuple(
        ExtremeResourceClassPassiveOwnership(
            skill_line=skill_line,
            passive_name=passive_name,
            source=f"Canonical U50 {skill_line} passive tooltip review",
            effect_family=effect_family,
        )
        for skill_line, passive_name, effect_family in _REVIEWED_TOOLTIP_IRRELEVANT
    )


class ExtremeResourceClassPassiveOwnershipService:
    """Resolve reviewed class-passive ownership for one max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    _ROWS = (
        ExtremeResourceClassPassiveOwnership(
            skill_line="Animal Companions",
            passive_name="Flourish",
            source="WardenPassiveInputResolver",
            effect_family="magicka/stamina recovery only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Animal Companions",
            passive_name="Advanced Species",
            source="WardenPassiveInputResolver",
            effect_family="critical damage only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Winter's Embrace",
            passive_name="Frozen Armor",
            source="WardenPassiveInputResolver",
            effect_family="physical/spell resistance only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Ardent Flame",
            passive_name="A Soul Ablaze",
            source="DragonknightPassiveInputResolver",
            effect_family="healing taken only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Storm Calling",
            passive_name="Expert Mage",
            source="SorcererPassiveInputResolver",
            effect_family="weapon/spell damage only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Aedric Spear",
            passive_name="Balanced Warrior",
            source="TemplarPassiveInputResolver",
            effect_family="weapon/spell damage and armor only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Bone Tyrant",
            passive_name="Health Avarice",
            source="NecromancerPassiveInputResolver",
            effect_family="healing received only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Bone Tyrant",
            passive_name="Last Gasp",
            source="NecromancerPassiveInputResolver",
            effect_family="flat Max Health only",
            affected_objectives=("max_health",),
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Siphoning",
            passive_name="Magicka Flood",
            source="NightbladePassiveInputResolver + active-bar resource search",
            effect_family="active-bar Max Magicka and Max Stamina percentage only",
            affected_objectives=("max_magicka", "max_stamina"),
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Class Mastery",
            passive_name="Nothing Wasted",
            source="ClassMasteryExtremeEffectService",
            effect_family="runtime-stacked Max Health and Weapon/Spell Damage only",
            affected_objectives=("max_health",),
        ),
    ) + _reviewed_tooltip_rows()

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def resolve(
        cls,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
    ) -> tuple[
        ExtremeResourceClassPassiveOwnership,
        ExtremeResourceClassPassiveOwnershipStatus,
    ] | None:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource class-passive objective: {objective_key!r}")
        if passive.domain is not ExtremeSkillDomain.CLASS:
            return None

        target = (
            cls._normalized(passive.skill_line),
            cls._normalized(passive.name),
        )
        for row in cls._ROWS:
            identity = (
                cls._normalized(row.skill_line),
                cls._normalized(row.passive_name),
            )
            if identity == target:
                return row, row.status_for(key)
        return None

    @classmethod
    def reviewed(cls) -> tuple[ExtremeResourceClassPassiveOwnership, ...]:
        return tuple(
            sorted(
                cls._ROWS,
                key=lambda row: (
                    row.skill_line.casefold(),
                    row.passive_name.casefold(),
                ),
            )
        )