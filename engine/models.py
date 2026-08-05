#engine/models.py
from dataclasses import dataclass, field
from typing import List

@dataclass
class CombatEffect:
    """The generic payload representing an absolute modifier or system state."""
    capability_id: str          # e.g., "breach_major", "courage_major"
    stat_modified: str          # e.g., "armor", "weapon_spell_damage"
    modification_value: float   # e.g., -5948, 430
    is_percent: bool = False

@dataclass
class DynamicTrigger:
    """The operational condition layer."""
    condition_type: str         # e.g., "on_hit", "on_crit", "on_equip"
    target: str                 # e.g., "self", "enemy", "group"
    effects: List[CombatEffect] = field(default_factory=list)

@dataclass
class SourceGameObject:
    """Universal schema representing any Layer 1 object (Skill, Set, Food, etc.)."""
    id: str                     # Stable lookup key (e.g., "skill_pierce_armor")
    name: str                   # Human readable display name
    source_layer: str           # "skills", "gear_sets", "mundus", etc.
    triggers: List[DynamicTrigger] = field(default_factory=list)


# Add this to engine/models.py
from dataclasses import dataclass, field
from enum import Enum

class WeaponBarType(Enum):
    FRONT_BAR = "front"
    BACK_BAR = "back"

@dataclass
class WeaponSetup:
    weapon_type: str        # e.g., "Ice Staff", "Restoration Staff"
    enchantment: str        # e.g., "Frost Glyph", "Absorb Magicka"
    trait: str              # e.g., "Charged", "Infused"

@dataclass
class PredictiveHealerProfile:
    gamertag: str
    front_bar: WeaponSetup
    back_bar: WeaponSetup
    back_bar_dot_duration: float = 12.0  # e.g., Blockade of Frost lasts 12 seconds
    back_bar_cast_time: float = 1.5      # Time spent on back bar per rotation loop


@dataclass
class Encounter:
    """Encounter mechanics expressed as required capability IDs."""
    encounter_id: str
    mechanics: List[str] = field(default_factory=list)


@dataclass
class RosterPlayer:
    """A player and the source game objects currently available to them."""
    name: str
    choices: List[SourceGameObject] = field(default_factory=list)


@dataclass
class Roster:
    """A group to evaluate; it does not encode player assignments."""
    players: List[RosterPlayer] = field(default_factory=list)


@dataclass
class CompositionReport:
    """Coverage facts returned by CompositionEngine.evaluate."""
    mechanics: List[str]
    mechanic_coverage: dict[str, dict[str, List[str]]]
    uncovered_mechanics: List[str]
    duplicated_capabilities: dict[str, List[str]]

