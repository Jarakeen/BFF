from __future__ import annotations

"""Raid-facing named buff/debuff reference catalog.

This is intentionally a human planning catalog, not a capability-resolution shortcut.
It lists group-relevant named effects and reviewed example sources so the Coverage UI
can help a raid lead answer "where can this come from?" without guessing canonical
EffectVariant mappings for systems that have not been proven end to end yet.

Mechanic jobs and situational raid utilities (kite, portal, interrupts, orbs, purify,
etc.) do not belong here. Magickasteal remains because it is itself a named debuff.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RaidGroupEffectReference:
    name: str
    category: str
    source_notes: tuple[str, ...]
    default_required: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if self.category not in {"Buff", "Debuff"}:
            raise ValueError("category must be Buff or Debuff")
        if not self.source_notes:
            raise ValueError("source_notes must contain at least one reviewed example")


# Existing Coverage requirements remain default-required where they are still actual
# buffs/debuffs. Newly exposed effects are reference-visible but are not silently
# promoted into universal raid requirements.
GROUP_COVERAGE_EFFECTS: tuple[RaidGroupEffectReference, ...] = (
    RaidGroupEffectReference(
        "Major Courage", "Buff",
        ("Sets: Spell Power Cure, Vestment of Olorime", "Ability: Ferocious Roar"),
        True,
    ),
    RaidGroupEffectReference(
        "Minor Courage", "Buff",
        ("Set: Claw of Yolnahkriin", "Abilities: Arcanist's Domain, Power Extraction, Pack Leader", "Scribing: Courage scripts"),
    ),
    RaidGroupEffectReference(
        "Major Force", "Buff",
        ("Ultimate: Aggressive Horn", "Set: Saxhleel Champion", "Abilities: Ink-Scribe's Verve, Light's Champion"),
    ),
    RaidGroupEffectReference(
        "Minor Force", "Buff",
        ("Set: Grave Inevitability", "Abilities: Stalwart Guard, Trap Beast", "Scribing: Force scripts"),
        True,
    ),
    RaidGroupEffectReference(
        "Major Slayer", "Buff",
        ("Sets: Roaring Opportunist, Master Architect, War Machine, Tooth of Lokkestiiz",),
        True,
    ),
    RaidGroupEffectReference(
        "Minor Berserk", "Buff",
        ("Ability: Combat Prayer", "Set: Stone's Accord", "Scribing: Berserk scripts"),
    ),
    RaidGroupEffectReference(
        "Major Berserk", "Buff",
        ("Ability/ultimate sources: Summon Storm Atronach, Lead From the Front", "Set sources include Kinras's Wrath and Tharriker's Strike"),
        True,
    ),
    RaidGroupEffectReference(
        "Major Brutality", "Buff",
        ("Group ability: Molten Weapons", "Scribing: Brutality and Sorcery scripts"),
    ),
    RaidGroupEffectReference(
        "Major Sorcery", "Buff",
        ("Group ability: Molten Weapons", "Scribing: Brutality and Sorcery scripts"),
    ),
    RaidGroupEffectReference(
        "Minor Brutality", "Buff",
        ("Dragonknight Earthen Heart group support passive/source",),
    ),
    RaidGroupEffectReference(
        "Minor Sorcery", "Buff",
        ("Templar passive: Illuminate",),
    ),
    RaidGroupEffectReference(
        "Minor Savagery", "Buff",
        ("Nightblade passive: Hemorrhage",),
    ),
    RaidGroupEffectReference(
        "Minor Prophecy", "Buff",
        ("Sorcerer passive: Exploitation",),
    ),
    RaidGroupEffectReference(
        "Major Resolve", "Buff",
        ("Group ability: Frost Cloak / Expansive Frost Cloak", "Scribing: Resolve scripts"),
    ),
    RaidGroupEffectReference(
        "Minor Resolve", "Buff",
        ("Ability: Blessing of Protection / Combat Prayer", "Sets: Magma Incarnate, Stone's Accord", "Scribing: Resolve scripts"),
        True,
    ),
    RaidGroupEffectReference(
        "Major Protection", "Buff",
        ("Group-capable ultimate/source: Sleet Storm / Permafrost", "Sets include Hagraven's Garden and Test of Resolve", "Scribing: Protection scripts"),
    ),
    RaidGroupEffectReference(
        "Minor Protection", "Buff",
        ("Abilities: Circle of Protection, Bone Totem", "Scribing: Protection scripts"),
    ),
    RaidGroupEffectReference(
        "Major Evasion", "Buff",
        ("Set: Gossamer",),
    ),
    RaidGroupEffectReference(
        "Major Heroism", "Buff",
        ("Set: Drake's Rush", "Sets also include Hanu's Compassion and Transformative Hope", "Scribing: Heroism on Trample"),
    ),
    RaidGroupEffectReference(
        "Major Vitality", "Buff",
        ("Synergy/source: Bone Surge", "Sets include Bani's Torment and Mender's Ward", "Scribing: Vitality scripts"),
    ),
    RaidGroupEffectReference(
        "Minor Vitality", "Buff",
        ("Sets: Ozezan the Inferno, Hollowfang Thirst", "Abilities: Mystic Guard, Vibrant Shroud", "Scribing: Vitality scripts"),
    ),
    RaidGroupEffectReference(
        "Major Fortitude", "Buff",
        ("Set/source: Apocryphal Inspiration",),
    ),
    RaidGroupEffectReference(
        "Minor Fortitude", "Buff",
        ("Ability: Arcanist's Domain",),
    ),
    RaidGroupEffectReference(
        "Major Intellect", "Buff",
        ("Set/source: Apocryphal Inspiration", "Scribing: Intellect and Endurance on Wield Soul"),
    ),
    RaidGroupEffectReference(
        "Minor Intellect", "Buff",
        ("Abilities: Arcanist's Domain, Enchanted Growth", "Scribing: Intellect and Endurance scripts"),
        True,
    ),
    RaidGroupEffectReference(
        "Major Endurance", "Buff",
        ("Set/source: Apocryphal Inspiration", "Scribing: Intellect and Endurance on Wield Soul"),
    ),
    RaidGroupEffectReference(
        "Minor Endurance", "Buff",
        ("Abilities: Arcanist's Domain, Enchanted Growth", "Scribing: Intellect and Endurance scripts"),
    ),
    RaidGroupEffectReference(
        "Major Expedition", "Buff",
        ("Group ability: Rapid Maneuver / Charging Maneuver",),
    ),
    RaidGroupEffectReference(
        "Minor Expedition", "Buff",
        ("Group ability: Charging Maneuver",),
    ),
    RaidGroupEffectReference(
        "Empower", "Buff",
        ("Group-capable ability: Empowering Grasp", "Scribing: Empower on Mender's Bond"),
    ),
    RaidGroupEffectReference(
        "Major Vulnerability", "Debuff",
        ("Ultimate: Frozen Colossus", "Sets: Turning Tide, Archdruid Devyric"),
        True,
    ),
    RaidGroupEffectReference(
        "Minor Vulnerability", "Debuff",
        ("Abilities/status: Swarm, Concussed", "Sets: Infallible Mage, Noble's Conquest", "Scribing: Vulnerability scripts"),
    ),
    RaidGroupEffectReference(
        "Major Breach", "Debuff",
        ("Abilities: Weakness to Elements, Puncture, Razor Caltrops, Unnerving Boneyard", "Sets: Kynmarcher's Cruelty, Night Mother's Gaze"),
        True,
    ),
    RaidGroupEffectReference(
        "Minor Breach", "Debuff",
        ("Abilities/status: Deep Fissure, Pierce Armor, Sundered", "Sets: Dragon's Defilement, Sunderflame", "Scribing: Breach scripts"),
    ),
    RaidGroupEffectReference(
        "Major Maim", "Debuff",
        ("Abilities: Frost Clench, Nova, Deafening Roar", "Sets: Bani's Torment, Lady Thorn, Void Bash", "Scribing: Maim scripts"),
    ),
    RaidGroupEffectReference(
        "Minor Maim", "Debuff",
        ("Abilities/status: Chilled, Low Slash, Inner Beast", "Sets: Knightmare, Shadowrend", "Scribing: Maim scripts"),
        True,
    ),
    RaidGroupEffectReference(
        "Major Cowardice", "Debuff",
        ("Sets: Vykosa, Kynmarcher's Cruelty", "Abilities: Bone Totem, Deafening Roar", "Scribing: Cowardice scripts"),
    ),
    RaidGroupEffectReference(
        "Minor Cowardice", "Debuff",
        ("Abilities: Corrupting Pollen, Power Extraction", "Set: Healing Mage", "Scribing: Cowardice scripts"),
    ),
    RaidGroupEffectReference(
        "Major Defile", "Debuff",
        ("Abilities: Corrupting Pollen, Dark Flare, Blighted Blastbones", "Sets: Durok's Bane, Ward of Cyrodiil", "Scribing: Defile on Wield Soul"),
    ),
    RaidGroupEffectReference(
        "Minor Defile", "Debuff",
        ("Status/ability: Diseased, Lethal Arrow", "Sets: Fasalla's Guile, Thurvokun", "Scribing: Defile scripts"),
    ),
    RaidGroupEffectReference(
        "Minor Brittle", "Debuff",
        ("Status/ability: Chilled while using an Ice Staff, Rune of the Colorless Pool", "Sets: Glittering Goad, The Saint and the Seducer", "Scribing: Brittle scripts"),
        True,
    ),
    RaidGroupEffectReference(
        "Minor Lifesteal", "Debuff",
        ("Abilities: Blood Altar, Force Siphon, Leeching Vines, Runic Embrace", "Scribing: Lifesteal scripts"),
    ),
    RaidGroupEffectReference(
        "Magickasteal", "Debuff",
        ("Abilities/status: Elemental Drain, Siphon Spirit, Overcharged", "Scribing: Magickasteal scripts"),
        True,
    ),
    RaidGroupEffectReference(
        "Minor Timidity", "Debuff",
        ("Set: Baron Thirsk",),
    ),
    RaidGroupEffectReference(
        "Minor Enervation", "Debuff",
        ("Sets: Blunted Blades, Critical Riposte, Lady Malygda, Wizard's Riposte", "Scribing: Enervation scripts"),
    ),
    RaidGroupEffectReference(
        "Minor Uncertainty", "Debuff",
        ("Set: Critical Riposte", "Scribing: Uncertainty scripts"),
    ),
    RaidGroupEffectReference(
        "Crusher", "Debuff",
        ("Weapon enchantment: Crusher",),
        True,
    ),
)


GROUP_COVERAGE_BY_NAME = {row.name: row for row in GROUP_COVERAGE_EFFECTS}
GROUP_COVERAGE_NAMES = tuple(row.name for row in GROUP_COVERAGE_EFFECTS)
GROUP_DEBUFF_NAMES = frozenset(
    row.name for row in GROUP_COVERAGE_EFFECTS if row.category == "Debuff"
)
