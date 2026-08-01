# 🛠️ TODO: Build the ESO Rules Engine (The Console)

"baseAbilityId" = ability id


# skills
https://esolog.uesp.net/exportJson.php?table=playerSkills
skills.json /class_passives.json                    playerSkills
"cooldown" - cooldown
"duration" = time (in ms)
"maxRange" = range
"radius" = radius
"target" = type
"isPassive" = if 1 then Passive Class skill, if 0 then Class Skill

# gear_sets.json                                      setSummary or minedSets
all gear sets = esolog.uesp.net/exportJson.php?table=minedItemSummary&type=2
"setName"  = armor set name
"setBonusCount5" = bonus5AbilityId
"abilityCooldown" - ability cooldown 
"armorType" = armor weight (1=light, 2=medium, 3=heavy)

buff.json / debuffs.json /       buffSummary
champion_points.json                                esolog.uesp.net/exportJson.php?table=cp2Skills
foods.json / potions.json                           minedItemSummary (4,7,12)
encounters.json                       playerData



# status_effects.json
import json
import urllib.request

# Target the master buff table
url = "https://uesp.net"

print("Downloading master UESP buff data...")
try:
    response = urllib.request.urlopen(url)
    all_effects = json.loads(response.read().decode())
    
    buffs = []
    debuffs = []
    status_effects = []
    
    for effect in all_effects:
        desc = effect.get("description", "").lower()
        name = effect.get("name", "").lower()
        
        # Determine target file based on text triggers 
        # (Customize these conditions to match your application's logic rules)
        if "reduces" in desc or "decreases" in desc or "damage over time" in desc:
            debuffs.append(effect)
        elif name in ["chilled", "concussed", "burning", "poisoned", "hemorrhage"]:
            status_effects.append(effect)
        else:
            buffs.append(effect)
            
    # Save into your separate local files
    with open("buff.json", "w") as f:
        json.dump(buffs, f, indent=4)
    with open("debuffs.json", "w") as f:
        json.dump(debuffs, f, indent=4)
    with open("status_effects.json", "w") as f:
        json.dump(status_effects, f, indent=4)
        
    print(f"Success! Saved {len(buffs)} buffs, {len(debuffs)} debuffs, and {len(status_effects)} status effects.")

except Exception as e:
    print(f"Error extracting data: {e}")


# Damage types
    "0": "None / Generic",
    "1": "Physical Damage",
    "2": "Magic Damage",
    "3": "Flame Damage",
    "4": "Frost Damage",
    "5": "Shock Damage",
    "6": "Poison Damage",
    "7": "Disease Damage",
    "8": "Bleed Damage",
    "9": "Oblivion Damage"



