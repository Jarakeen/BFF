from dataclasses import dataclass
from typing import List, Dict

@dataclass
class TeamCapabilityCache:
    # All flat group debuffs pulled from UESP static game facts
    major_breach_present: bool = False   # -5948 Armor
    minor_breach_present: bool = False   # -2974 Armor
    alkosh_present: bool = False          # -3000 Armor (Average optimization)
    crusher_enchant_value: int = 0        # -2108 Armor (Infused 1H) or -1622 (Normal)

class XboxSimulationEngine:
    @staticmethod
    def calculate_required_personal_penetration(
        boss_target_armor: int, 
        group_assets: TeamCapabilityCache
    ) -> Dict:
        """
        Calculates the static group shred matrix and tells individual players
        exactly what their character sheet needs to read for perfect optimization.
        """
        # 1. Map absolute UESP constant facts
        total_group_shred = 0
        if group_assets.major_breach_present: total_group_shred += 5948
        if group_assets.minor_breach_present: total_group_shred += 2974
        if group_assets.alkosh_present: total_group_shred += 3000
        total_group_shred += group_assets.crusher_enchant_value

        # 2. Deduct group output from total boss armor (UESP verified standard: 18200)
        remaining_boss_armor = max(0, boss_target_armor - total_group_shred)
        
        # 3. Output target guidelines for the individual raid slots
        return {
            "total_group_debuff_shred": total_group_shred,
            "target_boss_armor_remaining": remaining_boss_armor,
            "dps_character_sheet_target": remaining_boss_armor,
            "mitigation_if_dps_has_zero_pen_pct": round((remaining_boss_armor / 500.0), 2)
        }

# --- Live Operational Simulation ---
if __name__ == "__main__":
    # Simulate a standard optimization meeting before a trial
    # Your tanks confirm their builds: running Major Breach, Minor Breach, and an Infused Crusher staff
    my_roster_assets = TeamCapabilityCache(
        major_breach_present=True,
        minor_breach_present=True,
        alkosh_present=False,         # No Alkosh on this pull
        crusher_enchant_value=2108     # Gold Infused Crusher enchant active
    )

    engine = XboxSimulationEngine()
    strategic_report = engine.calculate_required_personal_penetration(
        boss_target_armor=18200, 
        group_assets=my_roster_assets
    )

    print("=== THE CONSOLE: XBOX RAID PRE-CHECK ===")
    print(f"Group Debuffs Total Shred: -{strategic_report['total_group_debuff_shred']} Armor")
    print(f"Remaining Boss Defense: {strategic_report['target_boss_armor_remaining']} Armor")
    print(f"\n[RAID LEAD CALLOUT] Tell all DPS characters that their character sheet")
    print(f"MUST show at least {strategic_report['dps_character_sheet_target']} Penetration!")
    print(f" -> If a player has less than that, they lose damage to a {strategic_report['mitigation_if_dps_has_zero_pen_pct']}% mitigation wall.")
