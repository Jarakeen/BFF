"""Build relationship indexes from locally stored reference data."""
#builders/relationship_builder.py
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


class RelationshipBuilder:
    """Connect local reference objects without fetching or mutating source data."""

    RELATIONSHIP_FILES = {
        "skills": "skill_effects.json",
        "gear_sets": "gear_set_effects.json",
        "potions": "potion_effects.json",
        "encounters": "encounter_mechanics.json",
        "mechanics": "mechanic_required_effects.json",
    }

    def __init__(self, data_directory: str, output_directory: str | None = None) -> None:
        self.data_directory = Path(data_directory)
        self.output_directory = Path(output_directory or data_directory)

    def build_all(self) -> dict[str, int]:
        """Build every relationship file and return the number of relationships."""
        relationships = {
            "skills": self.build_skill_effects(),
            "gear_sets": self.build_gear_set_effects(),
            "potions": self.build_potion_effects(),
            "encounters": self.build_encounter_mechanics(),
            "mechanics": self.build_mechanic_required_effects(),
        }

        return {
            self.RELATIONSHIP_FILES[key]: len(records)
            for key, records in relationships.items()
        }

    def build_skill_effects(self) -> list[dict[str, str]]:
        return self._build_effect_relationships("skills.json")

    def build_gear_set_effects(self) -> list[dict[str, str]]:
        return self._build_effect_relationships("gear_sets.json")

    def build_potion_effects(self) -> list[dict[str, str]]:
        return self._build_effect_relationships("potions.json")

    def build_encounter_mechanics(self) -> list[dict[str, str]]:
        relationships: list[dict[str, str]] = []
        for encounter in self._load_records("encounters.json"):
            encounter_id = str(encounter.get("encounter_id", encounter.get("id", "")))
            encounter_name = str(encounter.get("boss_name", encounter.get("name", encounter_id)))

            mechanics = encounter.get("mechanics", [])
            if not mechanics:
                mechanics = [
                    event.get("event_name")
                    for event in encounter.get("mechanical_timeline", [])
                    if isinstance(event, dict) and event.get("event_name")
                ]

            for mechanic in mechanics:
                mechanic_name = self._label(mechanic)
                relationships.append({
                    "encounter_id": encounter_id,
                    "encounter_name": encounter_name,
                    "mechanic_id": self._slug(mechanic_name),
                    "mechanic_name": mechanic_name,
                })

        return self._write("encounter_mechanics.json", relationships)

    def build_mechanic_required_effects(self) -> list[dict[str, str]]:
        relationships: list[dict[str, str]] = []
        for mechanic in self._load_records("mechanics.json"):
            mechanic_id = str(mechanic.get("id", ""))
            mechanic_name = str(mechanic.get("name", mechanic_id))
            required_effects = mechanic.get("required_effects", mechanic.get("effects", []))

            for effect in self._strings(required_effects):
                relationships.append({
                    "mechanic_id": mechanic_id or self._slug(mechanic_name),
                    "mechanic_name": mechanic_name,
                    "required_effect": effect,
                })

        for encounter in self._load_records("encounters.json"):
            encounter_id = str(encounter.get("encounter_id", encounter.get("id", "")))
            encounter_name = str(encounter.get("boss_name", encounter.get("name", encounter_id)))
            requirements = encounter.get("operational_requirements", {})
            for effect in self._strings(requirements.get("mandatory_capabilities", [])):
                relationships.append({
                    "mechanic_id": encounter_id or self._slug(encounter_name),
                    "mechanic_name": encounter_name,
                    "required_effect": effect,
                })

        return self._write("mechanic_required_effects.json", relationships)

    def _build_effect_relationships(self, file_name: str) -> list[dict[str, str]]:
        relationships: list[dict[str, str]] = []
        for record in self._load_records(file_name):
            source_id = str(record.get("id", ""))
            source_name = str(record.get("name", source_id))
            for effect in self._record_effects(record):
                relationships.append({
                    "source_id": source_id,
                    "source_name": source_name,
                    "effect": effect,
                })

        return self._write(self.RELATIONSHIP_FILES[file_name.removesuffix(".json")], relationships)

    def _write(self, file_name: str, records: list[dict[str, str]]) -> list[dict[str, str]]:
        self.output_directory.mkdir(parents=True, exist_ok=True)
        output_path = self.output_directory / file_name
        output_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return records

    def _load_records(self, file_name: str) -> list[dict]:
        path = self.data_directory / file_name
        if not path.exists():
            return []

        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [record for record in data if isinstance(record, dict)]
        if isinstance(data, dict):
            return [record for record in data.values() if isinstance(record, dict)]
        return []

    @classmethod
    def _record_effects(cls, record: dict) -> list[str]:
        effects: list[str] = []
        for value in record.get("effects", []):
            effects.extend(cls._strings([value]))

        for trigger in record.get("triggers", []):
            if isinstance(trigger, dict):
                effects.extend(cls._strings(trigger.get("effects", [])))

        return list(dict.fromkeys(effects))

    @staticmethod
    def _strings(values: Any) -> list[str]:
        if isinstance(values, str):
            return [values]
        if not isinstance(values, Iterable):
            return []

        result: list[str] = []
        for value in values:
            if isinstance(value, str):
                result.append(value)
            elif isinstance(value, dict):
                for key in ("capability_id", "required_effect", "effect", "name"):
                    if isinstance(value.get(key), str):
                        result.append(value[key])
                        break
        return result

    @staticmethod
    def _label(value: Any) -> str:
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