- [ ] [I want to access this github https://github.com/Baertram/LibSets and grab the set info](https://en.m.uesp.net/wiki/User:Daveh/ESO_Log_Collector#Item_Types)
- [ ] Google suggested we pull this info from UESP to get the skills info

    // Target the live U50 skill description and coefficient tables
            async function fetchU50SkillData(skillName) {
                const url = `https://uesp.net{encodeURIComponent(skillName)}&format=json`;
                    try {
        const response = await fetch(url);
        const data = await response.json();
        return data; // Pipes out clean JSON arrays for your project elements
            } catch (error) {
        console.error("Pipeline extraction failed:", error);
            }
        }
- [ ] What if we import_trials.py, import_sets.py, import_bosses.py, import_skills.py, import_achievements.py, race info, food buffs, potion buffs to get this info? That way its always current. 
- [ ] comp builder would need a page to assign 12 players names and roles (2 tanks, 2 healers, 8 damage dealers)
- [ ] it would need at least 4 'pages' for different builds - genpop, Boss 1, Boss 2, Boss 3
- [ ] it would need to account for all the possible buffs a trial group can have, and show which ones are missing. 
- [ ] it would idealy identify if ppl were over penetration cap, over critical cap
- [ ] if we wanna get super fancy, it would suggest armor or skills that better suit the build if over a cap or are doubling up on a buff, but I can understand if thats too much lol
- [ ] There needs to be a spot to put the teams name, time(s) they play, and current goal
- [ ] My Bff Rylo has Epilepsy and has to actually count out a lot of mechs in the game bc he has to adjust his TV to where he cant see most of the AOEs. I'd love to make him a Boss mech counter that pulls up mechs and the times of things. Something he can read but also edit or make notes on.



## Vision

The Console is **not** a build planner.

It is a **raid operations platform** built around how experienced ESO players actually think and communicate.

The engine should never care that a player is wearing Spell Power Cure or has Pierce Armor slotted.

It should understand that the player provides **Major Courage** or **Major Breach**.

Everything in the game ultimately exists to answer three questions:

1. What does this player provide?
2. What does this encounter require?
3. Does the raid have everything it needs for the trial or dungeon they are in?

---

## Core Philosophy

Store **facts**, not calculations.

The database contains game data.

The engine performs calculations.

The UI presents capabilities.

Never duplicate logic.

---

## Data Flow

Game Object
↓
Trigger
↓
Action
↓
Effect
↓
Capability
↓
Calculation
↓
Raid Recommendation

Example:

Pierce Armor
→ On Hit
→ Apply Major Breach
→ Enemy Armor -5948
→ Capability: Breach
→ Raid Penetration Updated

---

## Engine Layers

### 1. Source Layer
Actual ESO objects.

- Skills
- Passives
- Champion Points
- Gear Sets
- Mythics
- Races
- Mundus
- Food
- Potions
- Buffs
- Debuffs

---

### 2. Rules Layer

The combat engine.

Responsible for:

- Damage Types
- Status Effects
- Buff application
- Debuff application
- Proc chances
- Trigger handling
- Conditional effects
- Stat calculations
- Caps
- Rating conversions

This is where ESO's combat rules live.

---

### 3. Capability Layer

The language real raid teams use.

Examples:

- Courage
- Breach
- Crusher
- Vuln
- Brittle
- Berserk
- EC
- Zen
- Horn
- Orbs
- Purge
- Magickasteal

The UI should speak in Capabilities, not gear names.

---

### 4. Operations Layer

Rylo's knowledge.

Contains:

- Boss mechanics
- Callouts
- Assignments
- Teaching notes
- Achievement strategies
- Team templates
- Progression notes

This is what makes The Console unique.

---

## Database Structure

/game_data/eso/

stats.json
damage_types.json
status_effects.json
buffs.json
debuffs.json

classes.json
skills.json
passives.json

champion_points.json

gear_sets.json
mythics.json

races.json
mundus.json
foods.json
potions.json

capabilities.json

encounters.json
mechanics.json
achievements.json

---

## Import Philosophy

Import only information that affects:

• Combat calculations
• Raid recommendations
• Boss mechanics
• Team composition

Ignore:

- Icons
- Flavor text
- Internal IDs (unless needed as stable keys)
- Models
- Animations
- Sounds
- Quest data
- Collectibles

---

## Combat Model

Every object should be describable as:

Trigger
→ Action
→ Effect

Examples:

On Hit
→ Apply Major Breach

On Critical
→ Restore Ultimate

On Damage
→ Spawn AoE

On Status Proc
→ Apply Burning

No special-case code whenever possible.

---

## Character Model

Characters should only store choices.

Class
Race
Food
Mundus
Gear
Skills
Champion Points

Everything else is calculated.

---

## Raid Model

Raids should not ask:

"Who has Spell Power Cure?"

They should ask:

"Who provides Courage?"

Likewise:

Not:
"Who's wearing Turning Tide?"

Instead:
"Who covers Major Vulnerability?"

The Console should think exactly like experienced raid leaders.

---

## Long-Term Goal

The Console becomes a combat simulation and raid operations platform capable of:

• Optimizing builds
• Optimizing raid compositions
• Verifying buff/debuff coverage
• Calculating player statistics
• Simulating combat interactions
• Teaching mechanics
• Planning achievements
• Recording progression
• Providing actionable recommendations

The engine should be generic.

ESO becomes data.
The Console becomes the brain.

# Core Data Structures
import json
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional

@dataclass
class CombatEffect:
    """The generic payload representing an absolute modifier or system state."""
    capability_id: str          # e.g., "breach_major", "courage_major", "ec_fire"
    stat_modified: str          # e.g., "armor", "weapon_spell_damage", "crit_damage"
    modification_value: float   # e.g., -5948, 430, 15.0
    is_percent: bool = False

@dataclass
class DynamicTrigger:
    """The operational condition layer."""
    condition_type: str         # e.g., "on_hit", "on_crit", "on_slotted", "on_equip"
    target: str                 # e.g., "self", "enemy", "group"
    effects: List[CombatEffect] = field(default_factory=list)

@dataclass
class SourceGameObject:
    """Universal schema representing any Layer 1 object (Skill, Set, Food, etc.)."""
    id: str                     # Stable lookup key (e.g., "skill_pierce_armor")
    name: str                   # Human readable display name
    source_layer: str           # "skills", "gear_sets", "mundus", etc.
    triggers: List[DynamicTrigger] = field(default_factory=list)

# Core Implementation Layer
class TheConsoleEngine:
    def __init__(self, pvp_rules: bool = False):
        self.is_pvp = pvp_rules
        self.mitigation_constant = 660.0 if pvp_rules else 500.0

    def flatten_character_capabilities(self, choices: List[SourceGameObject]) -> Dict[str, CombatEffect]:
        """Layer 3: Reductor pipeline translating choices into exact unique capabilities.
        
        If multiple items provide 'Major Courage', this deduplicates them cleanly,
        storing the unique fact without duplicating calculation loops.
        """
        active_capabilities = {}
        for game_object in choices:
            for trigger in game_object.triggers:
                # Passive elements like Mundus, Food, or Class Passives are evaluated on 'slotted/equipped'
                if trigger.condition_type in ["on_slotted", "on_equip", "on_hit"]:
                    for effect in trigger.effects:
                        # Deduplicate by absolute Capability ID
                        active_capabilities[effect.capability_id] = effect
        return active_capabilities

    def compile_raid_matrix(self, roster_choices: Dict[str, List[SourceGameObject]]) -> Dict[str, CombatEffect]:
        """Aggregates all 12 unique player choice vectors into a single global group matrix."""
        global_capabilities = {}
        for player_name, choices in roster_choices.items():
            player_caps = self.flatten_character_capabilities(choices)
            global_capabilities.update(player_caps) # Overwrites duplicates naturally
        return global_capabilities

    def evaluate_encounter_operation(
        self, 
        global_capabilities: Dict[str, CombatEffect], 
        base_boss_armor: int,
        required_mechanics: Set[str]
    ) -> Dict:
        """Layer 4: Connects group capabilities straight to boss mechanics and math realities."""
        
        # --- RULES CALCULATION LAYER ---
        # 1. Resolve Group Debuffs against Boss Armor
        flat_armor_reductions = 0
        crit_damage_bonuses = 0.0
        
        for cap_id, effect in global_capabilities.items():
            if effect.stat_modified == "armor":
                # Sum flat absolute debuffs (e.g., Major Breach, Minor Breach, Crusher)
                flat_armor_reductions += abs(effect.modification_value)
            elif effect.stat_modified == "crit_damage" and effect.is_percent:
                crit_damage_bonuses += effect.modification_value

        effective_boss_armor = max(0, base_boss_armor - flat_armor_reductions)
        mitigation_pct = (effective_armor := effective_boss_armor) / self.mitigation_constant
        
        # 2. Map group capability strings directly to the interface requirements
        present_capabilities = set(global_capabilities.keys())
        missing_operational_requirements = required_mechanics - present_capabilities

        return {
            "group_penetration_status": {
                "initial_armor": base_boss_armor,
                "effective_armor": effective_armor,
                "boss_mitigation_percentage": round(mitigation_pct, 2),
                "shredded_armor_total": flat_armor_reductions
            },
            "group_crit_damage_bonus_percentage": round(min(crit_damage_bonuses, 125.0), 2), # Capped via rules layer
            "operational_audit": {
                "has_all_requirements": len(missing_operational_requirements) == 0,
                "missing_capabilities": list(missing_operational_requirements),
                "active_capabilities_logged": list(present_capabilities)
            }
        }

# Simulating a Pre-Fight Production Run
if __name__ == "__main__":
    # --- MOCKING /game_data/eso/skills.json & gear_sets.json ---
    # Pierce Armor -> On Hit -> Apply Major Breach (-5948 Armor)
    pierce_armor_skill = SourceGameObject(
        id="skill_pierce_armor", name="Pierce Armor", source_layer="skills",
        triggers=[DynamicTrigger(condition_type="on_hit", target="enemy", effects=[
            CombatEffect(capability_id="Breach", stat_modified="armor", modification_value=-5948)
        ])]
    )

    # Spell Power Cure -> On Heal -> Apply Major Courage (+430 Power)
    spc_gear_set = SourceGameObject(
        id="set_spell_power_cure", name="Spell Power Cure", source_layer="gear_sets",
        triggers=[DynamicTrigger(condition_type="on_equip", target="group", effects=[
            CombatEffect(capability_id="Courage", stat_modified="weapon_spell_damage", modification_value=430)
        ])]
    )

    # --- MOCKING /game_data/eso/encounters.json ---
    # A high end trial boss requiring deep structural utilities
    trial_boss_profile = {
        "name": "Lucent Citadel Boss",
        "base_armor": 18200,
        "required_capabilities": {"Breach", "Courage", "Purge"}
    }

    # --- SIMULATING THE ACTIVE ROSTER PACKAGES ---
    # The platform loops through choices uploaded by your 12 players
    current_raid_choices = {
        "Main_Tank": [create_obj := pierce_armor_skill],
        "Group_Healer": [create_obj := spc_gear_set],
        "DPS_Player1": []
    }

    # Execute platform pipeline processes
    console_engine = TheConsoleEngine(pvp_rules=False)
    
    # 1. Compile state profiles
    raid_matrix = console_engine.compile_raid_matrix(current_raid_choices)
    
    # 2. Run operational audit against the boss profile metrics
    dashboard_output = console_engine.evaluate_encounter_operation(
        global_capabilities=raid_matrix,
        base_boss_armor=trial_boss_profile["base_armor"],
        required_mechanics=trial_boss_profile["required_capabilities"]
    )

    # --- TRANSMITTING RESPONSE SCHEMA TO APP UI ---
    print("=== THE CONSOLE: OPERATIONS ROOM REPORT ===")
    print(f"Operational Audit Status: {'CLEAR FOR ACTION' if dashboard_output['operational_audit']['has_all_requirements'] else 'COMPOSITION WARNING'}")
    print(f"Missing Strategic Capabilities: {dashboard_output['operational_audit']['missing_capabilities']}")
    print(f"\nPenetration Calculation Output:")
    print(f" -> Boss Armor Dropped to: {dashboard_output['group_penetration_status']['effective_armor']} points.")
    print(f" -> Resulting Mitigation: {dashboard_output['group_penetration_status']['boss_mitigation_percentage']}% damage reduction.")


## Separation of Concerns (SoC) architectural pattern Crit Chance/Percent & Penetraction
from dataclasses import dataclass, field

@dataclass(frozen=True)
class CombatScalingRules:
    """Universal system constants and hard caps for ESO mechanics."""
    # Critical Chance scaling
    BASE_CRIT_CHANCE: float = 10.0
    CRIT_CHANCE_RATING_SCALE: float = 219.0
    CRIT_CHANCE_CAP: float = 100.0

    # Critical Damage scaling
    BASE_CRIT_DAMAGE_MODIFIER: float = 50.0
    CRIT_DAMAGE_BONUS_CAP: float = 125.0

    # Armor & Mitigation scaling
    PVE_ARMOR_MITIGATION_SCALE: float = 500.0
    PVP_ARMOR_MITIGATION_SCALE: float = 660.0
    PVP_MITIGATION_CAP: float = 50.0

@dataclass
class AttackerState:
    """The offensive profile of the attacking character."""
    raw_base_damage: float
    flat_crit_rating: float
    crit_damage_modifiers: list[float] = field(default_factory=list)
    flat_penetration: int = 0

@dataclass
class DefenderState:
    """The defensive profile of the target."""
    base_armor: int
    active_armor_debuffs: list[int] = field(default_factory=list)
    is_player: bool = False


class CriticalChanceCalculator:
    def __init__(self, rules: CombatScalingRules):
        self._rules = rules

    def calculate(self, flat_rating: float) -> float:
        total = self._rules.BASE_CRIT_CHANCE + (flat_rating / self._rules.CRIT_CHANCE_RATING_SCALE)
        return min(total, self._rules.CRIT_CHANCE_CAP)


class CriticalDamageCalculator:
    def __init__(self, rules: CombatScalingRules):
        self._rules = rules

    def get_multiplier(self, bonus_modifiers: list[float]) -> float:
        applied_bonus = min(sum(bonus_modifiers), self._rules.CRIT_DAMAGE_BONUS_CAP)
        return 1.0 + ((self._rules.BASE_CRIT_DAMAGE_MODIFIER + applied_bonus) / 100.0)


class ArmorMitigationCalculator:
    def __init__(self, rules: CombatScalingRules):
        self._rules = rules

    def get_mitigation_factor(self, defender: DefenderState, player_penetration: int) -> float:
        # 1. Deduct group debuffs first, then flat player penetration
        armor_after_debuffs = max(0, defender.base_armor - sum(defender.active_armor_debuffs))
        effective_armor = max(0, armor_after_debuffs - player_penetration)
        
        # 2. Select appropriate scaling constant
        scale = self._rules.PVP_ARMOR_MITIGATION_SCALE if defender.is_player else self._rules.PVE_ARMOR_MITIGATION_SCALE
        mitigation_percent = effective_armor / scale
        
        # 3. Enforce PvP mitigation ceiling
        if defender.is_player:
            mitigation_percent = min(mitigation_percent, self._rules.PVP_MITIGATION_CAP)
            
        return 1.0 - (mitigation_percent / 100.0)


class CombatSimulationService:
    def __init__(self, rules: CombatScalingRules = CombatScalingRules()):
        # Inject dependency components
        self.crit_chance_calc = CriticalChanceCalculator(rules)
        self.crit_damage_calc = CriticalDamageCalculator(rules)
        self.mitigation_calc = ArmorMitigationCalculator(rules)

    def run_simulation(self, attacker: AttackerState, defender: DefenderState) -> dict[str, float]:
        """Orchestrates individual modules to calculate final expected damage output."""
        # Execute isolated responsibilities
        chance = self.crit_chance_calc.calculate(attacker.flat_crit_rating)
        multiplier = self.crit_damage_calc.get_multiplier(attacker.crit_damage_modifiers)
        mitigation = self.mitigation_calc.get_mitigation_factor(defender, attacker.flat_penetration)
        
        # Process damage transformations
        normal_hit = attacker.raw_base_damage * mitigation
        critical_hit = normal_hit * multiplier
        
        # Calculate statistically weighed average damage (DPS baseline)
        chance_fraction = chance / 100.0
        avg_damage = (normal_hit * (1.0 - chance_fraction)) + (critical_hit * chance_fraction)
        
        return {
            "crit_chance_percent": round(chance, 2),
            "crit_multiplier": round(multiplier, 2),
            "mitigation_percent": round((1.0 - mitigation) * 100, 2),
            "damage_normal_hit": round(normal_hit, 2),
            "damage_critical_hit": round(critical_hit, 2),
            "average_expected_damage": round(avg_damage, 2)
        }


## Damage
def calculate_eso_hit(
    max_resource: int,
    power_stat: int,
    coeff_a: float,
    coeff_b: float,
    damage_done_modifiers: list[float],
    crit_damage_modifiers: list[float],
    is_crit: bool,
    enemy_armor: int,
    armor_debuffs: list[int],
    player_penetration: int,
    is_pvp: bool = False
) -> float:
    
    # Layer 1: Base Tooltip Scaling
    base_tooltip = (max_resource * coeff_a) + (power_stat * coeff_b)
    
    # Layer 2: Damage Done Modifiers
    modified_base = base_tooltip * (1.0 + (sum(damage_done_modifiers) / 100.0))
    
    # Layer 3: Critical Strike Layer
    if is_crit:
        bonus_crit = min(sum(crit_damage_modifiers), 125.0) # 125% hard cap
        crit_multiplier = 1.0 + ((50.0 + bonus_crit) / 100.0)
        attack_power = modified_base * crit_multiplier
    else:
        attack_power = modified_base
        
    # Layer 4: Armor Mitigation
    effective_armor = max(0, enemy_armor - sum(armor_debuffs) - player_penetration)
    scale = 660.0 if is_pvp else 500.0
    mitigation_percent = effective_armor / scale
    
    if is_pvp:
        mitigation_percent = min(mitigation_percent, 50.0) # 50% mitigation cap
        
    mitigation_factor = 1.0 - (mitigation_percent / 100.0)
    
    # Return Final Output
    return round(attack_power * mitigation_factor, 2)


## Damage with Skills
from dataclasses import dataclass

@dataclass(frozen=True)
class SkillCoefficients:
    coeff_a: float  # Multiplier for Max Resource (Magicka or Stamina)
    coeff_b: float  # Multiplier for Power Stat (Spell or Weapon Damage)

# Reference baseline library of popular class skills
ESO_SKILL_DATABASE = {
    # Nightblade
    "surprise_attack": SkillCoefficients(coeff_a=0.0754, coeff_b=0.7915),
    "impale_execute_base": SkillCoefficients(coeff_a=0.0632, coeff_b=0.6631), # Scales up to 300% on low health
    
    # Dragonknight
    "whip_molten": SkillCoefficients(coeff_a=0.0815, coeff_b=0.8552),
    "venomous_claw_tick": SkillCoefficients(coeff_a=0.0210, coeff_b=0.2205), # Ramp-up DoT
    
    # Sorcerer
    "crystal_fragments": SkillCoefficients(coeff_a=0.1102, coeff_b=1.1570),
    "daedric_prey": SkillCoefficients(coeff_a=0.0721, coeff_b=0.7570),
    
    # Templar
    "biting_jabs_per_hit": SkillCoefficients(coeff_a=0.0245, coeff_b=0.2572), # Hits multiple times
    "radiant_oppression_base": SkillCoefficients(coeff_a=0.0512, coeff_b=0.5376), # Executes up to 480%
    
    # Arcanist
    "fatecarver_per_tick": SkillCoefficients(coeff_a=0.0195, coeff_b=0.2048)  # Channeled Beam ticks
}

def calculate_base_tooltip(skill_name: str, max_mag: int, max_stam: int, spell_dmg: int, wpn_dmg: int) -> float:
    """Calculates base tooltip using Dynamic Hybridization Scaling."""
    if skill_name not in ESO_SKILL_DATABASE:
        raise ValueError(f"Skill {skill_name} not found in database.")
        
    skill = ESO_SKILL_DATABASE[skill_name]
    
    # Game engine identifies your highest offensive stats
    highest_resource = max(max_mag, max_stam)
    highest_power = max(spell_dmg, wpn_dmg)
    
    return (highest_resource * skill.coeff_a) + (highest_power * skill.coeff_b)


## Damage with Effects
@dataclass(frozen=True)
class StatusConstants:
    # Baseline coefficients assigned directly to status effects by the game system
    DIRECT_BURST_COEFF_A: float = 0.0152
    DIRECT_BURST_COEFF_B: float = 0.1602
    
    DOT_TICK_COEFF_A: float = 0.0095
    DOT_TICK_COEFF_B: float = 0.0998

class StatusEffectEngine:
    def __init__(self, constants: StatusConstants = StatusConstants()):
        self._c = constants

    def calculate_status_base(self, effect_name: str, max_resource: int, power_stat: int) -> dict:
        """Computes base performance arrays for status effects before armor/crit."""
        
        # Categorize the status effects to match game engine behavior
        dot_statuses = ["burning", "poisoned", "hemorrhaging"]
        direct_statuses = ["sundered", "chilled", "concussed", "overcharged", "diseased"]
        
        effect = effect_name.lower()
        
        if effect in direct_statuses:
            # Flat burst calculation
            base_damage = (max_resource * self._c.DIRECT_BURST_COEFF_A) + (power_stat * self._c.DIRECT_BURST_COEFF_B)
            return {"type": "Direct", "total_ticks": 1, "damage_per_tick": round(base_damage, 2)}
            
        elif effect in dot_statuses:
            # 4-second duration tracking (ticks every 1 second)
            base_tick = (max_resource * self._c.DOT_TICK_COEFF_A) + (power_stat * self._c.DOT_TICK_COEFF_B)
            
            # Hemorrhaging features stacking behavior up to 3 times
            return {"type": "DoT", "total_ticks": 4, "damage_per_tick": round(base_tick, 2)}
            
        else:
            raise ValueError("Unknown status effect type.")

# --- Demo Integration Testing ---
if __name__ == "__main__":
    engine = StatusEffectEngine()
    
    # A player with 42,000 Magicka and 5,500 Spell Damage
    mag, pwr = 42000, 5500
    
    burning_profile = engine.calculate_status_base("burning", mag, pwr)
    sundered_profile = engine.calculate_status_base("sundered", mag, pwr)
    
    print(f"Burning Tick Damage: {burning_profile['damage_per_tick']} per second (Total Ticks: {burning_profile['total_ticks']})")
    print(f"Sundered Burst Damage: {sundered_profile['damage_per_tick']} (Instant)")



## Proc Enchants
from dataclasses import dataclass

@dataclass(frozen=True)
class WeaponTraitBaselines:
    """The default value of weapon traits at Legendary (Gold) quality."""
    # Charged increases status effect chance
    CHARGED_1H: float = 117.5
    CHARGED_2H: float = 235.0
    
    # Infused boosts enchant power and cuts cooldowns
    INFUSED_COOL_DOWN_REDUCTION_PCT: float = 50.0
    INFUSED_ENCHANT_POWER_BOOST_PCT: float = 30.0

@dataclass(frozen=True)
class EnchantmentBaselines:
    """Baseline tracking for standard ESO damage glyphs (e.g., Flame/Frost)."""
    BASE_COOLDOWN_SECONDS: float = 4.0

from enum import Enum

class WeaponSlotType(Enum):
    ONE_HANDED = "1h"
    TWO_HANDED = "2h"

class ActiveTrait(Enum):
    NONE = "none"
    CHARGED = "charged"
    INFUSED = "infused"

@dataclass
class EquippedWeaponProfile:
    slot_type: WeaponSlotType
    trait: ActiveTrait
    has_heartland_conqueror: bool = False  # 5pc set bonus toggled via UI checkbox


from enum import Enum

class DamageSourceType(Enum):
    ENCHANT_OR_POISON = 20.0
    ST_DIRECT = 10.0
    AOE_DIRECT = 5.0
    ST_DOT = 3.0
    AOE_DOT = 1.0
    LIGHT_HEAVY_ATTACK = 0.0

class WeaponSystemEngine:
    def __init__(self, traits=WeaponTraitBaselines(), enchants=EnchantmentBaselines()):
        self._traits = traits
        self._enchants = enchants

    def calculate_trait_modifier(self, weapon: EquippedWeaponProfile) -> dict[str, float]:
        """Calculates exact status bonus and cooldown changes based on traits and sets."""
        # 1. Evaluate Heartland Conqueror's 2x multiplier
        trait_multiplier = 2.0 if weapon.has_heartland_conqueror else 1.0
        
        status_modifier = 0.0
        cooldown_reduction_pct = 0.0
        enchant_power_multiplier = 1.0

        # 2. Extract values based on trait choice and slot scaling
        if weapon.trait == ActiveTrait.CHARGED:
            base_charged = self._traits.CHARGED_2H if weapon.slot_type == WeaponSlotType.TWO_HANDED else self._traits.CHARGED_1H
            status_modifier = base_charged * trait_multiplier
            
        elif weapon.trait == ActiveTrait.INFUSED:
            cooldown_reduction_pct = self._traits.INFUSED_COOL_DOWN_REDUCTION_PCT * trait_multiplier
            power_boost = self._traits.INFUSED_ENCHANT_POWER_BOOST_PCT * trait_multiplier
            enchant_power_multiplier = 1.0 + (power_boost / 100.0)

        return {
            "status_modifier": status_modifier,
            "cooldown_reduction_pct": cooldown_reduction_pct,
            "enchant_power_multiplier": enchant_power_multiplier
        }

    def process_weapon_combat_state(
        self, 
        source_type: DamageSourceType, 
        weapon: EquippedWeaponProfile, 
        other_passives_sum: float = 0.0
    ) -> dict[str, float]:
        """Computes both the precise status effect proc chance AND enchantment cooldown metrics."""
        
        # 1. Resolve weapon trait configurations
        trait_data = self.calculate_trait_modifier(weapon)
        
        # 2. Calculate Final Proc Chance Percentage
        base_chance = source_type.value
        if base_chance == 0.0:
            final_proc_chance = 0.0
        else:
            total_modifiers = other_passives_sum + trait_data["status_modifier"]
            final_proc_chance = min(base_chance * (1.0 + (total_modifiers / 100.0)), 100.0)

        # 3. Calculate Enchantment Internal Cooldown (ICD)
        # Reduction cannot exceed 100% mathematically; Infused caps naturally via rules
        reduction_factor = 1.0 - (trait_data["cooldown_reduction_pct"] / 100.0)
        # Handle cases where reduction overshoots to prevent negative scaling
        reduction_factor = max(0.0, reduction_factor)
        
        final_cooldown = self._enchants.BASE_COOLDOWN_SECONDS * reduction_factor

        return {
            "proc_chance_percent": round(final_proc_chance, 2),
            "enchantment_cooldown_seconds": round(final_cooldown, 2),
            "enchantment_potency_multiplier": round(trait_data["enchant_power_multiplier"], 2)
        }

# Running App Simulator Validations
if __name__ == "__main__":
    engine = WeaponSystemEngine()
    
    # Destro staff passives or Champion Points (e.g., +160% combined)
    external_buffs = 160.0 

    # --- SETUP 1: The Status Effect Spammer ---
    # Player builds a 2-Handed Charged weapon paired with Heartland Conqueror
    charged_hc_weapon = EquippedWeaponProfile(
        slot_type=WeaponSlotType.TWO_HANDED,
        trait=ActiveTrait.CHARGED,
        has_heartland_conqueror=True
    )
    
    # Test on an Area of Effect Direct damage skill (5% base)
    charged_results = engine.process_weapon_combat_state(
        DamageSourceType.AOE_DIRECT, 
        charged_hc_weapon, 
        other_passives_sum=external_buffs
    )

    # --- SETUP 2: The Fast Cooldown Machine ---
    # Player builds a 1-Handed Infused weapon paired with Heartland Conqueror
    infused_hc_weapon = EquippedWeaponProfile(
        slot_type=WeaponSlotType.ONE_HANDED,
        trait=ActiveTrait.INFUSED,
        has_heartland_conqueror=True
    )
    
    # Test on a Weapon Enchantment trigger (20% base)
    infused_results = engine.process_weapon_combat_state(
        DamageSourceType.ENCHANT_OR_POISON, 
        infused_hc_weapon, 
        other_passives_sum=external_buffs
    )

    # --- App Output Prints ---
    print("=== SCENARIO 1: 2H Charged + Heartland Conqueror ===")
    print(f"AoE Skill Proc Chance: {charged_results['proc_chance_percent']}%") 
    print(f"Enchant Cooldown: {charged_results['enchantment_cooldown_seconds']}s")
    
    print("\n=== SCENARIO 2: 1H Infused + Heartland Conqueror ===")
    print(f"Enchantment Proc Chance: {infused_results['proc_chance_percent']}%")
    print(f"Enchant Cooldown: {infused_results['enchantment_cooldown_seconds']}s (Dropped from 4s baseline!)")
    print(f"Enchant Damage Multiplier: {infused_results['enchantment_potency_multiplier']}x")


## Skill Damage

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict

class EffectType(Enum):
    BUFF = "buff"                # Modifies attacker or defender stats
    DAMAGE_OVER_TIME = "dot"     # Deals damage every interval

@dataclass
class ActiveEffect:
    name: str
    effect_type: EffectType
    duration_ticks: int          # Remaining lifetime in system ticks
    tick_interval: int           # How many ticks pass between executions (e.g., 10 ticks = 1 sec)
    value: float                 # The stat increase OR the base tick damage
    time_since_last_tick: int = 0

@dataclass
class CombatEntity:
    name: str
    max_health: float
    current_health: float
    base_armor: int
    flat_penetration: int = 0
    damage_done_modifiers: List[float] = field(default_factory=list) # e.g., Minor Berserk
    active_effects: Dict[str, ActiveEffect] = field(default_factory=dict)

    def apply_effect(self, effect: ActiveEffect):
        """Applies or refreshes a lingering effect on the entity."""
        self.active_effects[effect.name] = effect


class ActiveCombatEngine:
    def __init__(self, tick_rate_seconds: float = 0.1):
        self.tick_rate = tick_rate_seconds
        self.total_ticks_elapsed = 0

    def process_tick(self, attacker: CombatEntity, defender: CombatEntity) -> List[str]:
        """Advances the entire fight forward by one engine tick (100ms)."""
        self.total_ticks_elapsed += 1
        combat_log = []

        # 1. Update/Recalculate dynamic states from active buffs
        self._refresh_entity_modifiers(attacker)
        self._refresh_entity_modifiers(defender)

        # 2. Process active effects ticking down on entities
        # We use list(dict.keys()) to allow safe deletion during iterations when durations hit 0
        for effect_name in list(defender.active_effects.keys()):
            effect = defender.active_effects[effect_name]
            effect.duration_ticks -= 1
            effect.time_since_last_tick += 1

            # Check if it's time for a DoT effect to strike
            if effect.effect_type == EffectType.DAMAGE_OVER_TIME:
                if effect.time_since_last_tick >= effect.tick_interval:
                    damage_dealt = self._execute_dot_damage(attacker, defender, effect.value)
                    defender.current_health = max(0.0, defender.current_health - damage_dealt)
                    effect.time_since_last_tick = 0 # Reset interval timer
                    
                    time_sec = self.total_ticks_elapsed * self.tick_rate
                    combat_log.append(
                        f"[{time_sec:.1f}s] {defender.name} takes {damage_dealt:.2f} damage from {effect.name} DoT."
                    )

            # Clean up expired skills/buffs
            if effect.duration_ticks <= 0:
                del defender.active_effects[effect_name]
                time_sec = self.total_ticks_elapsed * self.tick_rate
                combat_log.append(f"[{time_sec:.1f}s] Effect '{effect_name}' has expired on {defender.name}.")

        return combat_log

    def cast_instant_skill(self, skill_name: str, base_damage: float, attacker: CombatEntity, defender: CombatEntity) -> str:
        """Processes an instant direct-damage attack immediately."""
        # Layer 1 & 2: Base Damage + Additive Attacker Buffs
        modified_damage = base_damage * (1.0 + (sum(attacker.damage_done_modifiers) / 100.0))
        
        # Layer 3: Armor Mitigation
        effective_armor = max(0, defender.base_armor - attacker.flat_penetration)
        mitigation_factor = 1.0 - (effective_armor / 500.0 / 100.0)
        
        final_damage = round(modified_damage * mitigation_factor, 2)
        defender.current_health = max(0.0, defender.current_health - final_damage)
        
        time_sec = self.total_ticks_elapsed * self.tick_rate
        return f"[{time_sec:.1f}s] {attacker.name} casts {skill_name}! Direct hit on {defender.name} for {final_damage:.2f}."

    def _execute_dot_damage(self, attacker: CombatEntity, defender: CombatEntity, base_tick_value: float) -> float:
        """Helper to run localized calculations specifically for a DoT interval."""
        # DoTs scale via the attacker's dynamic active state during that specific tick
        modified_damage = base_tick_value * (1.0 + (sum(attacker.damage_done_modifiers) / 100.0))
        effective_armor = max(0, defender.base_armor - attacker.flat_penetration)
        mitigation_factor = 1.0 - (effective_armor / 500.0 / 100.0)
        return modified_damage * mitigation_factor

    def _refresh_entity_modifiers(self, entity: CombatEntity):
        """Scans active buffs to rebuild temporary combat properties."""
        # Wipe temporary stat modifications to clear the previous tick's state
        entity.damage_done_modifiers = []
        
        for effect in entity.active_effects.values():
            if effect.effect_type == EffectType.BUFF:
                if effect.name == "Minor Berserk":
                    entity.damage_done_modifiers.append(effect.value)


### Python Rotation & Priority Queue Engine
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional

class EffectType(Enum):
    BUFF = "buff"
    DAMAGE_OVER_TIME = "dot"

@dataclass
class ActiveEffect:
    name: str
    effect_type: EffectType
    duration_ticks: int
    tick_interval: int
    value: float
    time_since_last_tick: int = 0

@dataclass
class CombatEntity:
    name: str
    max_health: float
    current_health: float
    base_armor: int
    flat_penetration: int = 0
    damage_done_modifiers: List[float] = field(default_factory=list)
    active_effects: Dict[str, ActiveEffect] = field(default_factory=dict)

    def apply_effect(self, effect: ActiveEffect):
        self.active_effects[effect.name] = effect

    def is_effect_active(self, name: str, threshold_ticks: int = 10) -> bool:
        """Returns True if the effect is active and has more than threshold_ticks remaining.
        
        This prevents the AI from clipping/overwriting a DoT early.
        """
        if name not in self.active_effects:
            return False
        return self.active_effects[name].duration_ticks > threshold_ticks


@dataclass
class RotationSkill:
    name: str
    is_dot: bool
    base_damage: float           # Direct damage or per-tick DoT damage
    duration_seconds: float = 0.0 # Only applicable if it's a DoT
    priority: int = 1             # Higher number = higher priority in the queue


class AdvancedRotationEngine:
    def __init__(self, tick_rate_seconds: float = 0.1):
        self.tick_rate = tick_rate_seconds
        self.total_ticks_elapsed = 0
        self.player_gcd_ticks = 0  # Global Cooldown counter in engine ticks

    def process_tick(self, attacker: CombatEntity, defender: CombatEntity, skill_db: List[RotationSkill]) -> List[str]:
        """Steps the universe forward by 100ms, ticking DoTs and managing player GCDs."""
        self.total_ticks_elapsed += 1
        combat_log = []
        time_sec = self.total_ticks_elapsed * self.tick_rate

        # 1. Decelerate active timers
        if self.player_gcd_ticks > 0:
            self.player_gcd_ticks -= 1

        # 2. Process active DoT effects on the target
        for effect_name in list(defender.active_effects.keys()):
            effect = defender.active_effects[effect_name]
            effect.duration_ticks -= 1
            effect.time_since_last_tick += 1

            if effect.effect_type == EffectType.DAMAGE_OVER_TIME and effect.time_since_last_tick >= effect.tick_interval:
                damage = self._calculate_mitigated_damage(attacker, defender, effect.value)
                defender.current_health = max(0.0, defender.current_health - damage)
                effect.time_since_last_tick = 0
                combat_log.append(f"[{time_sec:.1f}s] [DoT Tick] {effect_name} hits for {damage:.2f}.")

            if effect.duration_ticks <= 0:
                del defender.active_effects[effect_name]
                combat_log.append(f"[{time_sec:.1f}s] [Status] DoT '{effect_name}' has expired.")

        # 3. If player is off GCD, evaluate Priority Queue and cast the optimal skill
        if self.player_gcd_ticks == 0 and defender.current_health > 0:
            optimal_skill = self._evaluate_priority_queue(defender, skill_db)
            
            if optimal_skill:
                cast_log = self._execute_skill_cast(attacker, defender, optimal_skill)
                combat_log.append(cast_log)
                self.player_gcd_ticks = 10  # Enforce 1.0s Global Cooldown (10 ticks * 0.1s)

        return combat_log

    def _evaluate_priority_queue(self, defender: CombatEntity, skill_db: List[RotationSkill]) -> Optional[RotationSkill]:
        """Analyzes active target conditions to select the highest priority valid skill."""
        # Sort skills by priority descending (highest priority evaluated first)
        sorted_skills = sorted(skill_db, key=lambda s: s.priority, reverse=True)

        for skill in sorted_skills:
            if skill.is_dot:
                # Priority logic: Only cast if the DoT is completely absent or expiring in under 1 second
                if not defender.is_effect_active(skill.name, threshold_ticks=10):
                    return skill
            else:
                # Spammables/Fillers have no target execution rules; they are always valid
                return skill
        return None

    def _execute_skill_cast(self, attacker: CombatEntity, defender: CombatEntity, skill: RotationSkill) -> str:
        """Handles the mathematical applications of a chosen action."""
        time_sec = self.total_ticks_elapsed * self.tick_rate
        
        if skill.is_dot:
            # Construct a dynamic tracking effect object
            total_duration_ticks = int(skill.duration_seconds / self.tick_rate)
            dot_effect = ActiveEffect(
                name=skill.name,
                effect_type=EffectType.DAMAGE_OVER_TIME,
                duration_ticks=total_duration_ticks,
                tick_interval=10, # Tick every 1.0 second
                value=skill.base_damage
            )
            defender.apply_effect(dot_effect)
            return f"[{time_sec:.1f}s] [Cast] {attacker.name} applies DoT '{skill.name}' (Priority {skill.priority})."
        else:
            # Compute immediate direct damage hit
            damage = self._calculate_mitigated_damage(attacker, defender, skill.base_damage)
            defender.current_health = max(0.0, defender.current_health - damage)
            return f"[{time_sec:.1f}s] [Cast] {attacker.name} fires Spammable '{skill.name}' for {damage:.2f} damage."

    def _calculate_mitigated_damage(self, attacker: CombatEntity, defender: CombatEntity, base_val: float) -> float:
        """Re-evaluates player/target math rules for any given combat hit."""
        modified = base_val * (1.0 + (sum(attacker.damage_done_modifiers) / 100.0))
        effective_armor = max(0, defender.base_armor - attacker.flat_penetration)
        mitigation = 1.0 - (effective_armor / 500.0 / 100.0)
        return modified * mitigation

### Simulating a 10-Second Automated Rotation
if __name__ == "__main__":
    # 1. Define the skill rules database
    # High priority actions sit at the top of the logic layer
    my_skills = [
        RotationSkill(name="Vampire's Bane", is_dot=True, base_damage=1800.0, duration_seconds=12.0, priority=3),
        RotationSkill(name="Purifying Light", is_dot=True, base_damage=2500.0, duration_seconds=6.0, priority=2),
        RotationSkill(name="Puncturing Sweep", is_dot=False, base_damage=4200.0, priority=1) # Spammable Filler
    ]

    # 2. Define entities
    templar = CombatEntity(name="Templar", max_health=22000, current_health=22000, base_armor=0, flat_penetration=3000)
    dummy_boss = CombatEntity(name="Target Dummy", max_health=500000, current_health=500000, base_armor=9100)

    # 3. Instantiate Engine
    engine = AdvancedRotationEngine(tick_rate_seconds=0.1)

    print("--- 10-SECOND AUTOMATED PRIORITY ROTATION ---")
    
    # Run the engine loops for 10.0 seconds (100 loops)
    for _ in range(100):
        logs = engine.process_tick(attacker=templar, defender=dummy_boss, skill_db=my_skills)
        for log in logs:
            print(log)

    print("---------------------------------------------")
    print(f"Target Dummy Remaining Health: {round(dummy_boss.current_health, 2)}")

### Roto with Resouce Restraints
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional

class ResourceType(Enum):
    MAGICKA = "magicka"
    STAMINA = "stamina"
    NONE = "none"

class EffectType(Enum):
    BUFF = "buff"
    DAMAGE_OVER_TIME = "dot"

@dataclass
class ActiveEffect:
    name: str
    effect_type: EffectType
    duration_ticks: int
    tick_interval: int
    value: float
    time_since_last_tick: int = 0

@dataclass
class CombatEntity:
    name: str
    max_health: float
    current_health: float
    base_armor: int
    flat_penetration: int = 0
    
    # Resource Pools
    max_magicka: int = 30000
    current_magicka: float = 30000.0
    magicka_recovery: int = 1200  # Restored every 2.0 seconds
    
    max_stamina: int = 30000
    current_stamina: float = 30000.0
    stamina_recovery: int = 1200   # Restored every 2.0 seconds
    
    damage_done_modifiers: List[float] = field(default_factory=list)
    active_effects: Dict[str, ActiveEffect] = field(default_factory=dict)

    def is_effect_active(self, name: str, threshold_ticks: int = 10) -> bool:
        if name not in self.active_effects:
            return False
        return self.active_effects[name].duration_ticks > threshold_ticks


@dataclass
class ResourceSkill:
    name: str
    is_dot: bool
    base_damage: float
    resource_type: ResourceType
    cost: int
    duration_seconds: float = 0.0
    priority: int = 1


class ResourceCombatEngine:
    def __init__(self, tick_rate_seconds: float = 0.1):
        self.tick_rate = tick_rate_seconds
        self.total_ticks_elapsed = 0
        self.player_gcd_ticks = 0

    def process_tick(self, attacker: CombatEntity, defender: CombatEntity, skill_db: List[ResourceSkill]) -> List[str]:
        """Steps the fight engine forward, processing resources, ticks, and actions."""
        self.total_ticks_elapsed += 1
        combat_log = []
        time_sec = self.total_ticks_elapsed * self.tick_rate

        # 1. Handle Game Engine Cooldowns
        if self.player_gcd_ticks > 0:
            self.player_gcd_ticks -= 1

        # 2. System Resource Recovery Engine: Ticks exactly every 2.0 seconds (20 engine ticks)
        if self.total_ticks_elapsed % 20 == 0:
            attacker.current_magicka = min(attacker.max_magicka, attacker.current_magicka + attacker.magicka_recovery)
            attacker.current_stamina = min(attacker.max_stamina, attacker.current_stamina + attacker.stamina_recovery)
            combat_log.append(
                f"[{time_sec:.1f}s] [Recovery] {attacker.name} regens stats. "
                f"Mag: {int(attacker.current_magicka)} | Stam: {int(attacker.current_stamina)}"
            )

        # 3. Process Active DoTs on Defender
        for effect_name in list(defender.active_effects.keys()):
            effect = defender.active_effects[effect_name]
            effect.duration_ticks -= 1
            effect.time_since_last_tick += 1

            if effect.effect_type == EffectType.DAMAGE_OVER_TIME and effect.time_since_last_tick >= effect.tick_interval:
                damage = self._calculate_mitigated_damage(attacker, defender, effect.value)
                defender.current_health = max(0.0, defender.current_health - damage)
                effect.time_since_last_tick = 0
                combat_log.append(f"[{time_sec:.1f}s] [DoT Tick] {effect_name} hits for {damage:.2f}.")

            if effect.duration_ticks <= 0:
                del defender.active_effects[effect_name]
                combat_log.append(f"[{time_sec:.1f}s] [Status] DoT '{effect_name}' has expired.")

        # 4. Action Decision Module (Executed on Global Cooldown)
        if self.player_gcd_ticks == 0 and defender.current_health > 0:
            optimal_skill = self._evaluate_priority_queue(attacker, defender, skill_db)
            
            if optimal_skill:
                # Deduct resources and execute the ability
                self._deduct_resources(attacker, optimal_skill)
                cast_log = self._execute_skill_cast(attacker, defender, optimal_skill)
                combat_log.append(cast_log)
                self.player_gcd_ticks = 10  # Enforce 1-second GCD
            else:
                # Emergency Logic: Out of resources! Trigger a 2-second Heavy Attack block to restore stats
                restore_amount = 2500
                attacker.current_magicka = min(attacker.max_magicka, attacker.current_magicka + restore_amount)
                attacker.current_stamina = min(attacker.max_stamina, attacker.current_stamina + restore_amount)
                combat_log.append(
                    f"[{time_sec:.1f}s] [ALERT] {attacker.name} has insufficient resources! "
                    f"Executes HEAVY ATTACK filler. Restored +{restore_amount} Mag/Stam."
                )
                self.player_gcd_ticks = 20  # Heavy Attacks lock the player for 2.0 seconds (20 ticks)

        return combat_log

    def _evaluate_priority_queue(self, attacker: CombatEntity, defender: CombatEntity, skill_db: List[ResourceSkill]) -> Optional[ResourceSkill]:
        """Finds the highest priority skill that the player can actually afford to cast."""
        sorted_skills = sorted(skill_db, key=lambda s: s.priority, reverse=True)

        for skill in sorted_skills:
            # Check resource availability first
            if skill.resource_type == ResourceType.MAGICKA and attacker.current_magicka < skill.cost:
                continue
            if skill.resource_type == ResourceType.STAMINA and attacker.current_stamina < skill.cost:
                continue
                
            # Evaluate standard rotation logic
            if skill.is_dot:
                if not defender.is_effect_active(skill.name, threshold_ticks=10):
                    return skill
            else:
                return skill
        return None

    def _deduct_resources(self, attacker: CombatEntity, skill: ResourceSkill):
        if skill.resource_type == ResourceType.MAGICKA:
            attacker.current_magicka -= skill.cost
        elif skill.resource_type == ResourceType.STAMINA:
            attacker.current_stamina -= skill.cost

    def _execute_skill_cast(self, attacker: CombatEntity, defender: CombatEntity, skill: ResourceSkill) -> str:
        time_sec = self.total_ticks_elapsed * self.tick_rate
        
        if skill.is_dot:
            total_duration_ticks = int(skill.duration_seconds / self.tick_rate)
            dot_effect = ActiveEffect(
                name=skill.name, effect_type=EffectType.DAMAGE_OVER_TIME,
                duration_ticks=total_duration_ticks, tick_interval=10, value=skill.base_damage
            )
            defender.active_effects[skill.name] = dot_effect
            return f"[{time_sec:.1f}s] [Cast] {attacker.name} uses '{skill.name}' (-{skill.cost} Magicka)."
        else:
            damage = self._calculate_mitigated_damage(attacker, defender, skill.base_damage)
            defender.current_health = max(0.0, defender.current_health - damage)
            return f"[{time_sec:.1f}s] [Cast] {attacker.name} fires '{skill.name}' for {damage:.2f} (-{skill.cost} Stamina)."

    def _calculate_mitigated_damage(self, attacker: CombatEntity, defender: CombatEntity, base_val: float) -> float:
        modified = base_val * (1.0 + (sum(attacker.damage_done_modifiers) / 100.0))
        effective_armor = max(0, defender.base_armor - attacker.flat_penetration)
        return modified * (1.0 - (effective_armor / 500.0 / 100.0))

### Simulating a Fight with Resource Drain
if __name__ == "__main__":
    # 1. Setup skills with resource costs
    hybrid_skills = [
        ResourceSkill(name="Unstable Wall", is_dot=True, base_damage=1500.0, resource_type=ResourceType.MAGICKA, cost=3500, duration_seconds=10.0, priority=2),
        ResourceSkill(name="Whirlwind Spammable", is_dot=False, base_damage=3800.0, resource_type=ResourceType.STAMINA, cost=4000, priority=1)
    ]

    # 2. Setup characters (low starting Stamina to force recovery rules)
    player = CombatEntity(
        name="Arcanist", max_health=22000, current_health=22000, base_armor=0, flat_penetration=4000,
        max_magicka=40000, current_magicka=20000.0, magicka_recovery=1000,
        max_stamina=12000, current_stamina=9000.0, stamina_recovery=800
    )
    boss = CombatEntity(name="Veteran Boss", max_health=500000, current_health=500000, base_armor=18200)

    engine = ResourceCombatEngine(tick_rate_seconds=0.1)

    print("--- AUTOMATED COMBAT WITH RESOURCE MANAGEMENT ---")
    
    for _ in range(80):
        logs = engine.process_tick(attacker=player, defender=boss, skill_db=hybrid_skills)
        for log in logs:
            print(log)

    print("-------------------------------------------------")
    print(f"Final Player State -> Magicka: {int(player.current_magicka)} | Stamina: {int(player.current_stamina)}")



## Build the Team
from dataclasses import dataclass, field
from typing import List, Set, Dict

# Complete list of mandatory optimization targets for a 2026 Veteran Trial team
MANDATORY_BUFFS = {
    # Major Buffs
    "Major Courage", "Major Force", "Major Slayer", "Major Vulnerability", "Major Breach",
    # Minor Buffs
    "Minor Courage", "Minor Force", "Minor Berserk", "Minor Sorcery", "Minor Prophecy", 
    "Minor Savagery", "Minor Brutality", "Minor Breach", "Minor Vulnerability",
    # Essential Synergy/Sustain Sets
    "Alcosh", "Elemental Catalyst", "Powerful Assault"
}

@dataclass(frozen=True)
class PlayerProfile:
    id: int
    name: str
    role: str       # "Tank", "Healer", "DPS"
    class_name: str # "Dragonknight", "Nightblade", "Sorcerer", "Templar", "Warden", "Necromancer", "Arcanist"
    provides: Set[str] = field(default_factory=set) # Buffs/sets this build can carry


## The Backtracking Matrix Engine
class TrialTeamOptimizer:
    def __init__(self, target_buffs: Set[str] = MANDATORY_BUFFS):
        self.target_buffs = target_buffs
        self.best_team: List[PlayerProfile] = []
        self.max_covered_buffs = -1

    def optimize(self, pool: List[PlayerProfile]) -> Dict:
        """Entry point to solve the roster composition matrix."""
        self.best_team = []
        self.max_covered_buffs = -1
        
        # Start recursive matrix search
        self._backtrack(pool, 0, [], {"Tank": 0, "Healer": 0, "DPS": 0}, set())
        
        # Compute results for application response payload
        if not self.best_team:
            return {"status": "Error", "message": "No valid team could be generated from pool constraints."}
            
        final_buffs = set().union(*(p.provides for p in self.best_team))
        missing = self.target_buffs - final_buffs
        
        return {
            "status": "Optimized" if len(missing) == 0 else "Suboptimal (Best Effort)",
            "team_roster": [(p.name, p.role, p.class_name) for p in self.best_team],
            "buff_coverage_percent": round((len(final_buffs & self.target_buffs) / len(self.target_buffs)) * 100, 1),
            "missing_buffs": list(missing)
        }

    def _backtrack(self, pool: List[PlayerProfile], index: int, current_team: List[PlayerProfile], 
                   role_counts: Dict[str, int], covered_buffs: Set[str]):
        """Internal recursive matrix branch prune solver."""
        
        # Base Case: We hit the strict 12-person trial layout limits
        if len(current_team) == 12:
            relevant_coverage = len(covered_buffs & self.target_buffs)
            if relevant_coverage > self.max_covered_buffs:
                self.max_covered_buffs = relevant_coverage
                self.best_team = list(current_team)
            return

        # Pruning optimization: If remaining players can't possibly beat the current high score, stop searching this branch
        remaining_slots = 12 - len(current_team)
        if len(current_team) + (len(pool) - index) < 12:
            return

        for i in range(index, len(pool)):
            player = pool[i]
            role = player.role
            
            # Strict Trial Constraint Pruning Rules
            if role == "Tank" and role_counts["Tank"] >= 2: continue
            if role == "Healer" and role_counts["Healer"] >= 2: continue
            if role == "DPS" and role_counts["DPS"] >= 8: continue

            # Apply step to state
            role_counts[role] += 1
            current_team.append(player)
            new_covered = covered_buffs.union(player.provides)

            # Move down the decision tree branch
            self._backtrack(pool, i + 1, current_team, role_counts, new_covered)

            # Backtrack step (Revert state for next iteration branch)
            current_team.pop()
            role_counts[role] -= 1

## Healer Rank
from dataclasses import dataclass
from typing import List, Dict

@dataclass(frozen=True)
class HealerClassProfile:
    class_name: str
    base_hps_multiplier: float  # Percent modifiers to overall healing output
    aoe_hot_capability: float    # Score for keeping up passive ground circles
    burst_emergency_heal: float # Score for pulling players back from 1% health
    unique_group_utility: list[str] # Buffs this class handles natively


class HealerRecommendationEngine:
    def __init__(self):
        # Database containing standard game mechanical scores for each class
        self.class_database = [
            HealerClassProfile(
                class_name="Warden",
                base_hps_multiplier=1.10,  # +10% Healing done via passives (Nature's Gift/Bond)
                aoe_hot_capability=9.5,    # Budding Seeds and Enchanted Growth rule AoE healing
                burst_emergency_heal=8.0,  # Fungal Growth is strong but directional
                unique_group_utility=["Minor Toughness (+10% Max Health)", "Minor Vulnerability"]
            ),
            HealerClassProfile(
                class_name="Nightblade",
                base_hps_multiplier=1.04,  # Reinvigorating Drain/Healthy Offering passives
                aoe_hot_capability=9.0,    # Refreshing Path is one of the highest ticking HoTs
                burst_emergency_heal=9.5,  # Healthy Offering provides massive instant single-target burst
                unique_group_utility=["Minor Savagery", "Massive Ultimate Generation"]
            ),
            HealerClassProfile(
                class_name="Templar",
                base_hps_multiplier=1.12,  # Sacred Ground passives grant massive raw healing buffs
                aoe_hot_capability=8.0,    # Extended Ritual covers a massive area but ticks slower
                burst_emergency_heal=10.0, # Breath of Life is the ultimate automated emergency button
                unique_group_utility=["Minor Sorcery", "Extremely Easy Synergy Activations"]
            ),
            HealerClassProfile(
                class_name="Arcanist",
                base_hps_multiplier=1.05,
                aoe_hot_capability=8.5,    # Chakram Shields complement traditional healing well
                burst_emergency_heal=8.5,  # Evolving Runemend scales dynamically off Crux
                unique_group_utility=["Minor Courage", "Minor Evasion"]
            ),
        ]

    def get_ranked_recommendations(self, prioritize_burst: bool = False) -> List[Dict]:
        """Calculates algorithmic healer power levels and returns a sorted payload."""
        ranked_list = []

        for profile in self.class_database:
            # Core Math Formula: Score throughput combined with mechanical modifiers
            if prioritize_burst:
                # Weighted heavier toward fixing emergency mistakes instantly
                throughput_score = (profile.burst_emergency_heal * 1.5) + profile.aoe_hot_capability
            else:
                # Default baseline layout: Maximize overall group stacking HoTs
                throughput_score = (profile.aoe_hot_capability * 1.5) + profile.burst_emergency_heal

            # Apply their percentage healing done passive multiplier
            final_hps_score = throughput_score * profile.base_hps_multiplier

            ranked_list.append({
                "class": profile.class_name,
                "calculated_hps_score": round(final_hps_score, 2),
                "burst_rating": profile.burst_emergency_heal,
                "aoe_hot_rating": profile.aoe_hot_capability,
                "core_utility": profile.unique_group_utility
            })

        # Sort dynamically from absolute highest numeric calculation to lowest
        return sorted(ranked_list, key=lambda x: x["calculated_hps_score"], reverse=True)

if __name__ == "__main__":
    engine = HealerRecommendationEngine()

    # Scenario A: Standard Group Stack-and-Burn (Prioritizing Area HoTs)
    standard_rankings = engine.get_ranked_recommendations(prioritize_burst=False)

    print("=== RECOMMENDED HEALERS: GENERAL HOPS STACKING ===")
    for rank, item in enumerate(standard_rankings, 1):
        print(f"{rank}. {item['class']:<12} | Performance Score: {item['calculated_hps_score']:<5} | Passive Buffs: {item['core_utility']}")

    # Scenario B: Chaotic Progresion Fights (Prioritizing Emergency Clutch Heals)
    emergency_rankings = engine.get_ranked_recommendations(prioritize_burst=True)

    print("\n=== RECOMMENDED HEALERS: EMERGENCY BURST HEALING ===")
    for rank, item in enumerate(emergency_rankings, 1):
        print(f"{rank}. {item['class']:<12} | Performance Score: {item['calculated_hps_score']:<5}")


## HPS
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ActiveHoT:
    name: str
    base_tick_heal: float
    duration_seconds: float
    tick_interval_seconds: float
    targets_hit: int = 1

class ESOHearingEngine:
    @staticmethod
    def calculate_single_heal(
        base_heal: float,
        healing_done_mods: List[float],
        healing_received_mods: List[float],
        crit_chance: float,
        crit_damage_mods: List[float]
    ) -> Dict[str, float]:
        """Calculates the expected mathematical output of a single raw healing event."""
        
        # 1. Apply additive percentage buffs
        total_done = 1.0 + (sum(healing_done_mods) / 100.0)
        total_received = 1.0 + (sum(healing_received_mods) / 100.0)
        modified_normal_heal = base_heal * total_done * total_received

        # 2. Compute Critical healing multiplier
        bonus_crit = min(sum(crit_damage_mods), 125.0)  # Enforce +125% cap
        crit_multiplier = 1.0 + ((50.0 + bonus_crit) / 100.0)
        modified_crit_heal = modified_normal_heal * crit_multiplier

        # 3. Calculate statistically weighed average output (Expected Value)
        crit_fraction = crit_chance / 100.0
        expected_average_heal = (modified_normal_heal * (1.0 - crit_fraction)) + (modified_crit_heal * crit_fraction)

        return {
            "normal_heal": round(modified_normal_heal, 2),
            "critical_heal": round(modified_crit_heal, 2),
            "expected_average": round(expected_average_heal, 2)
        }

    @classmethod
    def calculate_active_hps_pool(
        self, 
        active_hots: List[ActiveHoT], 
        crit_chance: float,
        healing_done: List[float],
        crit_damage_mods: List[float]
    ) -> float:
        """Sums up all ticking sources of healing to output a group HPS metric."""
        total_hps = 0.0

        for hot in active_hots:
            # Solve the baseline performance for 1 target hit by 1 tick
            heal_profile = self.calculate_single_heal(
                base_heal=hot.base_tick_heal,
                healing_done_mods=healing_done,
                healing_received_mods=[], # Assumed baseline targets
                crit_chance=crit_chance,
                crit_damage_mods=crit_damage_mods
            )
            
            # Convert single tick to standard per-second throughput across all targets
            ticks_per_second = 1.0 / hot.tick_interval_seconds
            hot_hps = heal_profile["expected_average"] * ticks_per_second * hot.targets_hit
            total_hps += hot_hps

        return round(total_hps, 2)

# --- App Engine Verification ---
if __name__ == "__main__":
    engine = ESOHearingEngine()

    # Player stats: 52% Crit Chance, +15% Healing Done, +10% Crit Damage (Minor Force)
    my_crit = 52.0
    my_healing_buffs = [15.0]  # e.g., Ritual Mundus + passives
    my_crit_damage_buffs = [10.0]

    # Simulation: A Healer keeping up standard ticking circles on a full 12-person trial group
    active_buff_pool = [
        # Ticks every 1.0s, hitting all 12 group members stacked on a boss
        ActiveHoT(name="Illustrious Healing", base_tick_heal=1100.0, duration_seconds=12.0, tick_interval_seconds=1.0, targets_hit=12),
        # Ticks every 2.0s (Echoing Vigor standard), hitting all 12 players
        ActiveHoT(name="Echoing Vigor", base_tick_heal=1400.0, duration_seconds=10.0, tick_interval_seconds=2.0, targets_hit=12)
    ]

    simulated_hps = engine.calculate_active_hps_pool(
        active_hots=active_buff_pool,
        crit_chance=my_crit,
        healing_done=my_healing_buffs,
        crit_damage_mods=my_crit_damage_buffs
    )

    print(f"=== ENGINE REPORT ===")
    print(f"Total Group Sustained HPS: {simulated_hps} health restored per second.")


## Race reccomendation engine
from dataclasses import dataclass
from typing import List, Dict

@dataclass(frozen=True)
class RacePassiveProfile:
    race_name: str
    max_magicka: int = 0
    max_stamina: int = 0
    max_health: int = 0
    mag_recovery: int = 0
    stam_recovery: int = 0
    weapon_spell_damage: int = 0
    cost_reduction_pct: float = 0.0
    damage_mitigation_pct: float = 0.0

class ESORaceRecommendationEngine:
    def __init__(self):
        # Database tracking exact operational passives for major races
        self.race_database = [
            RacePassiveProfile("Breton", max_magicka=2000, mag_recovery=130, cost_reduction_pct=7.0),
            RacePassiveProfile("High Elf (Altmer)", max_magicka=2000, weapon_spell_damage=258),
            RacePassiveProfile("Dark Elf (Dunmer)", max_magicka=1910, max_stamina=1910, weapon_spell_damage=258),
            RacePassiveProfile("Imperial", max_health=2000, max_stamina=2000, cost_reduction_pct=6.0),
            RacePassiveProfile("Orc", max_health=1000, max_stamina=2000, weapon_spell_damage=258),
            RacePassiveProfile("Nord", max_health=1000, max_stamina=1500, damage_mitigation_pct=4.0) # Resistances mapped
        ]

    def recommend_for_role(self, role: str) -> List[Dict]:
        """Scores and ranks races dynamically based on mathematical role preferences."""
        scored_races = []
        target_role = role.lower()

        for race in self.race_database:
            fitness_score = 0.0

            # --- WEIGHTING LOGIC PER COMBAT PILLARS ---
            if target_role == "healer":
                # Prioritizes Magicka Size, Magicka Sustain, and Ability Cost Reductions
                fitness_score += (race.max_magicka * 0.1)
                fitness_score += (race.mag_recovery * 2.0)
                fitness_score += (race.cost_reduction_pct * 150.0)
                fitness_score += (race.weapon_spell_damage * 0.5)  # Spell power affects raw healing output

            elif target_role == "tank":
                # Prioritizes Health, Stamina, Cost Reductions (Block/Skills), and Mitigation
                fitness_score += (race.max_health * 0.15)
                fitness_score += (race.max_stamina * 0.1)
                fitness_score += (race.cost_reduction_pct * 200.0)
                fitness_score += (race.damage_mitigation_pct * 300.0)

            elif "dps" in target_role:
                # Prioritizes Raw Power Stat (Weapon/Spell Damage) and corresponding Resource Size
                fitness_score += (race.weapon_spell_damage * 3.0)
                if "magicka" in target_role:
                    fitness_score += (race.max_magicka * 0.1) + (race.mag_recovery * 0.5)
                else:
                    fitness_score += (race.max_stamina * 0.1) + (race.stam_recovery * 0.5)

            # Package output schema
            scored_races.append({
                "race": race.race_name,
                "engine_fitness_score": round(fitness_score, 1),
                "primary_benefit": self._get_primary_tag(race, target_role)
            })

        # Sort absolute highest scoring race configurations to the top
        return sorted(scored_races, key=lambda x: x["engine_fitness_score"], reverse=True)

    def _get_primary_tag(self, race: RacePassiveProfile, role: str) -> str:
        """Helper to return an explicit frontend UI textual tag."""
        if race.cost_reduction_pct > 0 and (role == "healer" or role == "tank"):
            return f"Superb Ability Sustain (-{race.cost_reduction_pct}% Resource Costs)"
        if race.weapon_spell_damage > 0:
            return f"Maximum Offensive Throughput (+{race.weapon_spell_damage} Spell/Weapon Power)"
        if race.damage_mitigation_pct > 0:
            return "Ultimate Survival & Raw Physical Damage Mitigation"
        return "Balanced Hybrid Resource Pools"

# Verification & Live Output Parsing
if __name__ == "__main__":
    engine = ESORaceRecommendationEngine()

    # Calculate optimal race choices for your Healer system profile
    healer_rankings = engine.recommend_for_role("Healer")

    print("=== EVERYTHNG RECOMMENDATION ENGINE: RACE SUITE ===")
    print("Target Selected: ROLE = HEALER\n")
    for ranking, item in enumerate(healer_rankings, 1):
        print(f"{ranking}. {item['race']:<18} | Match Score: {item['engine_fitness_score']:<6} | Highlight: {item['primary_benefit']}")

    # Check for Tanks
    tank_rankings = engine.recommend_for_role("Tank")
    print("\nTarget Selected: ROLE = TANK\n")
    for ranking, item in enumerate(tank_rankings, 1):
        print(f"{ranking}. {item['race']:<18} | Match Score: {item['engine_fitness_score']:<6}")

## Mundus picker
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict

class MundusType(Enum):
    THE_THIEF = "The Thief (Critical Chance)"
    THE_SHADOW = "The Shadow (Critical Damage)"
    THE_RITUAL = "The Ritual (Healing Done)"
    THE_ATRONACH = "The Atronach (Magicka Recovery)"
    THE_LORD = "The Lord (Max Health)"

@dataclass(frozen=True)
class MundusBaseline:
    name: MundusType
    base_value: float  # Flat rating or raw percentage depending on type

# Game database mapping the exact raw un-buffed values of key stones
MUNDUS_DATABASE = {
    MundusType.THE_THIEF: MundusBaseline(MundusType.THE_THIEF, base_value=1333.0),      # Flat Crit Rating
    MundusType.THE_SHADOW: MundusBaseline(MundusType.THE_SHADOW, base_value=11.0),     # Raw Crit Damage %
    MundusType.THE_RITUAL: MundusBaseline(MundusType.THE_RITUAL, base_value=8.0),      # Raw Healing Done %
    MundusType.THE_ATRONACH: MundusBaseline(MundusType.THE_ATRONACH, base_value=310.0), # Mag Recovery
    MundusType.THE_LORD: MundusBaseline(MundusType.THE_LORD, base_value=2231.0)        # Max Health
}
@dataclass(frozen=True)
class RaceProfile:
    name: str
    bonus_magicka: int = 0
    bonus_spell_dmg: int = 0
    bonus_mag_regen: int = 0
    bonus_health: int = 0

class ESOMundusRaceOptimizer:
    def __init__(self):
        self.races = [
            RaceProfile("Breton", bonus_magicka=2000, bonus_mag_regen=130),
            RaceProfile("High Elf (Altmer)", bonus_magicka=2000, bonus_spell_dmg=258),
            RaceProfile("Dark Elf (Dunmer)", bonus_magicka=1910, bonus_spell_dmg=258)
        ]

    def calculate_scaled_mundus(self, mundus_type: MundusType, gold_divines_pieces: int) -> float:
        """Calculates exact Mundus values boosted by legendary Divines armor traits."""
        base = MUNDUS_DATABASE[mundus_type].base_value
        # Each gold divines piece adds 9.1% effectiveness
        multiplier = 1.0 + (gold_divines_pieces * 0.091)
        return round(base * multiplier, 2)

    def optimize_build(
        self, 
        target_role: str, 
        current_crit_chance_pct: float, 
        current_crit_dmg_bonus_pct: float,
        divines_count: int = 7
    ) -> List[Dict]:
        """Ranks Race + Mundus pairings based on automated combat simulation metrics."""
        recommendations = []
        role = target_role.lower()

        # Pre-calculate what the active stones actually yield with the user's armor
        thief_rating = self.calculate_scaled_mundus(MundusType.THE_THIEF, divines_count)
        thief_converted_pct = thief_rating / 219.0 # 219 crit rating = 1% chance
        
        shadow_pct = self.calculate_scaled_mundus(MundusType.THE_SHADOW, divines_count)
        ritual_pct = self.calculate_scaled_mundus(MundusType.THE_RITUAL, divines_count)

        for race in self.races:
            # 1. Base the initial score on structural role fitness
            if role == "healer":
                # Healers want raw spell damage power or heavy sustain pools
                base_fitness = (race.bonus_magicka * 0.1) + (race.bonus_spell_dmg * 0.5) + (race.bonus_mag_regen * 1.5)
                
                # Pair with Ritual for raw throughput, or Atronach for recovery profiles
                recommendations.append({
                    "combination": f"{race.name} + {MundusType.THE_RITUAL.value}",
                    "score": round(base_fitness + (ritual_pct * 10), 2),
                    "benefit": f"Brings +{ritual_pct}% Healing Done with {divines_count} Divines pieces."
                })
                
            elif "dps" in role:
                # Base DPS offensive metric profile
                base_fitness = (race.bonus_magicka * 0.05) + (race.bonus_spell_dmg * 2.0)
                
                # --- DYNAMIC THE THIEF VS THE SHADOW RESOLUTION ---
                # Predict output based on standard DPS optimization theory
                # We select whichever stone yields the higher expected critical multiplier density
                
                # Choice A: Simulate adding The Thief
                sim_chance_thief = min(current_crit_chance_pct + thief_converted_pct, 100.0)
                thief_expected_multiplier = 1.0 + ((sim_chance_thief / 100.0) * (50.0 + current_crit_dmg_bonus_pct) / 100.0)
                
                # Choice B: Simulate adding The Shadow (Enforce 125% game cap limit)
                sim_bonus_shadow = min(current_crit_dmg_bonus_pct + shadow_pct, 125.0)
                shadow_expected_multiplier = 1.0 + ((current_crit_chance_pct / 100.0) * (50.0 + sim_bonus_shadow) / 100.0)

                # Determine winning combination
                if thief_expected_multiplier >= shadow_expected_multiplier:
                    best_stone = MundusType.THE_THIEF
                    impact = f"+{thief_converted_pct:.2f}% Critical Chance (Best option for your current stats)"
                    final_score = base_fitness * thief_expected_multiplier
                else:
                    best_stone = MundusType.THE_SHADOW
                    impact = f"+{shadow_pct:.2f}% Critical Damage Modifier (Best option for your current stats)"
                    final_score = base_fitness * shadow_expected_multiplier

                recommendations.append({
                    "combination": f"{race.name} + {best_stone.value}",
                    "score": round(final_score, 2),
                    "benefit": impact
                })

        return sorted(recommendations, key=lambda x: x["score"], reverse=True)

# Verification & Live Output Parsing
if __name__ == "__main__":
    optimizer = ESOMundusRaceOptimizer()

    # --- TEST CASE 1: Low Critical Chance Build ---
    # The user has low crit chance (35%) but decent crit damage buffs running (60%)
    print("=== SCENARIO 1: CURRENT STATS REQUIRE CRIT CHANCE ===")
    rankings_low_crit = optimizer.optimize_build(
        target_role="Magicka_DPS",
        current_crit_chance_pct=35.0,
        current_crit_dmg_bonus_pct=60.0,
        divines_count=7
    )
    for idx, r in enumerate(rankings_low_crit, 1):
        print(f"{idx}. Build: {r['combination']:<42} | Score: {r['score']:<6} | {r['benefit']}")

    # --- TEST CASE 2: High Critical Chance Build ---
    # The user has high crit chance (72%) but low critical damage modifiers (20%)
    print("\n=== SCENARIO 2: CURRENT STATS REQUIRE CRIT DAMAGE ===")
    rankings_high_crit = optimizer.optimize_build(
        target_role="Magicka_DPS",
        current_crit_chance_pct=72.0,
        current_crit_dmg_bonus_pct=20.0,
        divines_count=7
    )
    for idx, r in enumerate(rankings_high_crit, 1):
        print(f"{idx}. Build: {r['combination']:<42} | Score: {r['score']:<6} | {r['benefit']}")

## Food engine
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict

class FoodCategory(Enum):
    BI_STAT_MAX = "Bi-Stat Maximum Power"
    TRI_STAT_MAX = "Tri-Stat Balanced Defense"
    SUSTAIN_RECOVERY = "Single/Dual Stat Sustain"
    SPECIAL_HYBRID = "End-Game Special Hybrid"

@dataclass(frozen=True)
class FoodItemProfile:
    name: str
    category: FoodCategory
    health_bonus: int = 0
    magicka_bonus: int = 0
    stamina_bonus: int = 0
    health_regen: int = 0
    magicka_regen: int = 0
    stamina_regen: int = 0


class ESOFoodRecommendationEngine:
    def __init__(self):
        # Database containing standard game mechanical baselines for top-tier food choices
        self.food_database = [
            FoodItemProfile("Mistral Banana Bunny Hash", FoodCategory.BI_STAT_MAX, health_bonus=5395, magicka_bonus=4936),
            FoodItemProfile("Braised Rabbit with Spring Vegetables", FoodCategory.BI_STAT_MAX, health_bonus=5395, stamina_bonus=4936),
            FoodItemProfile("Longfin Pastry with Melon Sauce", FoodCategory.TRI_STAT_MAX, health_bonus=4462, magicka_bonus=4105, stamina_bonus=4105),
            FoodItemProfile("Witchmother's Potent Brew", FoodCategory.SUSTAIN_RECOVERY, health_bonus=3094, magicka_bonus=2856, magicka_regen=315),
            FoodItemProfile("Dubious Camoran Throne", FoodCategory.SUSTAIN_RECOVERY, health_bonus=3094, stamina_bonus=2856, stamina_regen=315),
            FoodItemProfile("Clockwork Citrus Filet", FoodCategory.SPECIAL_HYBRID, health_bonus=3326, magicka_bonus=3080, magicka_regen=338, health_regen=406),
            FoodItemProfile("Artaeum Takeaway Broth", FoodCategory.SPECIAL_HYBRID, health_bonus=3326, stamina_bonus=3080, stamina_regen=338, health_regen=406)
        ]

    def recommend_food(self, role: str, max_resource_deficit: bool, recovery_deficit: bool) -> List[Dict]:
        """Scores and filters the food database to resolve a character's current deficiencies."""
        scored_food = []
        target_role = role.lower()

        for food in self.food_database:
            fitness_score = 0.0

            # 1. Tank Logic (Tanks almost always require balanced tri-stat infrastructure)
            if target_role == "tank":
                if food.category == FoodCategory.TRI_STAT_MAX:
                    fitness_score += 100.0
                fitness_score += (food.health_bonus * 0.01) + (food.stamina_bonus * 0.01)

            # 2. Healer & Magicka DPS Logic
            elif target_role == "healer" or "magicka" in target_role:
                # Prioritize Magicka attributes
                if food.magicka_bonus > 0 or food.magicka_regen > 0:
                    fitness_score += 20.0
                
                # Dynamic adjustment based on user performance state
                if max_resource_deficit and food.category == FoodCategory.BI_STAT_MAX:
                    fitness_score += 50.0  # Boost flat power food if pools are too shallow
                if recovery_deficit and (food.magicka_regen > 0):
                    fitness_score += 60.0  # Boost recovery food if they are bottoming out

            # 3. Stamina DPS Logic
            elif "stamina" in target_role:
                # Prioritize Stamina attributes
                if food.stamina_bonus > 0 or food.stamina_regen > 0:
                    fitness_score += 20.0
                
                if max_resource_deficit and food.category == FoodCategory.BI_STAT_MAX:
                    fitness_score += 50.0
                if recovery_deficit and (food.stamina_regen > 0):
                    fitness_score += 60.0

            scored_food.append({
                "food_name": food.name,
                "category": food.category.value,
                "engine_fitness_score": round(fitness_score, 1),
                "stats_provided": f"H: +{food.health_bonus} | M: +{food.magicka_bonus} | S: +{food.stamina_bonus} | M-Regen: +{food.magicka_regen}"
            })

        # Return sorted list with the highest algorithmic fitness score first
        return sorted(scored_food, key=lambda x: x["engine_fitness_score"], reverse=True)

# Simulating Live Character Status Assessment
if __name__ == "__main__":
    engine = ESOFoodRecommendationEngine()

    # Scenario A: Magicka DPS has massive pool sizes but can't sustain their 10-second rotation
    print("=== SCENARIO A: MAGICKA CHARACTER RUNNING OUT OF SUSTAIN ===")
    sustain_results = engine.recommend_food(role="Magicka_DPS", max_resource_deficit=False, recovery_deficit=True)
    for idx, f in enumerate(sustain_results[:2], 1):
        print(f"{idx}. Choice: {f['food_name']:<32} | Score: {f['engine_fitness_score']:<5} | Stats: {f['stats_provided']}")

    # Scenario B: Stamina DPS needs raw maximum pool size for pure scaling burst damage
    print("\n=== SCENARIO B: STAMINA CHARACTER REQUIRING MAX RAW POWER ===")
    power_results = engine.recommend_food(role="Stamina_DPS", max_resource_deficit=True, recovery_deficit=False)
    for idx, f in enumerate(power_results[:2], 1):
        print(f"{idx}. Choice: {f['food_name']:<32} | Score: {f['engine_fitness_score']:<5} | Stats: {f['stats_provided']}")


## Potion Engine
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict

class PotionBuffType(Enum):
    MAJOR_PROPHECY = "Major Prophecy"   # Spell Crit Chance
    MAJOR_SAVAGERY = "Major Savagery"   # Weapon Crit Chance
    MAJOR_SORCERY = "Major Sorcery"     # Spell Damage
    MAJOR_BRUTALITY = "Major Brutality" # Weapon Damage
    MAJOR_INTELLECT = "Major Intellect" # Magicka Recovery
    MAJOR_ENDURANCE = "Major Endurance" # Stamina Recovery

@dataclass(frozen=True)
class PotionProfile:
    name: str
    effects: List[PotionBuffType]
    base_duration_seconds: float = 36.0
    instant_health_restore: int = 0
    instant_magicka_restore: int = 0
    instant_stamina_restore: int = 0

class ESOPotionEngine:
    BASE_POTION_COOLDOWN = 45.0  # Seconds

    def __init__(self, alchemy_medicinal_use_rank: int = 0, jewelry_infusion_count: int = 0):
        """
        Args:
            alchemy_medicinal_use_rank: 0 to 3 (+10% duration per rank)
            jewelry_infusion_count: Number of jewelry traits reducing potion cooldown (if applicable)
        """
        self.medicinal_use_rank = min(max(0, alchemy_medicinal_use_rank), 3)
        
        # Calculate altered duration modifier
        self.duration_multiplier = 1.0 + (self.medicinal_use_rank * 0.10)
        
        # Calculate altered cooldown (e.g., jewelry glyphs of potion speed reduce the 45s baseline)
        # Assuming standard baseline here, but scalable for jewelry traits
        self.active_cooldown_limit = self.BASE_POTION_COOLDOWN - (jewelry_infusion_count * 5.0)

    def calculate_static_metrics(self, potion: PotionProfile) -> Dict:
        """Computes the theoretical uptime parameters for the UI configuration."""
        final_duration = potion.base_duration_seconds * self.duration_multiplier
        uptime_pct = (final_duration / self.active_cooldown_limit) * 100.0
        
        return {
            "potion_name": potion.name,
            "modified_duration_seconds": round(final_duration, 1),
            "cooldown_seconds": round(self.active_cooldown_limit, 1),
            "max_theoretical_uptime_percent": min(100.0, round(uptime_pct, 1)),
            "has_perfect_loop": final_duration >= self.active_cooldown_limit
        }

    def simulate_potion_drink(self, potion: PotionProfile, current_magicka: float, max_magicka: int) -> Dict:
        """Executes a live event trigger inside your combat loop."""
        metrics = self.calculate_static_metrics(potion)
        
        # 1. Apply instant burst resource restore mechanics (e.g., standard trash or tri-pot effects)
        # Scaled by baseline character level metrics natively
        new_magicka = min(max_magicka, current_magicka + potion.instant_magicka_restore)
        mag_gained = new_magicka - current_magicka

        return {
            "action": "Drink Potion",
            "instant_magicka_restored": mag_gained,
            "buffs_applied": [effect.value for effect in potion.effects],
            "duration_ticks": int(metrics["modified_duration_seconds"] * 10), # Converted to 100ms engine ticks
            "cooldown_ticks": int(metrics["cooldown_seconds"] * 10)
        }

# Application Verification Loop
if __name__ == "__main__":
    # Define a high-end meta spellcaster potion (Essence of Spell Power)
    # Provides power stats, crit chance, and active resource restore over time loops
    spell_power_pot = PotionProfile(
        name="Essence of Spell Power",
        effects=[PotionBuffType.MAJOR_SORCERY, PotionBuffType.MAJOR_PROPHECY, PotionBuffType.MAJOR_INTELLECT],
        instant_magicka_restore=7500
    )

    # --- Scenario A: Raw Character with NO Alchemy passives unlocked ---
    basic_character_engine = ESOPotionEngine(alchemy_medicinal_use_rank=0)
    basic_report = basic_character_engine.calculate_static_metrics(spell_power_pot)

    print("=== POTION AUDIT: MEDICINAL USE RANK 0 ===")
    print(f"Buff Active Duration: {basic_report['modified_duration_seconds']}s")
    print(f"Potion Cooldown Window: {basic_report['cooldown_seconds']}s")
    print(f"Maximum Buff Uptime: {basic_report['max_theoretical_uptime_percent']}%")
    print(f"Status Checklist: Perfect Loop Active? -> {basic_report['has_perfect_loop']}")

    # --- Scenario B: Optimized End-Game Character with Max Alchemy passives ---
    optimized_character_engine = ESOPotionEngine(alchemy_medicinal_use_rank=3)
    optimized_report = optimized_character_engine.calculate_static_metrics(spell_power_pot)
    live_event = optimized_character_engine.simulate_potion_drink(spell_power_pot, current_magicka=12000, max_magicka=40000)

    print("\n=== POTION AUDIT: MEDICINAL USE RANK 3 (MAXIMUM META) ===")
    print(f"Buff Active Duration: {optimized_report['modified_duration_seconds']}s")
    print(f"Potion Cooldown Window: {optimized_report['cooldown_seconds']}s")
    print(f"Maximum Buff Uptime: {optimized_report['max_theoretical_uptime_percent']}% (Continuous Loop Locked!)")
    print(f"Status Checklist: Perfect Loop Active? -> {optimized_report['has_perfect_loop']}")
    
    print(f"\nLive Combat Cast Output Dictionary sent to Engine:")
    print(f" -> Instant Resources: +{live_event['instant_magicka_restored']} Magicka")
    print(f" -> UI Active Buffer: Apply {live_event['buffs_applied']} for {live_event['duration_ticks']} engine ticks.")

