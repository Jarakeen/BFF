import json
import re
from pathlib import Path
from typing import Any

class ReferenceLibrary:
    FILE_NAMES = (
        "armor_passives.json", "buff.json", "capabilities.json",
        "champion_points.json", "class_passives.json", "damage_types.json",
        "debuffs.json", "encounters.json", "enemy_types.json", "foods.json",
        "gear_sets.json", "guild_passives.json", "mechanics.json", "mundus.json",
        "mythics.json", "potions.json", "races.json", "roster.json", "skills.json",
        "status_effects.json", "weapon_passives.json",
    )

    def __init__(self, data_directory: str):
        """Load reference data from JSON files in the given directory."""
        self.data_directory = Path(data_directory)
        self.cache = {}
        self.load_errors: dict[str, str] = {}
        self.id_index: dict[str, dict] = {}
        self.name_index: dict[str, dict] = {}
        self.effect_index: dict[str, dict] = {}
        self.effect_providers: dict[str, list[dict]] = {}
        self.effect_requirements: dict[str, list[dict]] = {}
        self.mechanic_requirements: dict[str, list[dict]] = {}
        self._effect_aliases: dict[str, set[str]] = {}
        self._boss_name_index: dict[str, dict] = {}

        # Load all data files into memory during initialization
        for file_name in self.FILE_NAMES:
            file_path = self.data_directory / file_name
            if not file_path.exists():
                self.load_errors[file_name] = "File not found"
                continue

            try:
                text = file_path.read_text(encoding="utf-8").strip()

                if not text:
                    print(f"[ReferenceLibrary] {file_name} is empty. Using [].")
                    data = []
                else:
                    data = json.loads(text)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
                self.load_errors[file_name] = str(error)
                continue

            self.cache[file_name.removesuffix(".json")] = data

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build lookup indexes from all currently loaded reference records."""
        self.id_index.clear()
        self.name_index.clear()
        self.effect_index.clear()
        self.effect_providers.clear()
        self.effect_requirements.clear()
        self.mechanic_requirements.clear()
        self._effect_aliases.clear()
        self._boss_name_index.clear()

        for data_key, data in self.cache.items():
            for record in self._records(data):
                record_id = record.get("id")
                if record_id is not None:
                    self.id_index[str(record_id)] = record

                name = record.get("name")
                if isinstance(name, str):
                    self.name_index[name] = record
                    if data_key == "status_effects":
                        self.effect_index[name] = record

                boss_name = record.get("boss_name")
                if isinstance(boss_name, str):
                    self._boss_name_index[boss_name] = record

                for effect in self._effects_for(record):
                    self._add_indexed_record(self.effect_providers, effect, record)

                for effect in self._required_effects_for(record):
                    self._add_indexed_record(self.effect_requirements, effect, record)
                    if record.get("name"):
                        self._add_indexed_record(self.mechanic_requirements, effect, record)

    def _add_indexed_record(
        self,
        index: dict[str, list[dict]],
        effect: str,
        record: dict,
    ) -> None:
        for alias in self._effect_aliases_for(effect):
            self._effect_aliases.setdefault(alias, set()).add(effect)
            providers = index.setdefault(effect, [])
            if not any(provider is record for provider in providers):
                providers.append(record)

    @classmethod
    def _effect_aliases_for(cls, effect: str) -> set[str]:
        normalized = effect.casefold().strip()
        aliases = {normalized, cls._slug(effect)}
        words = normalized.split()
        if len(words) > 1 and words[0] in {"major", "minor"}:
            aliases.add(cls._slug("_".join(words[1:] + [words[0]])))
        if normalized.endswith("_major") or normalized.endswith("_minor"):
            effect_name, qualifier = normalized.rsplit("_", 1)
            aliases.add(cls._slug(f"{qualifier} {effect_name}"))
        return {alias for alias in aliases if alias}

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")

    @staticmethod
    def _records(data: Any) -> list[dict]:
        if isinstance(data, list):
            return [record for record in data if isinstance(record, dict)]
        if isinstance(data, dict):
            return [record for record in data.values() if isinstance(record, dict)]
        return []

    @staticmethod
    def _effects_for(record: dict) -> set[str]:
        effects: set[str] = set()

        def add_effect(value: Any) -> None:
            if isinstance(value, str):
                effects.add(value)
            elif isinstance(value, dict):
                for key in ("capability_id", "effect", "name"):
                    candidate = value.get(key)
                    if isinstance(candidate, str):
                        effects.add(candidate)

        for value in record.get("effects", []):
            add_effect(value)

        for trigger in record.get("triggers", []):
            if isinstance(trigger, dict):
                for value in trigger.get("effects", []):
                    add_effect(value)

        return effects

    @staticmethod
    def _required_effects_for(record: dict) -> set[str]:
        requirements: set[str] = set()
        for key in ("required_effects", "mandatory_capabilities", "required_capabilities"):
            values = record.get(key, [])
            if isinstance(values, str):
                requirements.add(values)
            elif isinstance(values, list):
                requirements.update(value for value in values if isinstance(value, str))
        operational_requirements = record.get("operational_requirements", {})
        if isinstance(operational_requirements, dict):
            for key in ("mandatory_capabilities", "required_effects"):
                values = operational_requirements.get(key, [])
                if isinstance(values, list):
                    requirements.update(value for value in values if isinstance(value, str))
        return requirements

    def _resolve_effects(self, effect: str) -> set[str]:
        resolved: set[str] = set()
        for alias in self._effect_aliases_for(effect):
            resolved.update(self._effect_aliases.get(alias, set()))
        return resolved

    def get_effect(self, name: str) -> dict | None:
        """Retrieve an effect by name."""
        self.get_data("status_effects")
        return self.effect_index.get(name)

    def get_set(self, name: str) -> dict | None:
        """Retrieve a gear set by name."""
        return self._find_named_record(name, "gear_sets")

    def get_skill(self, name: str) -> dict | None:
        """Retrieve a skill by name."""
        return self._find_named_record(name, "skills")

    def get_trial(self, name: str) -> dict | None:
        """Retrieve a trial (encounter) by name."""
        self.get_data("encounters")
        return self._boss_name_index.get(name)

    def get_achievement(self, id: int) -> dict | None:
        """Retrieve an achievement by ID. Note: Achievements are typically not stored as JSON."""
        # Since achievements might not be in a JSON file, this method will return None
        return None

    def find_sets_providing(self, effect_name: str) -> list[dict]:
        """Find gear sets that provide the specified effect."""
        providers = self.find_providers(effect_name)
        return [
            provider for provider in providers
            if provider.get("source_layer") == "gear_sets"
        ]

    def find_skills_providing(self, effect_name: str) -> list[dict]:
        """Find skills that provide the specified effect."""
        providers = self.find_providers(effect_name)
        return [
            provider for provider in providers
            if provider.get("source_layer") == "skills"
        ]

    def get_by_id(self, record_id: str) -> dict | None:
        """Retrieve any indexed reference object by ID."""
        return self.id_index.get(str(record_id))

    def get_by_name(self, name: str) -> dict | None:
        """Retrieve any indexed reference object by name."""
        return self.name_index.get(name)

    def get_effect_providers(self, effect: str) -> list[dict]:
        """Return indexed objects that provide an effect."""
        return self.find_providers(effect)

    def find_providers(self, effect: str) -> list[dict]:
        """Return every indexed object that provides an effect."""
        providers: list[dict] = []
        for resolved_effect in self._resolve_effects(effect):
            for provider in self.effect_providers.get(resolved_effect, []):
                if not any(existing is provider for existing in providers):
                    providers.append(provider)
        return providers

    def find_encounters_requiring(self, effect: str) -> list[dict]:
        """Return indexed encounters that require an effect."""
        return self._find_requirements(effect, "encounters")

    def find_mechanics_requiring(self, effect: str) -> list[dict]:
        """Return indexed mechanics that require an effect."""
        return self._find_requirements(effect, "mechanics")

    def find_everything_using(self, effect: str) -> dict[str, list[dict]]:
        """Return all indexed providers and requirements for an effect."""
        providers = self.find_providers(effect)
        return {
            "providers": providers,
            "skills": [item for item in providers if item.get("source_layer") == "skills"],
            "sets": [item for item in providers if item.get("source_layer") == "gear_sets"],
            "potions": [item for item in providers if item.get("source_layer") == "potions"],
            "encounters": self.find_encounters_requiring(effect),
            "mechanics": self.find_mechanics_requiring(effect),
        }

    def _find_requirements(self, effect: str, source_layer: str) -> list[dict]:
        records: list[dict] = []
        for resolved_effect in self._resolve_effects(effect):
            for record in self.effect_requirements.get(resolved_effect, []):
                if record.get("source_layer") == source_layer or (
                    source_layer == "encounters" and "encounter_id" in record
                ) or (
                    source_layer == "mechanics" and "encounter_id" not in record
                ):
                    if not any(existing is record for existing in records):
                        records.append(record)
        return records

    def _find_named_record(self, name: str, data_key: str) -> dict | None:
        self.get_data(data_key)
        record = self.name_index.get(name)
        if record is None:
            return None
        return record if record.get("source_layer") == data_key else record

    def get_data(self, file_name: str) -> dict | list:
        """Retrieve data from the cache or load it if not already loaded."""
        cache_key = file_name.removesuffix(".json")
        if cache_key not in self.cache:
            file_path = self.data_directory / (cache_key + ".json")
            with open(file_path, "r", encoding="utf-8") as f:
                self.cache[cache_key] = json.load(f)
            self._build_indexes()
        return self.cache[cache_key]
