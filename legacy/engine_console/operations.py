# Legacy copy of the retired engine/operations.py prototype.
import json
import math
from pathlib import Path
from typing import List, Dict, Set


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

        group_capabilities = set()
        for player_name, choices in roster_choices.items():
            player_caps = self.extract_capabilities(choices)
            group_capabilities.update(player_caps)

        mandatory = set(target_boss["operational_requirements"]["mandatory_capabilities"])
        recommended = set(target_boss["operational_requirements"]["recommended_capabilities"])

        missing_mandatory = mandatory - group_capabilities
        missing_recommended = recommended - group_capabilities

        base_armor = target_boss["combat_metrics"]["base_armor"]
        flat_shred = 0

        for cap_id in group_capabilities:
            cap_fact = self.capabilities_db[cap_id]
            if cap_fact["stat_modified"] == "armor":
                flat_shred += abs(cap_fact["modification_value"])

        effective_armor = max(0, base_armor - flat_shred)
        final_mitigation_pct = effective_armor / 500.0

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

    def calculate_active_timeline_alerts(self, encounter_id: str, current_fight_time_seconds: float) -> list[dict]:
        """Compare elapsed fight time against the encounter timeline for upcoming alerts."""
        encounters = self._load_json("encounters.json")
        target_boss = next((e for e in encounters if e["encounter_id"] == encounter_id), None)

        if not target_boss:
            return []

        active_alerts = []

        for event in target_boss.get("mechanical_timeline", []):
            base_trigger = event["timestamp_seconds"]
            event_name = event["event_name"]
            directive = event["directive_text"]

            if event["is_recurring"] and current_fight_time_seconds > base_trigger:
                interval = event["loop_interval_seconds"]
                elapsed_past_trigger = current_fight_time_seconds - base_trigger
                current_loop_count = math.floor(elapsed_past_trigger / interval) + 1
                next_trigger_time = base_trigger + (current_loop_count * interval)
            else:
                next_trigger_time = base_trigger

            time_remaining = next_trigger_time - current_fight_time_seconds

            if 0.0 <= time_remaining <= 30.0:
                active_alerts.append({
                    "event_name": event_name,
                    "seconds_remaining": round(time_remaining, 1),
                    "directive_text": directive,
                    "progress_percentage": round((time_remaining / 30.0), 2)
                })

        return sorted(active_alerts, key=lambda x: x["seconds_remaining"])
