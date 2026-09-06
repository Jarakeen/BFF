from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from services.scribing_catalog import (
    compatible_affix as static_compatible_affix,
    compatible_focus as static_compatible_focus,
    compatible_signature as static_compatible_signature,
)


class ScribingSimulatorDataService:
    """Read structured ESO-Hub Scribing simulator compatibility data.

    The imported simulator payload stores each Grimoire's allowed script ids and
    explicit forbidden script combinations. When the structured feed is not
    available, callers can still fall back to the older static catalog.
    """

    SOURCE_KEY = "eso_hub:scribing_simulator_initialize"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.available = False
        self._script_id_by_name: dict[str, int] = {}
        self._script_name_by_id: dict[int, str] = {}
        self._script_type_by_id: dict[int, int] = {}
        self._skill_id_by_name: dict[str, int] = {}
        self._allowed_ids_by_skill: dict[int, tuple[int, ...]] = {}
        self._forbidden_by_skill: dict[int, tuple[frozenset[int], ...]] = {}
        self._load()

    @staticmethod
    def _int_values(value) -> list[int]:
        """Extract integer ids from the payload's nested rule representation."""
        found: list[int] = []
        if isinstance(value, bool):
            return found
        if isinstance(value, int):
            return [value] if value > 0 else []
        if isinstance(value, str):
            try:
                parsed = int(value)
            except ValueError:
                return []
            return [parsed] if parsed > 0 else []
        if isinstance(value, dict):
            for nested in value.values():
                found.extend(ScribingSimulatorDataService._int_values(nested))
            return found
        if isinstance(value, (list, tuple)):
            for nested in value:
                found.extend(ScribingSimulatorDataService._int_values(nested))
        return found

    @classmethod
    def _normalize_forbidden_rules(cls, raw_json: str) -> tuple[frozenset[int], ...]:
        try:
            raw = json.loads(raw_json or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            return ()
        if not isinstance(raw, list):
            raw = [raw]

        rules: list[frozenset[int]] = []
        for entry in raw:
            ids = frozenset(cls._int_values(entry))
            # A forbidden "combination" needs at least two selected scripts.
            # Ignoring singletons keeps malformed metadata from disabling an
            # otherwise valid script globally.
            if len(ids) >= 2 and ids not in rules:
                rules.append(ids)
        return tuple(rules)

    def _load(self) -> None:
        if not self.database_path.is_file():
            return
        try:
            with sqlite3.connect(self.database_path) as connection:
                tables = {
                    str(row[0])
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                required = {
                    "scribing_simulator_script",
                    "scribing_simulator_skill",
                    "scribing_result_name_reference_source",
                }
                if not required.issubset(tables):
                    return

                verified = connection.execute(
                    """
                    SELECT 1
                    FROM scribing_result_name_reference_source
                    WHERE source_key = ? AND probe_verified = 1
                    LIMIT 1
                    """,
                    (self.SOURCE_KEY,),
                ).fetchone()
                if verified is None:
                    return

                script_rows = connection.execute(
                    """
                    SELECT script_id, script_type, name
                    FROM scribing_simulator_script
                    WHERE source_key = ?
                    """,
                    (self.SOURCE_KEY,),
                ).fetchall()
                skill_rows = connection.execute(
                    """
                    SELECT skill_id, name, scripts_json, forbidden_combinations_json
                    FROM scribing_simulator_skill
                    WHERE source_key = ?
                    """,
                    (self.SOURCE_KEY,),
                ).fetchall()
        except sqlite3.Error:
            return

        for script_id, script_type, name in script_rows:
            script_id = int(script_id or 0)
            name = str(name or "").strip()
            if script_id <= 0 or not name:
                continue
            self._script_id_by_name[name] = script_id
            self._script_name_by_id[script_id] = name
            self._script_type_by_id[script_id] = int(script_type or 0)

        for skill_id, name, scripts_json, forbidden_json in skill_rows:
            skill_id = int(skill_id or 0)
            name = str(name or "").strip()
            if skill_id <= 0 or not name:
                continue
            try:
                raw_ids = json.loads(str(scripts_json or "[]"))
            except (TypeError, ValueError, json.JSONDecodeError):
                raw_ids = []
            allowed = tuple(
                script_id
                for script_id in self._int_values(raw_ids)
                if script_id in self._script_name_by_id
            )
            self._skill_id_by_name[name] = skill_id
            self._allowed_ids_by_skill[skill_id] = allowed
            self._forbidden_by_skill[skill_id] = self._normalize_forbidden_rules(str(forbidden_json or "[]"))

        self.available = bool(self._skill_id_by_name and self._script_id_by_name)

    def _names_for_type(self, grimoire: str, script_type: int) -> list[str]:
        skill_id = self._skill_id_by_name.get(str(grimoire).strip())
        if not skill_id:
            return []
        return sorted(
            (
                self._script_name_by_id[script_id]
                for script_id in self._allowed_ids_by_skill.get(skill_id, ())
                if self._script_type_by_id.get(script_id) == script_type
            ),
            key=str.casefold,
        )

    def compatible_focus(self, grimoire: str) -> list[str]:
        values = self._names_for_type(grimoire, 1)
        return values if values or self.available else static_compatible_focus(grimoire)

    def compatible_signature(self, grimoire: str) -> list[str]:
        values = self._names_for_type(grimoire, 2)
        return values if values or self.available else static_compatible_signature(grimoire)

    def compatible_affix(self, grimoire: str) -> list[str]:
        values = self._names_for_type(grimoire, 3)
        return values if values or self.available else static_compatible_affix(grimoire)

    def is_combination_allowed(self, grimoire: str, script_names: Iterable[str]) -> bool:
        if not self.available:
            return True
        skill_id = self._skill_id_by_name.get(str(grimoire).strip())
        if not skill_id:
            return False
        selected_ids = {
            self._script_id_by_name[name]
            for name in (str(value or "").strip() for value in script_names)
            if name and name in self._script_id_by_name
        }
        return not any(rule.issubset(selected_ids) for rule in self._forbidden_by_skill.get(skill_id, ()))

    def filtered_choices(
        self,
        grimoire: str,
        script_type: int,
        selected_names: Iterable[str],
    ) -> list[str]:
        if script_type == 1:
            candidates = self.compatible_focus(grimoire)
        elif script_type == 2:
            candidates = self.compatible_signature(grimoire)
        elif script_type == 3:
            candidates = self.compatible_affix(grimoire)
        else:
            return []
        selected = [str(value or "").strip() for value in selected_names if str(value or "").strip()]
        return [
            candidate
            for candidate in candidates
            if self.is_combination_allowed(grimoire, [*selected, candidate])
        ]
