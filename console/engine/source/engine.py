from typing import List, Dict, Set
from models import CombatEffect, SourceGameObject

class TheConsoleEngine:
    def __init__(self, pvp_rules: bool = False):
        self.is_pvp = pvp_rules
        self.mitigation_constant = 660.0 if pvp_rules else 500.0

    def flatten_character_capabilities(self, choices: List[SourceGameObject]) -> Dict[str, CombatEffect]:
        """Layer 3: Reductor pipeline translating choices into exact unique capabilities."""
        active_capabilities = {}
        for game_object in choices:
            for trigger in game_object.triggers:
                if trigger.condition_type in ["on_slotted", "on_equip", "on_hit", "on_heal"]:
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


# Add this to console/engine/sorce/engine.py
from models import PredictiveHealerProfile, WeaponBarType

class WeaponSwapSimulationEngine:
    @staticmethod
    def evaluate_minor_brittle_coverage(healer: PredictiveHealerProfile) -> dict:
        """
        Predicts the mathematical uptime percentage of Minor Brittle 
        based on the healer's weapon traits and bar-swap window constraints.
        """
        # Minor Brittle REQUIRES an Ice Staff on an active bar
        has_ice_front = "Ice Staff" in healer.front_bar.weapon_type
        has_ice_back = "Ice Staff" in healer.back_bar.weapon_type

        # Case 1: Double Ice Staff (100% Structural Availability)
        if has_ice_front and has_ice_back:
            base_uptime = 100.0
        # Case 2: Only on Back Bar (Standard Meta Resto/Ice Setup)
        elif has_ice_back:
            # Uptime window is limited by the duration of the lingering AoE (Blockade)
            # and how quickly the healer returns to reapply it
            rotation_loop_total = healer.back_bar_dot_duration
            time_on_ice_bar = healer.back_bar_cast_time
            
            # Base probability of target exposure
            base_uptime = (time_on_ice_bar / rotation_loop_total) * 100.0
            
            # Boost calculations based on UESP game facts (Charged Trait increases proc odds)
            if healer.back_bar.trait == "Charged":
                base_uptime = min(100.0, base_uptime * 2.35) # Charged multiplies status odds
        else:
            base_uptime = 0.0

        return {
            "has_structural_capability": has_ice_front or has_ice_back,
            "predicted_brittle_uptime_pct": round(base_uptime, 1),
            "is_reliable_coverage": base_uptime >= 85.0,
            "operational_recommendation": (
                "Clear" if base_uptime >= 85.0 else 
                "Instruct healer to run CHARGED trait on Back-Bar Ice Staff to push proc saturation loop."
            )
        }
