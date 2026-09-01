from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from models.build_model import BuildRoster, PlayerBuild

SCHEMA_VERSION = 3


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
        name = build.Name.strip().casefold()
        gamertag = build.Gamertag.strip().casefold()
        if name:
            return f"{gamertag or 'unknown-account'}:{name}"
        if gamertag:
            return f"{gamertag}:unnamed-{index + 1}"
        return f"member-{index + 1}"

    @staticmethod
    def _character_match_key(name: object, gamertag: object) -> tuple[str, str]:
        return (
            str(gamertag or "").strip().casefold(),
            str(name or "").strip().casefold(),
        )

    @staticmethod
    def _normalize_owned_skill_lines(value: Any) -> list[str]:
        if not isinstance(value, (list, tuple, set)):
            return []
        seen: set[str] = set()
        normalized: list[str] = []
        for entry in value:
            name = " ".join(str(entry or "").strip().split())
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            normalized.append(name)
        return normalized

    @staticmethod
    def _normalize_named_nonnegative_ints(value: Any) -> dict[str, int]:
        """Normalize explicit character progression values.

        Zero is intentionally preserved. It means the player explicitly
        recorded that the passive/CP node is not purchased. An absent key means
        the value is unknown and must not be silently treated as zero.
        """
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, int] = {}
        seen: set[str] = set()
        for raw_name, raw_value in value.items():
            name = " ".join(str(raw_name or "").strip().split())
            key = name.casefold()
            if not name or key in seen:
                continue
            try:
                number = int(raw_value)
            except (TypeError, ValueError):
                continue
            if number < 0:
                continue
            seen.add(key)
            normalized[name] = number
        return normalized

    @classmethod
    def _normalize_passive_ranks(cls, value: Any) -> dict[str, int]:
        return cls._normalize_named_nonnegative_ints(value)

    @classmethod
    def _normalize_passive_cp_points(cls, value: Any) -> dict[str, int]:
        return cls._normalize_named_nonnegative_ints(value)

    @classmethod
    def _normalize_character(cls, value: Any) -> dict[str, Any]:
        character = copy.deepcopy(value) if isinstance(value, dict) else {}
        character["owned_skill_lines"] = cls._normalize_owned_skill_lines(
            character.get("owned_skill_lines")
        )
        character["passive_ranks"] = cls._normalize_passive_ranks(
            character.get("passive_ranks")
        )
        character["passive_cp_points"] = cls._normalize_passive_cp_points(
            character.get("passive_cp_points")
        )
        return character

    @classmethod
    def _has_meaningful_value(cls, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, dict):
            return any(cls._has_meaningful_value(v) for v in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(cls._has_meaningful_value(v) for v in value)
        return True

    @classmethod
    def _is_empty_member(cls, build: PlayerBuild) -> bool:
        return not cls._has_meaningful_value(build.to_dict())

    @classmethod
    def _normalize(cls, data: Any) -> dict[str, Any]:
        data = data if isinstance(data, dict) else {}
        return {
            "schema_version": SCHEMA_VERSION,
            "characters": [
                cls._normalize_character(character)
                for character in list(data.get("characters") or [])
            ],
            "builds": list(data.get("builds") or []),
        }

    def new_catalog(self) -> dict[str, Any]:
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
        """Create canonical records while preserving character-owned state."""
        existing = self.load()
        existing_by_character = {
            self._character_match_key(
                character.get("name"),
                character.get("gamertag"),
            ): character
            for character in existing["characters"]
            if isinstance(character, dict)
        }

        catalog = self._normalize(None)
        characters: dict[str, dict[str, Any]] = {}

        for index, member in enumerate(roster.Members):
            if self._is_empty_member(member):
                continue

            identity = self._identity(member, index)
            match_key = self._character_match_key(member.Name, member.Gamertag)
            previous = existing_by_character.get(match_key)
            previous_id = str(previous.get("character_id", "")).strip() if previous else ""
            character_id = previous_id or self._stable_id("character", identity)
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
                    "owned_skill_lines": self._normalize_owned_skill_lines(
                        previous.get("owned_skill_lines") if previous else []
                    ),
                    "passive_ranks": self._normalize_passive_ranks(
                        previous.get("passive_ranks") if previous else {}
                    ),
                    "passive_cp_points": self._normalize_passive_cp_points(
                        previous.get("passive_cp_points") if previous else {}
                    ),
                }

            legacy = member.to_dict()
            legacy["CharacterId"] = character_id
            legacy["BuildId"] = build_id
            catalog["builds"].append(
                {
                    "build_id": build_id,
                    "character_id": character_id,
                    "name": member.BuildName,
                    "legacy": legacy,
                    "payload": copy.deepcopy(legacy),
                }
            )

        catalog["characters"] = list(characters.values())
        return catalog

    def import_legacy_file(self, legacy_path: Path) -> dict[str, Any]:
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

    def get_character(self, character_id: str) -> dict[str, Any] | None:
        catalog = self.load()
        for character in catalog["characters"]:
            if character.get("character_id") == character_id:
                return copy.deepcopy(character)
        return None

    def set_owned_skill_lines(
        self,
        *,
        character_id: str,
        owned_skill_lines: list[str] | tuple[str, ...] | set[str],
    ) -> dict[str, Any] | None:
        catalog = self.load()
        for index, character in enumerate(catalog["characters"]):
            if character.get("character_id") != character_id:
                continue
            updated = copy.deepcopy(character)
            updated["owned_skill_lines"] = self._normalize_owned_skill_lines(owned_skill_lines)
            catalog["characters"][index] = updated
            self.save(catalog)
            return copy.deepcopy(updated)
        return None

    def set_passive_rank(
        self,
        *,
        character_id: str,
        passive_name: str,
        rank: int,
    ) -> dict[str, Any] | None:
        """Persist one known passive rank without touching build payloads."""
        name = " ".join(str(passive_name or "").strip().split())
        if not name:
            raise ValueError("Passive name must be non-empty")
        try:
            normalized_rank = int(rank)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid passive rank: {rank!r}") from exc
        if normalized_rank < 0:
            raise ValueError("Passive rank cannot be negative")

        catalog = self.load()
        for index, character in enumerate(catalog["characters"]):
            if character.get("character_id") != character_id:
                continue
            updated = copy.deepcopy(character)
            ranks = self._normalize_passive_ranks(updated.get("passive_ranks"))
            existing_name = next(
                (key for key in ranks if key.casefold() == name.casefold()),
                None,
            )
            if existing_name is not None:
                ranks.pop(existing_name)
            ranks[name] = normalized_rank
            updated["passive_ranks"] = ranks
            catalog["characters"][index] = updated
            self.save(catalog)
            return copy.deepcopy(updated)
        return None

    def clear_passive_rank(
        self,
        *,
        character_id: str,
        passive_name: str,
    ) -> dict[str, Any] | None:
        """Return a passive to unknown/unrecorded state."""
        name = " ".join(str(passive_name or "").strip().split()).casefold()
        if not name:
            raise ValueError("Passive name must be non-empty")
        catalog = self.load()
        for index, character in enumerate(catalog["characters"]):
            if character.get("character_id") != character_id:
                continue
            updated = copy.deepcopy(character)
            ranks = self._normalize_passive_ranks(updated.get("passive_ranks"))
            updated["passive_ranks"] = {
                stored_name: rank
                for stored_name, rank in ranks.items()
                if stored_name.casefold() != name
            }
            catalog["characters"][index] = updated
            self.save(catalog)
            return copy.deepcopy(updated)
        return None

    def get_passive_rank(self, character_id: str, passive_name: str) -> int | None:
        """Return a known passive rank; absent means unknown, not rank zero."""
        name = " ".join(str(passive_name or "").strip().split()).casefold()
        if not name:
            return None
        character = self.get_character(character_id)
        if character is None:
            return None
        for stored_name, rank in self._normalize_passive_ranks(
            character.get("passive_ranks")
        ).items():
            if stored_name.casefold() == name:
                return rank
        return None

    def get_build(self, build_id: str) -> dict[str, Any] | None:
        catalog = self.load()
        for build in catalog["builds"]:
            if build.get("build_id") == build_id:
                return copy.deepcopy(build)
        return None

    def upsert_build(
        self,
        *,
        character_id: str,
        build_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        catalog = self.load()
        name = build_name.strip() or "Default"
        build_id = self._stable_id(
            "build",
            f"{character_id}:{name.casefold()}",
        )
        record = {
            "build_id": build_id,
            "character_id": character_id,
            "name": name,
            "payload": copy.deepcopy(payload),
            "legacy": copy.deepcopy(payload),
        }
        for index, existing in enumerate(catalog["builds"]):
            if existing.get("build_id") == build_id:
                catalog["builds"][index] = record
                self.save(catalog)
                return copy.deepcopy(record)
        catalog["builds"].append(record)
        self.save(catalog)
        return copy.deepcopy(record)

    def builds_for_character(self, character_id: str) -> list[dict[str, Any]]:
        return [
            build
            for build in self.load()["builds"]
            if build.get("character_id") == character_id
        ]
