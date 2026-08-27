from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from minmax.character_build.character import Character
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import (
    ClassMasteryConfiguration,
    ClassSkillLineConfiguration,
)
from minmax.role import Role


SCHEMA_VERSION = 1


class CanonicalBuildService:
    """Persistence boundary for canonical characters and their builds.

    The ESO database remains reference data. Character/build state is user
    data and is stored separately in JSON. The file is deliberately versioned
    so the legacy Builds page can be migrated without making eso.db part of
    the user's mutable state.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": SCHEMA_VERSION, "characters": [], "builds": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": SCHEMA_VERSION, "characters": [], "builds": []}
        if not isinstance(data, dict):
            return {"schema_version": SCHEMA_VERSION, "characters": [], "builds": []}
        return self._normalize(data)

    def save(self, data: dict[str, Any]) -> None:
        normalized = self._normalize(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "characters": list(data.get("characters") or []),
            "builds": list(data.get("builds") or []),
        }

    @staticmethod
    def character_to_dict(character: Character) -> dict[str, Any]:
        return {
            "character_id": character.character_id,
            "name": character.name,
            "character_class": character.character_class.value,
            "role": character.role.value,
            "race_id": character.race_id,
            "mastered_class_skill_lines": sorted(character.mastered_class_skill_lines),
            "vampire": character.vampire,
            "werewolf": character.werewolf,
        }

    @staticmethod
    def character_from_dict(data: dict[str, Any]) -> Character:
        return Character(
            character_id=str(data.get("character_id") or ""),
            name=str(data.get("name") or ""),
            character_class=CharacterClass(str(data.get("character_class"))),
            role=Role(str(data.get("role"))),
            race_id=data.get("race_id"),
            mastered_class_skill_lines=frozenset(data.get("mastered_class_skill_lines") or []),
            vampire=bool(data.get("vampire", False)),
            werewolf=bool(data.get("werewolf", False)),
        )

    @staticmethod
    def class_configuration_to_dict(config: ClassSkillLineConfiguration) -> dict[str, Any]:
        return {
            "equipped_skill_lines": list(config.equipped_skill_lines),
            "class_mastery": {
                "passive_ability_ids": list(config.class_mastery.passive_ability_ids),
            },
        }

    @staticmethod
    def class_configuration_from_dict(data: dict[str, Any] | None) -> ClassSkillLineConfiguration:
        data = data or {}
        mastery = data.get("class_mastery") or {}
        return ClassSkillLineConfiguration(
            equipped_skill_lines=tuple(str(x) for x in data.get("equipped_skill_lines") or []),
            class_mastery=ClassMasteryConfiguration(
                passive_ability_ids=tuple(int(x) for x in mastery.get("passive_ability_ids") or []),
            ),
        )
