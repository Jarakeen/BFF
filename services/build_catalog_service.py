from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from models.build_model import BuildRoster, PlayerBuild


CATALOG_SCHEMA_VERSION = 2


class BuildCatalogService:
    """Persistent canonical catalog of characters and their builds.

    A character is an identity. A build is a configuration belonging to
    that identity. This keeps one character reusable across multiple builds
    and gives consumers such as Optimization a stable reference instead of
    recreating a character from a UI-local roster slot.

    The catalog deliberately stores serialized PlayerBuild payloads for now.
    Mechanical conversion into minmax.character_build.CharacterBuild belongs
    at the application/engine boundary and must not be duplicated here.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    # --------------------------------------------------
    # Catalog lifecycle
    # --------------------------------------------------

    @staticmethod
    def new_catalog() -> dict[str, Any]:
        return {
            "schema_version": CATALOG_SCHEMA_VERSION,
            "characters": [],
            "builds": [],
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.new_catalog()

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self.new_catalog()

        return self._normalize(data)

    def save(self, catalog: dict[str, Any]) -> None:
        normalized = self._normalize(catalog)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # --------------------------------------------------
    # Legacy migration
    # --------------------------------------------------

    def import_legacy_roster(self, roster: BuildRoster) -> dict[str, Any]:
        """Convert the old one-build-per-roster-slot model into the catalog.

        Character identity is keyed by gamertag when available, otherwise by
        character name. Blank placeholder members are ignored. Multiple
        legacy builds for the same identity become separate build records
        pointing at one character record.
        """
        catalog = self.new_catalog()
        characters_by_key: dict[str, dict[str, Any]] = {}

        for member in roster.Members:
            if not member.Name.strip() and not member.Gamertag.strip():
                continue

            identity_key = self._identity_key(member)
            character = characters_by_key.get(identity_key)

            if character is None:
                character = {
                    "character_id": self._stable_id("character", identity_key),
                    "name": member.Name.strip(),
                    "gamertag": member.Gamertag.strip(),
                }
                characters_by_key[identity_key] = character
                catalog["characters"].append(character)

            payload = member.to_dict()
            build_name = member.BuildName.strip() or "Default"
            build_id = self._stable_id(
                "build",
                f"{character['character_id']}:{build_name}",
            )

            catalog["builds"].append(
                {
                    "build_id": build_id,
                    "character_id": character["character_id"],
                    "name": build_name,
                    "payload": payload,
                }
            )

        return self._normalize(catalog)

    # --------------------------------------------------
    # Canonical access
    # --------------------------------------------------

    def get_character(self, character_id: str) -> dict[str, Any] | None:
        catalog = self.load()
        for character in catalog["characters"]:
            if character.get("character_id") == character_id:
                return copy.deepcopy(character)
        return None

    def get_build(self, build_id: str) -> dict[str, Any] | None:
        catalog = self.load()
        for build in catalog["builds"]:
            if build.get("build_id") == build_id:
                return copy.deepcopy(build)
        return None

    def builds_for_character(self, character_id: str) -> list[dict[str, Any]]:
        catalog = self.load()
        return [
            copy.deepcopy(build)
            for build in catalog["builds"]
            if build.get("character_id") == character_id
        ]

    def upsert_build(
        self,
        *,
        character_id: str,
        build_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert or replace one canonical build without duplicating identity."""
        catalog = self.load()
        name = build_name.strip() or "Default"
        build_id = self._stable_id("build", f"{character_id}:{name}")

        record = {
            "build_id": build_id,
            "character_id": character_id,
            "name": name,
            "payload": copy.deepcopy(payload),
        }

        for index, existing in enumerate(catalog["builds"]):
            if existing.get("build_id") == build_id:
                catalog["builds"][index] = record
                self.save(catalog)
                return copy.deepcopy(record)

        catalog["builds"].append(record)
        self.save(catalog)
        return copy.deepcopy(record)

    # --------------------------------------------------
    # Normalization
    # --------------------------------------------------

    def _normalize(self, catalog: dict[str, Any]) -> dict[str, Any]:
        data = dict(catalog or {})
        data["schema_version"] = CATALOG_SCHEMA_VERSION
        data["characters"] = [
            dict(character)
            for character in data.get("characters", [])
            if isinstance(character, dict)
        ]
        data["builds"] = [
            dict(build)
            for build in data.get("builds", [])
            if isinstance(build, dict)
        ]

        for character in data["characters"]:
            character.setdefault("character_id", "")
            character.setdefault("name", "")
            character.setdefault("gamertag", "")

        for build in data["builds"]:
            build.setdefault("build_id", "")
            build.setdefault("character_id", "")
            build.setdefault("name", "Default")
            build.setdefault("payload", {})

        return data

    @staticmethod
    def _identity_key(member: PlayerBuild) -> str:
        value = member.Gamertag.strip() or member.Name.strip()
        return " ".join(value.casefold().split())

    @staticmethod
    def _stable_id(kind: str, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
        return f"{kind}_{digest}"
