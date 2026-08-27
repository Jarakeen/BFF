from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from models.build_model import BuildRoster, PlayerBuild

SCHEMA_VERSION = 2


class BuildCatalogService:
    """Persist character identity separately from reusable build configs.

    eso.db remains read-only ESO reference data. User-owned state lives here.
    Existing builds.json can be migrated without changing or deleting it.
    """

    def __init__(self, catalog_path: Path):
        self.catalog_path = Path(catalog_path)

    @staticmethod
    def _stable_id(kind: str, value: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"bff:{kind}:{value}"))

    @staticmethod
    def _identity(build: PlayerBuild, index: int) -> str:
        return (
            build.Gamertag.strip().casefold()
            or build.Name.strip().casefold()
            or f"member-{index + 1}"
        )

    @staticmethod
    def _has_meaningful_value(value: Any) -> bool:
        """Return whether a legacy field contains actual user data."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, bool):
            return value
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True

    @classmethod
    def _is_empty_member(cls, build: PlayerBuild) -> bool:
        """Return True for the blank rows used by the legacy roster UI."""
        data = build.to_dict()
        return not any(
            cls._has_meaningful_value(value)
            for key, value in data.items()
            if key not in {"Vampire", "Werewolf"}
        ) and not build.Vampire and not build.Werewolf

    @staticmethod
    def _normalize(data: Any) -> dict[str, Any]:
        data = data if isinstance(data, dict) else {}
        return {
            "schema_version": SCHEMA_VERSION,
            "characters": list(data.get("characters") or []),
            "builds": list(data.get("builds") or []),
        }

    def new_catalog(self) -> dict[str, Any]:
        """Return a new empty canonical catalog with the current schema version."""
        return self._normalize(None)

    def load(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            return self._normalize(None)
        try:
            return self._normalize(
                json.loads(self.catalog_path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError):
            return self._normalize(None)

    def save(self, catalog: dict[str, Any]) -> None:
        normalized = self._normalize(catalog)
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.catalog_path.with_suffix(self.catalog_path.suffix + ".tmp")
        temp.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.catalog_path)

    def import_legacy_roster(self, roster: BuildRoster) -> dict[str, Any]:
        """Create one character record per stable identity and one build per row.

        Completely blank rows in the legacy Builds UI are placeholders and are
        intentionally excluded from the canonical catalog.
        """
        catalog = self._normalize(None)
        characters: dict[str, dict[str, Any]] = {}

        for index, member in enumerate(roster.Members):
            if self._is_empty_member(member):
                continue

            identity = self._identity(member, index)
            character_id = self._stable_id("character", identity)
            build_id = self._stable_id(
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
                }

            legacy = member.to_dict()
            legacy["CharacterId"] = character_id
            legacy["BuildId"] = build_id
            catalog["builds"].append({
                "build_id": build_id,
                "character_id": character_id,
                "name": member.BuildName,
                "legacy": legacy,
            })

        catalog["characters"] = list(characters.values())
        return catalog

    def import_legacy_file(self, legacy_path: Path) -> dict[str, Any]:
        """Load a legacy builds.json file and convert it to the canonical catalog."""
        roster = BuildRoster.from_dict(
            json.loads(Path(legacy_path).read_text(encoding="utf-8"))
        )
        return self.import_legacy_roster(roster)

    def migrate_if_needed(self, legacy_path: Path) -> dict[str, Any]:
        current = self.load()
        if current["characters"] or current["builds"] or not Path(legacy_path).exists():
            return current
        migrated = self.import_legacy_file(legacy_path)
        self.save(migrated)
        return migrated

    def characters(self) -> list[dict[str, Any]]:
        return self.load()["characters"]

    def builds_for_character(self, character_id: str) -> list[dict[str, Any]]:
        return [
            build for build in self.load()["builds"]
            if build.get("character_id") == character_id
        ]
