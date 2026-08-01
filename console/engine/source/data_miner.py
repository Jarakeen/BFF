"""UESP data miners for the Console reference database."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

try:
    from .parsers import (
        parse_abilityCooldown, parse_description, parse_duration, parse_effects,
        parse_range, parse_skillCoef, parse_stat, parse_target,
    )
except ImportError:
    from parsers import (
        parse_abilityCooldown, parse_description, parse_duration, parse_effects,
        parse_range, parse_skillCoef, parse_stat, parse_target,
    )


class UESPApiError(RuntimeError):
    """Raised when UESP returns an HTTP or structured API error."""


class UESPApiClient:
    URL = "https://esolog.uesp.net/exportJson.php"

    def fetch(self, table: str, **parameters: str | int) -> list[dict[str, Any]]:
        query = urlencode({"table": table, **parameters})
        request = urllib.request.Request(
            f"{self.URL}?{query}",
            headers={"User-Agent": "BlackFeatherFoundry/FoundryDock"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            raise UESPApiError(f"{table}: {error}") from error

        if not isinstance(payload, dict):
            raise UESPApiError(f"{table}: expected a JSON object response")
        if payload.get("error"):
            errors = payload["error"]
            detail = "; ".join(map(str, errors)) if isinstance(errors, list) else str(errors)
            raise UESPApiError(f"{table}: {detail}")
        records = payload.get(table, [])
        if not isinstance(records, list):
            raise UESPApiError(f"{table}: expected '{table}' to contain an array")
        return [record for record in records if isinstance(record, dict)]


class TheConsoleDataMiner:
    """Fetch and normalize UESP reference data into the Console data directory."""

    EXPORT_JSON_URL = UESPApiClient.URL

    def __init__(self, data_directory: str, client: UESPApiClient | None = None):
        self.data_dir = Path(data_directory)
        self.client = client or UESPApiClient()

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        try:
            return float(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            return default

    def _write_to_database(self, file_name: str, data: list[dict[str, Any]]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with (self.data_dir / file_name).open("w", encoding="utf-8") as output:
            json.dump(data, output, indent=2, ensure_ascii=False)

    def _mine_records(
        self,
        output_file: str,
        records: list[dict[str, Any]],
        builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    ) -> str:
        mined = []
        for raw in records:
            record = builder(raw)
            if record is not None:
                mined.append(record)
        self._write_to_database(output_file, mined)
        return f"Success! Mined {len(mined)} records into {self.data_dir / output_file}"

    def mine_skills(self) -> str:
        records = self.client.fetch("playerSkills")

        def build(entry: dict[str, Any]) -> dict[str, Any] | None:
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                return None
            description = parse_description(str(entry.get("description", "")))
            coefficients = parse_skillCoef(description)
            return {
                "id": f"skill_{entry.get('id', entry.get('abilityId', ''))}",
                "name": name,
                "source_layer": "skills",
                "base_ability_id": entry.get("baseAbilityId", entry.get("abilityId")),
                "cooldown_seconds": parse_abilityCooldown(description),
                "duration_seconds": parse_duration(description),
                "range_meters": parse_range(description),
                "target": parse_target(description),
                "effects": parse_effects(description),
                "coefficients": {
                    "coeff_a": coefficients.get("coeff_a", self._number(entry.get("coefA"))),
                    "coeff_b": coefficients.get("coeff_b", self._number(entry.get("coefB"))),
                },
                "is_passive": str(entry.get("isPassive", "0")).casefold() in {"1", "true"},
            }

        return self._mine_records("skills.json", records, build)

    def mine_gear_sets(self) -> str:
        records = self.client.fetch("setSummary")

        def build(entry: dict[str, Any]) -> dict[str, Any] | None:
            name = entry.get("setName", entry.get("name"))
            if not isinstance(name, str) or not name.strip():
                return None
            return {
                "id": f"set_{self._slug(name)}",
                "name": name,
                "source_layer": "gear_sets",
                "armor_type": entry.get("armorType"),
                "bonuses": {
                    f"{pieces}_piece": entry.get(f"setBonusDesc{pieces}")
                    for pieces in (2, 3, 4, 5)
                    if entry.get(f"setBonusDesc{pieces}")
                },
                "bonus_5_ability_id": entry.get("bonus5AbilityId"),
            }

        return self._mine_records("gear_sets.json", records, build)

    def mine_consumables(self) -> str:
        records = []
        for item_type in (4, 7, 12):
            records.extend(self.client.fetch("minedItemSummary", type=item_type))

        foods = []
        potions = []
        seen: set[tuple[Any, Any]] = set()
        for entry in records:
            key = (entry.get("itemId", entry.get("id")), entry.get("name"))
            if key in seen or not entry.get("name"):
                continue
            seen.add(key)
            description = parse_description(str(entry.get("description", "")))
            item_type = self._number(entry.get("type"), -1)
            if item_type in (4, 12):
                foods.append({
                    "id": f"food_{self._slug(str(entry['name']))}",
                    "name": entry["name"],
                    "source_layer": "foods",
                    "duration_seconds": parse_duration(description),
                    "stats_provided": {
                        key: parse_stat(description, label) or 0
                        for key, label in (
                            ("max_health", "Max Health"), ("max_magicka", "Max Magicka"),
                            ("max_stamina", "Max Stamina"), ("magicka_recovery", "Magicka Recovery"),
                            ("stamina_recovery", "Stamina Recovery"),
                        )
                    },
                })
            elif item_type == 7:
                potions.append({
                    "id": f"potion_{self._slug(str(entry['name']))}",
                    "name": entry["name"],
                    "source_layer": "potions",
                    "cooldown_seconds": parse_abilityCooldown(description),
                    "duration_seconds": parse_duration(description),
                    "instant_restoration": {
                        key: parse_stat(description, label) or 0
                        for key, label in (("health", "Health"), ("magicka", "Magicka"), ("stamina", "Stamina"))
                    },
                })
        self._write_to_database("foods.json", foods)
        self._write_to_database("potions.json", potions)
        return f"Success! Compiled {len(foods)} foods and {len(potions)} potions into game data."

    def mine_champion_points(self) -> str:
        records = self.client.fetch("cp2Skills")
        return self._mine_records(
            "champion_points.json", records,
            lambda entry: {
                "id": f"cp_{entry.get('id', entry.get('abilityId', ''))}",
                "name": entry.get("name", entry.get("abilityName", "")),
                "source_layer": "champion_points",
                "description": parse_description(str(entry.get("description", ""))),
            } if entry.get("name", entry.get("abilityName")) else None,
        )

    def mine_class_passives(self) -> str:
        records = self.client.fetch("playerSkills")
        classes = {"dragonknight", "nightblade", "sorcerer", "templar", "warden", "necromancer", "arcanist"}
        passives = [
            entry for entry in records
            if str(entry.get("isPassive", "0")).casefold() in {"1", "true"}
            and str(entry.get("skillType", entry.get("class", ""))).casefold() in classes
        ]
        return self._mine_records(
            "class_passives.json", passives,
            lambda entry: {
                "id": f"passive_{entry.get('id', entry.get('abilityId', ''))}",
                "name": entry["name"],
                "class_affinity": str(entry.get("skillType", entry.get("class", ""))).title(),
                "source_layer": "class_passives",
                "effects": parse_effects(parse_description(str(entry.get("description", "")))),
            } if entry.get("name") else None,
        )

    def mine_all(self) -> list[str]:
        return [self.mine_skills(), self.mine_gear_sets(), self.mine_consumables(),
                self.mine_champion_points(), self.mine_class_passives()]


class UESPSkillMiner(TheConsoleDataMiner):
    """Backward-compatible skill-only pipeline used by the Console launcher."""

    def __init__(self, output_directory: str, client: UESPApiClient | None = None):
        super().__init__(output_directory, client)
        self.output_path = self.data_dir / "skills.json"

    def run_mining_pipeline(self) -> str:
        try:
            return self.mine_skills()
        except Exception as error:
            return f"Pipeline execution failed: {error}"


class CrossLinkedSkillMiner(TheConsoleDataMiner):
    """Backward-compatible facade for the former cross-linked skill miner."""

    def mine_skills_by_global_ids(self) -> str:
        return self.mine_skills()

    def mine_gear_sets_by_global_ids(self) -> str:
        return self.mine_gear_sets()

    def mine_champion_points_by_global_ids(self) -> str:
        return self.mine_champion_points()

    def mine_class_passives_by_global_ids(self) -> str:
        return self.mine_class_passives()


def mine_consumables(self: TheConsoleDataMiner) -> str:
    return self.mine_consumables()


def mine_gear_sets_by_global_ids(self: CrossLinkedSkillMiner) -> str:
    return self.mine_gear_sets_by_global_ids()


def mine_champion_points_by_global_ids(self: CrossLinkedSkillMiner) -> str:
    return self.mine_champion_points_by_global_ids()


def mine_class_passives_by_global_ids(self: CrossLinkedSkillMiner) -> str:
    return self.mine_class_passives_by_global_ids()
