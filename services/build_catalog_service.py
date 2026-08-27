from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from models.build_model import BuildRoster, PlayerBuild


SCHEMA_VERSION = 2


class BuildCatalogService:
    """Canonical persistence boundary for characters and reusable builds.

    `data/eso.db` remains read-only reference data. User-owned character/build
    state is persisted separately. The legacy Builds JSON can be imported once
    and retained as a compatibility source while callers migrate to this
    catalog.

    The catalog deliberately stores identity/configuration metadata separately
    from calculated MinMax results. Calculated state must remain ephemeral and
    reproducible from the canonical build.
    """

    def __init__(self, catalog_path: Path):
        self.catalog_path = Path(catalog_path)

    @staticmethod
    def _stable_id(kind: str, value: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"bff:{kind}:{value}"))

    @classmethod
    def _identity_for(cls, build: PlayerBuild, index: int) -> str:
        value = build.Gamertag.strip().casefold() or build.Name.strip().casefold()
        return value or f"member-{index + 1}"

    def new_catalog(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "characters": [], "builds": []}

    def load(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            return self.new_catalog()
        try:
            data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self.new_catalog()
        return self._normalize(data)

    def save(self, catalog: dict[str, Any]) -> None:
        normalized = self._normalize(catalog)
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.catalog_path.with_suffix(self.catalog_path.suffix + ".tmp")
        temp.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.catalog_path)

    @staticmethod
    def _normalize(data: dict[str, Any] | None) -> dict[str, Any]:
        data = data if isinstance(data, dict) else {}
        return {
            "schema_version": SCHEMA_VERSION,
            "characters": list(data.get("characters") or []),
            "builds": list(data.get("builds") or []),
        }

    def import_legacy_roster(self, roster: BuildRoster) -> dict[str, Any]:
        """Convert the existing flat BuildRoster into the canonical catalog.

        Existing values are preserved. A character is created once per stable
        character identity and each legacy row becomes one reusable build.
        No ESO reference data is copied into the catalog.
        """
        catalog = self.new_catalog()
        characters: dict[str, dict[str, Any]] = {}

        for index, member in enumerate(roster.Members):
            member.ensure_ids(index)
            identity = self._identity_for(member, index)
            character_id = member.CharacterId or self._stable_id("character", identity)
            member.CharacterId = character_id
            if not member.BuildId:
                member.BuildId = self._stable_id(
                    "build",
                    f"{character_id}:{member.BuildName.strip().casefold() or index}",
                )

            if character_id not in characters:
                characters[character_id] = {
                    "character_id": character_id,
                    "name": member.Name,
                    "gamertag": member.Gamertag,
                    "eso_class": member.EsoClass,
                    "race": member.Race,
                    "role": member.Role,
                    "alliance": member.Alliance,
                    "vampire": member.Vampire,
                    "werewolf": member.Werewolf,
                    "mastered_class_skill_lines": list(member.MasteredClassSkillLines),
                }
            else:
                character = characters[character_id]
                # Fill identity fields only when an older/alternate build did
                # not have them. Conflicting edits remain build-owned data.
                for key, value in {
                    "name": member.Name,
                    "gamertag": member.Gamertag,
                    "eso_class": member.EsoClass,
                    "race": member.Race,
                    "role": member.Role,
                    "alliance": member.Alliance,
                }.items():
                    if not character.get(key) and value:
                        character[key] = value

            catalog["builds"].append({
                "build_id": member.BuildId,
                "character_id": character_id,
                "name": member.BuildName,
                "legacy": member.to_dict(),
            })

        catalog["characters"] = list(characters.values())
        return catalog

    def import_legacy_file(self, legacy_path: Path) -> dict[str, Any]:
        legacy_path = Path(legacy_path)
        if not legacy_path.exists():
            return self.new_catalog()
        try:
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self.new_catalog()
        roster = BuildRoster.from_dict(data)
        return self.import_legacy_roster(roster)

    def characters(self) -> list[dict[str, Any]]:
        return self.load()["characters"]

    def builds_for_character(self, character_id: str) -> list[dict[str, Any]]:
        return [
            build
            for build in self.load()["builds"]
            if build.get("character_id") == character_id
        ]
