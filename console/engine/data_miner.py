"""Offline data builders for the Console reference database."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

try:
    from ..parsers import (
        parse_abilityCooldown, parse_description, parse_duration, parse_effects,
        parse_range, parse_skillCoef, parse_stat, parse_target,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from console.parsers import (
        parse_abilityCooldown, parse_description, parse_duration, parse_effects,
        parse_range, parse_skillCoef, parse_stat, parse_target,
    )

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
LOGGER = logging.getLogger("DataBuilderService")


class DataBuilderService:
    """Build normalized FoundryDock data from local raw JSON files without network access."""

    def __init__(self, data_directory: str | Path, raw_directory: str | Path | None = None):
        self.data_dir = Path(data_directory)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = Path(raw_directory) if raw_directory is not None else self._resolve_raw_dir()
        self.logger = LOGGER

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        try:
            return float(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            return default

    def _resolve_raw_dir(self) -> Path:
        candidates = [
            self.data_dir / "raw",
            self.data_dir.parent / "raw data",
            self.data_dir / ".." / "raw data",
            self.data_dir.parent.parent / "raw data",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return (self.data_dir / "raw").resolve()

    def _source_path(self, file_name: str) -> Path:
        candidate = self.raw_dir / file_name
        if candidate.exists():
            return candidate
        legacy = self.data_dir.parent / file_name
        if legacy.exists():
            return legacy
        raise FileNotFoundError(f"Unable to locate raw data file: {file_name} in {self.raw_dir}")

    def _read_raw_records(self, file_name: str, key: str | None = None) -> list[dict[str, Any]]:
        path = self._source_path(file_name)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected object payload in {path}")
        records = payload.get(key, payload.get("records", [])) if key else payload.get("records", [])
        if not isinstance(records, list):
            raise ValueError(f"Expected a list of records in {path}")
        read_records = [record for record in records if isinstance(record, dict)]
        self.logger.info("Read %s raw records from %s", len(read_records), path)
        return read_records

    def _write_to_database(self, file_name: str, data: list[dict[str, Any]]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.data_dir / file_name
        with output_path.open("w", encoding="utf-8") as output:
            json.dump(data, output, indent=2, ensure_ascii=False)
        self.logger.info("Wrote %s normalized records to %s", len(data), output_path)

    def _collect_source_ids(self, record: dict[str, Any]) -> dict[str, Any]:
        candidate_keys = (
            "id",
            "displayId",
            "itemId",
            "abilityId",
            "baseAbilityId",
            "skillId",
            "parentSkillId",
            "disciplineId",
            "setId",
            "sourceId",
        )
        source_ids: dict[str, Any] = {}
        for key in candidate_keys:
            value = record.get(key)
            if value in (None, "", [], {}):
                continue
            source_ids[key] = value
        return source_ids

    def _normalize_records(
        self,
        output_file: str,
        records: list[dict[str, Any]],
        builder: Callable[[dict[str, Any]], dict[str, Any] | None],
        source_file: str,
        source_key: str | None = None,
    ) -> str:
        normalized: list[dict[str, Any]] = []
        skipped = 0
        skipped_reasons: dict[str, int] = {}
        for index, raw in enumerate(records, start=1):
            if not isinstance(raw, dict):
                skipped += 1
                skipped_reasons["non_object"] = skipped_reasons.get("non_object", 0) + 1
                continue
            try:
                record = builder(raw)
            except ValueError as error:
                skipped += 1
                reason = str(error)
                skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
                continue
            if record is not None:
                normalized.append(record)
        self._write_to_database(output_file, normalized)
        if skipped:
            reason_summary = ", ".join(f"{reason}={count}" for reason, count in sorted(skipped_reasons.items()))
            self.logger.info("Skipped %s records while building %s (%s)", skipped, output_file, reason_summary)
        return f"Built {len(normalized)} normalized records into {self.data_dir / output_file}"

    def build_skills(self) -> str:
        records = self._read_raw_records("skills_raw.json", "playerSkills")

        def build(entry: dict[str, Any]) -> dict[str, Any] | None:
            name = str(entry.get("name", "")).strip()
            if not name:
                raise ValueError("missing skill name")
            description = parse_description(str(entry.get("description", "")))
            coefficients = parse_skillCoef(description)
            return {
                "id": f"skill_{entry.get('id', entry.get('abilityId', ''))}",
                "name": name,
                "source_layer": "skills",
                "source_ids": self._collect_source_ids(entry),
                "base_ability_id": entry.get("baseAbilityId", entry.get("abilityId")),
                "cooldown_seconds": parse_abilityCooldown(description),
                "duration_seconds": parse_duration(description),
                "range_meters": parse_range(description),
                "target": parse_target(description),
                "effects": parse_effects(description),
                "coefficients": {
                    "coeff_a": coefficients.get("coeff_a", self._number(entry.get("a1"))),
                    "coeff_b": coefficients.get("coeff_b", self._number(entry.get("b1"))),
                },
                "is_passive": str(entry.get("isPassive", "0")).casefold() in {"1", "true"},
            }

        return self._normalize_records("skills.json", records, build, "skills_raw.json", "playerSkills")

    def build_gear_sets(self) -> str:
        records = self._read_raw_records("gear_sets_raw.json", "minedItemSummary")

        def build(entry: dict[str, Any]) -> dict[str, Any] | None:
            name = str(entry.get("setName", entry.get("name", ""))).strip()
            if not name:
                raise ValueError("missing gear set name")
            return {
                "id": f"set_{self._slug(name)}",
                "name": name,
                "source_layer": "gear_sets",
                "source_ids": self._collect_source_ids(entry),
                "armor_type": entry.get("armorType"),
                "bonuses": {
                    f"{pieces}_piece": entry.get(f"setBonusDesc{pieces}")
                    for pieces in (2, 3, 4, 5)
                    if entry.get(f"setBonusDesc{pieces}")
                },
                "bonus_5_ability_id": entry.get("bonus5AbilityId"),
            }

        return self._normalize_records("gear_sets.json", records, build, "gear_sets_raw.json", "minedItemSummary")

    def build_consumables(self) -> str:
        food_records = self._read_raw_records("food_raw.json", "minedItemSummary")
        drink_records = self._read_raw_records("drinks_raw.json", "minedItemSummary")
        all_records = food_records + drink_records

        foods: list[dict[str, Any]] = []
        potions: list[dict[str, Any]] = []
        seen: set[tuple[Any, Any]] = set()
        for index, entry in enumerate(all_records, start=1):
            name = str(entry.get("name", "")).strip()
            if not name:
                self.logger.warning("Skipped consumable record %s: missing name", index)
                continue
            key = (entry.get("itemId", entry.get("id")), name)
            if key in seen:
                continue
            seen.add(key)
            description = parse_description(str(entry.get("description", "")))
            item_type = self._number(entry.get("type"), -1)
            if item_type in (4, 12):
                foods.append({
                    "id": f"food_{self._slug(name)}",
                    "name": name,
                    "source_layer": "foods",
                    "source_ids": self._collect_source_ids(entry),
                    "duration_seconds": parse_duration(description),
                    "stats_provided": {
                        key_name: parse_stat(description, label) or 0
                        for key_name, label in (
                            ("max_health", "Max Health"), ("max_magicka", "Max Magicka"),
                            ("max_stamina", "Max Stamina"), ("magicka_recovery", "Magicka Recovery"),
                            ("stamina_recovery", "Stamina Recovery"),
                        )
                    },
                })
            elif item_type == 7:
                potions.append({
                    "id": f"potion_{self._slug(name)}",
                    "name": name,
                    "source_layer": "potions",
                    "source_ids": self._collect_source_ids(entry),
                    "cooldown_seconds": parse_abilityCooldown(description),
                    "duration_seconds": parse_duration(description),
                    "instant_restoration": {
                        key_name: parse_stat(description, label) or 0
                        for key_name, label in (("health", "Health"), ("magicka", "Magicka"), ("stamina", "Stamina"))
                    },
                })
            else:
                self.logger.warning("Skipped consumable record %s for %s: unsupported item type %s", index, name, entry.get("type"))
        self._write_to_database("foods.json", foods)
        self._write_to_database("potions.json", potions)
        return f"Built {len(foods)} foods and {len(potions)} potions"

    def build_champion_points(self) -> str:
        records = self._read_raw_records("champion_points_raw.json", "cp2Skills")

        def build(entry: dict[str, Any]) -> dict[str, Any] | None:
            name = str(entry.get("name", entry.get("abilityName", ""))).strip()
            if not name:
                raise ValueError("missing champion point name")
            description = parse_description(str(entry.get("minDescription", "")))
            return {
                "id": f"cp_{entry.get('id', entry.get('abilityId', ''))}",
                "name": name,
                "source_layer": "champion_points",
                "source_ids": self._collect_source_ids(entry),
                "description": description,
            }

        return self._normalize_records("champion_points.json", records, build, "champion_points_raw.json", "cp2Skills")

    def build_class_passives(self) -> str:
        records = self._read_raw_records("skills_raw.json", "playerSkills")
        classes = {"dragonknight", "nightblade", "sorcerer", "templar", "warden", "necromancer", "arcanist"}
        passives: list[dict[str, Any]] = []
        for index, entry in enumerate(records, start=1):
            name = str(entry.get("name", "")).strip()
            if not name:
                self.logger.warning("Skipped class passive record %s: missing name", index)
                continue
            is_passive = str(entry.get("isPassive", "0")).casefold() in {"1", "true"}
            affinity = str(entry.get("classType") or entry.get("skillType") or entry.get("class", "")).strip()
            if not is_passive or affinity.casefold() not in classes:
                continue
            description = parse_description(str(entry.get("description", "")))
            passives.append({
                "id": f"passive_{entry.get('id', entry.get('abilityId', ''))}",
                "name": name,
                "class_affinity": affinity.title(),
                "source_layer": "class_passives",
                "source_ids": self._collect_source_ids(entry),
                "effects": parse_effects(description),
            })
        self._write_to_database("class_passives.json", passives)
        return f"Built {len(passives)} class passives"

    def build_all(self) -> list[str]:
        return [
            self.build_skills(),
            self.build_gear_sets(),
            self.build_consumables(),
            self.build_champion_points(),
            self.build_class_passives(),
        ]


class TheConsoleDataMiner(DataBuilderService):
    """Backward-compatible name for the offline local builder."""


class UESPSkillMiner(DataBuilderService):
    """Backward-compatible skill-only pipeline used by the Console launcher."""

    def __init__(self, output_directory: str | Path, raw_directory: str | Path | None = None):
        super().__init__(output_directory, raw_directory)
        self.output_path = self.data_dir / "skills.json"

    def run_mining_pipeline(self) -> str:
        try:
            return self.build_skills()
        except Exception as error:  # pragma: no cover - defensive path
            return f"Pipeline execution failed: {error}"


class CrossLinkedSkillMiner(DataBuilderService):
    """Backward-compatible facade for the former cross-linked skill miner."""

    def mine_skills_by_global_ids(self) -> str:
        return self.build_skills()

    def mine_gear_sets_by_global_ids(self) -> str:
        return self.build_gear_sets()

    def mine_champion_points_by_global_ids(self) -> str:
        return self.build_champion_points()

    def mine_class_passives_by_global_ids(self) -> str:
        return self.build_class_passives()


def mine_consumables(self: DataBuilderService) -> str:
    return self.build_consumables()


def mine_gear_sets_by_global_ids(self: CrossLinkedSkillMiner) -> str:
    return self.mine_gear_sets_by_global_ids()


def mine_champion_points_by_global_ids(self: CrossLinkedSkillMiner) -> str:
    return self.mine_champion_points_by_global_ids()


def mine_class_passives_by_global_ids(self: CrossLinkedSkillMiner) -> str:
    return self.mine_class_passives_by_global_ids()
