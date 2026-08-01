import json
import math
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass, field

# Point cleanly to models without importing itself
from models import SourceGameObject, DynamicTrigger, CombatEffect

class TheConsoleOpsEngine:
    def __init__(self, data_directory_path: str):
        self.data_dir = Path(data_directory_path)
        self.capabilities_db = self._load_json("capabilities.json")
        
    # ... rest of your class code follows down here ...


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
    


## Simulating a Pre-Fight Production Run
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
    
## End Test


class TheConsoleOpsEngine:
    def __init__(self, data_directory_path: str):
        self.data_dir = Path(data_directory_path)
        self.capabilities_db = self._load_json("capabilities.json")

    def _load_json(self, file_name: str) -> Dict:
        file_path = self.data_dir / file_name
        if not file_path.exists():
            return {}
        with open(file_path, "r") as f:
            return json.load(f)

    def extract_capabilities(self, player_choices: List[Dict]) -> Set[str]:
        """Layer 3: Flattens a player's choices down into unique capability string keys."""
        discovered_capabilities = set()
        for choice in player_choices:
            for trigger in choice.get("triggers", []):
                for effect in trigger.get("effects", []):
                    cap_id = effect.get("capability_id")
                    if cap_id in self.capabilities_db:
                        discovered_capabilities.add(cap_id)
        return discovered_capabilities

    def audit_raid_operations(self, roster_choices: Dict[str, List[Dict]], encounter_id: str) -> Dict:
        """Layer 4: Audits your 12-person squad capabilities against Rylo's operational mandates."""
        encounters = self._load_json("encounters.json")
        target_boss = next((e for e in encounters if e["encounter_id"] == encounter_id), None)
        
        if not target_boss:
            raise ValueError(f"Encounter {encounter_id} missing from operations database.")

        # 1. Compile total group assets
        group_capabilities = set()
        for player_name, choices in roster_choices.items():
            player_caps = self.extract_capabilities(choices)
            group_capabilities.update(player_caps)

        # 2. Check operational parameters
        mandatory = set(target_boss["operational_requirements"]["mandatory_capabilities"])
        recommended = set(target_boss["operational_requirements"]["recommended_capabilities"])
        
        missing_mandatory = mandatory - group_capabilities
        missing_recommended = recommended - group_capabilities

        # 3. Calculate absolute system mechanics (Rules Layer math)
        base_armor = target_boss["combat_metrics"]["base_armor"]
        flat_shred = 0
        
        for cap_id in group_capabilities:
            cap_fact = self.capabilities_db[cap_id]
            if cap_fact["stat_modified"] == "armor":
                flat_shred += abs(cap_fact["modification_value"])

        effective_armor = max(0, base_armor - flat_shred)
        final_mitigation_pct = effective_armor / 500.0  # 500 armor = 1% PvE reduction

        return {
            "encounter": target_boss["boss_name"],
            "operations_status": "READY_TO_PULL" if len(missing_mandatory) == 0 else "HOLD_COMPOSITION_WARNING",
            "combat_math_metrics": {
                "boss_effective_armor": effective_armor,
                "boss_mitigation_pct": round(final_mitigation_pct, 2),
                "total_shred_value": flat_shred
            },
            "raid_recommendations": {
                "missing_critical_capabilities": list(missing_mandatory),
                "missing_optional_utility": list(missing_recommended),
                "rylos_execution_directives": target_boss["rylos_intel"]["teaching_notes"]
            }

          }

# Timeline Evaluation Code
    def calculate_active_timeline_alerts(self, encounter_id: str, current_fight_time_seconds: float) -> list[dict]:
        """
        Compares the current elapsed fight stopwatch time against the encounter 
        timeline to output active countdown metrics for the desktop bars.
        """
        encounters = self._load_json("encounters.json")
        target_boss = next((e for e in encounters if e["encounter_id"] == encounter_id), None)
        
        if not target_boss:
            return []

        active_alerts = []
        
        for event in target_boss.get("mechanical_timeline", []):
            base_trigger = event["timestamp_seconds"]
            event_name = event["event_name"]
            directive = event["directive_text"]
            
            # --- EVALUATE RECURRING LOOPS ---
            if event["is_recurring"] and current_fight_time_seconds > base_trigger:
                interval = event["loop_interval_seconds"]
                # Calculate the next loop target timestamp point
                elapsed_past_trigger = current_fight_time_seconds - base_trigger
                current_loop_count = math.floor(elapsed_past_trigger / interval) + 1
                next_trigger_time = base_trigger + (current_loop_count * interval)
            else:
                next_trigger_time = base_trigger

            # Calculate seconds remaining until the mechanic strikes
            time_remaining = next_trigger_time - current_fight_time_seconds
            
            # Only track alerts that are coming up within a 30-second strategic window
            if 0.0 <= time_remaining <= 30.0:
                active_alerts.append({
                    "event_name": event_name,
                    "seconds_remaining": round(time_remaining, 1),
                    "directive_text": directive,
                    "progress_percentage": round((time_remaining / 30.0), 2) # Feeds progress bar assets directly
                })
                
        # Sort so the most urgent mechanic hitting the team next sits at index 0
        return sorted(active_alerts, key=lambda x: x["seconds_remaining"])
    