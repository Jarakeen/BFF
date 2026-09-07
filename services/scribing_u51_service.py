from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class U51ScribingResolution:
    result_name: str = ""
    description: str = ""
    ability_id: int = 0


class U51ScribingService:
    """Read the normalized Update 51 PTS scribing catalog from eso.db."""

    SOURCE_KEY = "uesp:esolog:u51pts:scribing"
    DESCRIPTION_SOURCE_KEY = "uesp:esolog:craftedScriptDescriptions51pts"

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.available = False
        self._crafted_id_by_name: dict[str, int] = {}
        self._skill_line_type_by_name: dict[str, int] = {}
        self._script_id_by_name: dict[str, int] = {}
        self._script_name_by_id: dict[int, str] = {}
        self._script_slot_by_id: dict[int, int] = {}
        self._allowed_by_skill_slot: dict[tuple[int, int], tuple[int, ...]] = {}
        self._descriptions: dict[tuple[int, int, int], U51ScribingResolution] = {}
        self._load()

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
                    "scribing_u51_source",
                    "scribing_u51_script",
                    "scribing_u51_crafted_skill",
                    "scribing_u51_skill_script",
                    "scribing_crafted_script_description",
                }
                if not required.issubset(tables):
                    return

                skills = connection.execute(
                    """
                    SELECT crafted_ability_id, skill_type, name
                    FROM scribing_u51_crafted_skill
                    WHERE source_key = ?
                    """,
                    (self.SOURCE_KEY,),
                ).fetchall()
                scripts = connection.execute(
                    """
                    SELECT script_id, slot, name
                    FROM scribing_u51_script
                    WHERE source_key = ?
                    """,
                    (self.SOURCE_KEY,),
                ).fetchall()
                compatibility = connection.execute(
                    """
                    SELECT crafted_ability_id, slot, script_id
                    FROM scribing_u51_skill_script
                    WHERE source_key = ?
                    ORDER BY crafted_ability_id, slot, script_id
                    """,
                    (self.SOURCE_KEY,),
                ).fetchall()
                descriptions = connection.execute(
                    """
                    SELECT crafted_ability_id, script_id, class_id,
                           ability_id, name, description
                    FROM scribing_crafted_script_description
                    WHERE source_key = ?
                    """,
                    (self.DESCRIPTION_SOURCE_KEY,),
                ).fetchall()
        except sqlite3.Error:
            return

        for crafted_id, skill_type, name in skills:
            clean = str(name or "").strip()
            if clean:
                self._crafted_id_by_name[clean] = int(crafted_id or 0)
                self._skill_line_type_by_name[clean] = int(skill_type or 0)

        for script_id, slot, name in scripts:
            script_id = int(script_id or 0)
            clean = str(name or "").strip()
            if script_id > 0 and clean:
                self._script_id_by_name[clean] = script_id
                self._script_name_by_id[script_id] = clean
                self._script_slot_by_id[script_id] = int(slot or 0)

        grouped: dict[tuple[int, int], list[int]] = {}
        for crafted_id, slot, script_id in compatibility:
            grouped.setdefault((int(crafted_id), int(slot)), []).append(int(script_id))
        self._allowed_by_skill_slot = {
            key: tuple(values) for key, values in grouped.items()
        }

        for crafted_id, script_id, class_id, ability_id, name, description in descriptions:
            key = (int(crafted_id), int(script_id), int(class_id or 0))
            self._descriptions[key] = U51ScribingResolution(
                result_name=str(name or "").strip(),
                description=str(description or "").strip(),
                ability_id=int(ability_id or 0),
            )

        self.available = bool(self._crafted_id_by_name and self._script_id_by_name)

    def grimoire_names(self) -> list[str]:
        return sorted(self._crafted_id_by_name, key=str.casefold)

    def _compatible(self, grimoire: str, slot: int) -> list[str]:
        crafted_id = self._crafted_id_by_name.get(str(grimoire or "").strip())
        if not crafted_id:
            return []
        return sorted(
            (
                self._script_name_by_id[script_id]
                for script_id in self._allowed_by_skill_slot.get((crafted_id, slot), ())
                if script_id in self._script_name_by_id
            ),
            key=str.casefold,
        )

    def compatible_focus(self, grimoire: str) -> list[str]:
        return self._compatible(grimoire, 1)

    def compatible_signature(self, grimoire: str) -> list[str]:
        return self._compatible(grimoire, 2)

    def compatible_affix(self, grimoire: str) -> list[str]:
        return self._compatible(grimoire, 3)

    def _resolution(self, grimoire: str, script_name: str, class_id: int = 0) -> U51ScribingResolution:
        crafted_id = self._crafted_id_by_name.get(str(grimoire or "").strip())
        script_id = self._script_id_by_name.get(str(script_name or "").strip())
        if not crafted_id or not script_id:
            return U51ScribingResolution()
        exact = self._descriptions.get((crafted_id, script_id, int(class_id or 0)))
        if exact:
            return exact
        return self._descriptions.get((crafted_id, script_id, 0), U51ScribingResolution())

    def result_name(self, grimoire: str, focus: str, class_id: int = 0) -> str:
        return self._resolution(grimoire, focus, class_id).result_name

    def result_ability_id(self, grimoire: str, focus: str, class_id: int = 0) -> int:
        return self._resolution(grimoire, focus, class_id).ability_id

    def description_for_script(
        self,
        grimoire: str,
        script_name: str,
        class_id: int = 0,
    ) -> str:
        return self._resolution(grimoire, script_name, class_id).description

    def combined_description(
        self,
        grimoire: str,
        focus: str,
        signature: str,
        affix: str,
        class_id: int = 0,
    ) -> str:
        parts: list[str] = []
        for label, script_name in (
            ("Focus", focus),
            ("Signature", signature),
            ("Affix", affix),
        ):
            if not str(script_name or "").strip():
                continue
            description = self.description_for_script(grimoire, script_name, class_id)
            if description and description not in parts:
                parts.append(f"{label}: {description}")
        return "\n".join(parts)
