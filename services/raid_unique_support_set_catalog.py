from __future__ import annotations

"""Raid-planning references for support sets with unique, non-Major/Minor effects.

These rows are presentation/reference data for Coverage. They do not create canonical
combat-effect mappings or universal raid requirements. ``required_pieces`` records the
reviewed equipment threshold needed before static build state can prove that the set's
support effect is even available. ``static_state`` remains conservative: triggered/proc
support effects are capability evidence, not uptime evidence.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RaidUniqueSupportSetReference:
    name: str
    category: str
    type_label: str
    source_notes: tuple[str, ...]
    default_required: bool = False
    required_pieces: int = 5
    static_state: str = "conditional"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if self.category not in {"Buff", "Debuff"}:
            raise ValueError("category must be Buff or Debuff")
        if not self.type_label.startswith("Unique:"):
            raise ValueError("unique support type labels must start with 'Unique:'")
        if not self.source_notes:
            raise ValueError("source_notes must contain at least one reviewed example")
        if int(self.required_pieces) <= 0:
            raise ValueError("required_pieces must be positive")
        if self.static_state not in {"available", "conditional"}:
            raise ValueError("static_state must be available or conditional")


# Keep labels deliberately terse: this column is for raid-lead scanning, while
# Coverage Notes carries the fuller planning explanation. All current unique effects
# remain conditional because their actual raid value depends on proc/activation/combat
# state even when the equipment threshold is statically proven.
UNIQUE_SUPPORT_SET_EFFECTS: tuple[RaidUniqueSupportSetReference, ...] = (
    RaidUniqueSupportSetReference(
        "Powerful Assault", "Buff", "Unique: +307 W/SD",
        ("Set: Powerful Assault", "Casting an Assault ability grants a unique Weapon and Spell Damage increase to nearby group members."),
    ),
    RaidUniqueSupportSetReference(
        "Spaulder of Ruin", "Buff", "Unique: +W/SD aura",
        ("Mythic: Spaulder of Ruin", "Aura of Pride grants nearby group members a unique Weapon and Spell Damage increase."),
        required_pieces=1,
    ),
    RaidUniqueSupportSetReference(
        "Pearlescent Ward", "Buff", "Unique: dmg / mitigation",
        ("Set: Pearlescent Ward", "Unique group scaling effect that shifts between offensive support and damage mitigation as group members die."),
    ),
    RaidUniqueSupportSetReference(
        "Pillager's Profit", "Buff", "Unique: group Ultimate",
        ("Set: Pillager's Profit", "Ultimate use supplies a unique Ultimate-gain effect to other group members."),
    ),
    RaidUniqueSupportSetReference(
        "Symphony of Blades", "Buff", "Unique: resource restore",
        ("Monster set: Symphony of Blades", "Unique ally Magicka/Stamina restoration proc."),
        required_pieces=2,
    ),
    RaidUniqueSupportSetReference(
        "Ozezan the Inferno", "Buff", "Unique: +Armor / Vitality",
        ("Monster set: Ozezan the Inferno", "Provides Minor Vitality and an additional unique Armor-support effect from healing/overhealing."),
        required_pieces=2,
    ),
    RaidUniqueSupportSetReference(
        "Jorvuld's Guidance", "Buff", "Unique: buff duration",
        ("Set: Jorvuld's Guidance", "Extends Major/Minor buffs and damage shields applied by the wearer."),
    ),
    RaidUniqueSupportSetReference(
        "Arkasis's Genius", "Buff", "Unique: group Ultimate",
        ("Set: Arkasis's Genius", "Potion use supplies a unique Ultimate gain to the wearer and nearby group members."),
    ),
    RaidUniqueSupportSetReference(
        "Roar of Alkosh", "Debuff", "Unique: up to -6000 Armor",
        ("Set: Roar of Alkosh", "Synergy activation applies a unique enemy resistance reduction; it is not Major or Minor Breach."),
    ),
    RaidUniqueSupportSetReference(
        "Touch of Z'en", "Debuff", "Unique: +damage taken",
        ("Set: Z'en's Redress", "Maintains a unique enemy damage-taken increase from the wearer's damage-over-time pressure."),
    ),
    RaidUniqueSupportSetReference(
        "Way of Martial Knowledge", "Debuff", "Unique: +damage taken",
        ("Set: Way of Martial Knowledge", "Applies a unique enemy damage-taken increase while its stamina condition is met."),
    ),
    RaidUniqueSupportSetReference(
        "Elemental Catalyst", "Debuff", "Unique: +crit dmg taken",
        ("Set: Elemental Catalyst", "Elemental damage applies unique Flame/Frost/Shock critical-damage-taken effects to the enemy."),
    ),
    RaidUniqueSupportSetReference(
        "Crimson Oath's Rive", "Debuff", "Unique: Armor shred",
        ("Set: Crimson Oath's Rive", "Using an ability that applies a Major or Minor buff/debuff applies a unique enemy Armor reduction nearby."),
    ),
    RaidUniqueSupportSetReference(
        "Nazaray", "Debuff", "Unique: debuff extension",
        ("Monster set: Nazaray", "Ultimate use extends eligible negative effects already active on nearby enemies."),
        required_pieces=2,
    ),
    RaidUniqueSupportSetReference(
        "Encratis's Behemoth", "Debuff", "Unique: flame dmg modifier",
        ("Monster set: Encratis's Behemoth", "Creates a unique flame-support area that increases enemy Flame Damage taken and reduces Flame Damage taken by group members."),
        required_pieces=2,
    ),
)


UNIQUE_SUPPORT_SET_BY_NAME = {row.name: row for row in UNIQUE_SUPPORT_SET_EFFECTS}
UNIQUE_SUPPORT_SET_NAMES = tuple(row.name for row in UNIQUE_SUPPORT_SET_EFFECTS)
UNIQUE_SUPPORT_DEBUFF_NAMES = frozenset(
    row.name for row in UNIQUE_SUPPORT_SET_EFFECTS if row.category == "Debuff"
)
