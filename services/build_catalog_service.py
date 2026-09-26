from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path
from typing import Any

from engine.config import get_data_dir, get_user_database_path
from uuid import NAMESPACE_URL, uuid5

from models.build_model import BuildRoster, PlayerBuild
from services.user_build_catalog_pydantic_schema import (
    ValidationError as CatalogValidationError,
    validate_user_build_catalog_payload,
)

SCHEMA_VERSION = 4


class BuildCatalogService:
    """Persist player -> character -> build ownership as canonical user state.

    ``eso.db`` remains read-only ESO reference data. User-owned identity and
    build state live here. ``PlayerBuild`` / ``BuildRoster`` are compatibility
    snapshots for existing consumers, not the identity authority.

    Schema v4 adds explicit player records and build-level team assignments.
    Older character/build catalogs are upgraded deterministically in memory and
    written back only when a normal catalog save occurs.
    """

    def __init__(self, catalog_path: Path):
        requested_path = Path(catalog_path)
        try:
            is_application_catalog = (
                requested_path.resolve()
                == (get_data_dir() / "characters.json").resolve()
            )
        except OSError:
            is_application_catalog = requested_path == (get_data_dir() / "characters.json")

        if is_application_catalog:
            from services.user_data_migration_service import migrate_legacy_user_data

            migrate_legacy_user_data()
            self.catalog_path = get_user_database_path()
        else:
            self.catalog_path = requested_path

        self._database_mode = self.catalog_path.suffix.casefold() in {".db", ".sqlite", ".sqlite3"}
        if self._database_mode:
            self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.catalog_path) as db:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS build_catalog (
                        singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                        payload_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

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
    def _player_match_key(gamertag: object) -> str:
        return str(gamertag or "").strip().casefold()

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
    def _normalize_player(cls, value: Any) -> dict[str, Any]:
        player = copy.deepcopy(value) if isinstance(value, dict) else {}
        player["player_id"] = str(player.get("player_id") or "").strip()
        player["gamertag"] = str(player.get("gamertag") or "").strip()
        player["display_name"] = str(player.get("display_name") or "").strip()
        player["notes"] = str(player.get("notes") or "").strip()
        player["status"] = str(player.get("status") or "Active").strip() or "Active"
        player["avatar_path"] = str(player.get("avatar_path") or "").strip()
        player["discord_avatar_url"] = str(player.get("discord_avatar_url") or "").strip()
        return player

    @classmethod
    def _normalize_assignment(cls, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        build_id = str(value.get("build_id") or "").strip()
        team_name = str(value.get("team_name") or value.get("team") or "").strip()
        if not build_id or not team_name:
            return None
        assignment_id = str(value.get("assignment_id") or "").strip() or cls._stable_id(
            "team-assignment", f"{team_name.casefold()}:{build_id}"
        )
        return {
            "assignment_id": assignment_id,
            "team_name": team_name,
            "build_id": build_id,
            "raid_role": str(value.get("raid_role") or "").strip(),
            "slot_name": str(value.get("slot_name") or "").strip(),
            "status": str(value.get("status") or "Active").strip() or "Active",
            "notes": str(value.get("notes") or "").strip(),
        }

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
        raw_players = [
            cls._normalize_player(player)
            for player in list(data.get("players") or [])
            if isinstance(player, dict)
        ]
        players_by_id = {
            player["player_id"]: player
            for player in raw_players
            if player.get("player_id")
        }
        players_by_gamertag = {
            cls._player_match_key(player.get("gamertag")): player
            for player in raw_players
            if cls._player_match_key(player.get("gamertag"))
        }

        characters: list[dict[str, Any]] = []
        for raw_character in list(data.get("characters") or []):
            if not isinstance(raw_character, dict):
                continue
            character = cls._normalize_character(raw_character)
            character_id = str(character.get("character_id") or "").strip()
            gamertag = str(character.get("gamertag") or "").strip()
            player_id = str(character.get("player_id") or "").strip()

            player = players_by_id.get(player_id) if player_id else None
            if player is None and gamertag:
                player = players_by_gamertag.get(cls._player_match_key(gamertag))
            if player is None:
                player_seed = gamertag.casefold() or character_id or str(character.get("name") or "unknown")
                player_id = cls._stable_id("player", player_seed)
                player = cls._normalize_player(
                    {
                        "player_id": player_id,
                        "gamertag": gamertag,
                        "status": "Active",
                    }
                )
                players_by_id[player_id] = player
                if gamertag:
                    players_by_gamertag[cls._player_match_key(gamertag)] = player
            else:
                player_id = str(player.get("player_id") or "").strip()

            character["player_id"] = player_id
            # Retain the historical mirror for compatibility readers. Player is
            # authoritative for Gamertag from schema v4 onward.
            if not gamertag:
                character["gamertag"] = str(player.get("gamertag") or "")
            characters.append(character)

        assignments = []
        seen_assignment_ids: set[str] = set()
        for raw_assignment in list(data.get("team_assignments") or []):
            assignment = cls._normalize_assignment(raw_assignment)
            if assignment is None or assignment["assignment_id"] in seen_assignment_ids:
                continue
            seen_assignment_ids.add(assignment["assignment_id"])
            assignments.append(assignment)

        return {
            "schema_version": SCHEMA_VERSION,
            "players": list(players_by_id.values()),
            "characters": characters,
            "builds": list(data.get("builds") or []),
            "team_assignments": assignments,
        }

    @classmethod
    def _validated_catalog(cls, data: Any) -> dict[str, Any]:
        normalized = cls._normalize(data)
        try:
            return validate_user_build_catalog_payload(normalized)
        except CatalogValidationError as exc:
            raise ValueError(f"canonical Build catalog failed Pydantic validation: {exc}") from exc

    def new_catalog(self) -> dict[str, Any]:
        return self._validated_catalog(None)

    def load_strict(self) -> dict[str, Any]:
        if self._database_mode:
            with sqlite3.connect(self.catalog_path) as db:
                row = db.execute(
                    "SELECT payload_json FROM build_catalog WHERE singleton_id = 1"
                ).fetchone()
            if row is None:
                return self._validated_catalog(None)
            payload = json.loads(str(row[0] or ""))
            return self._validated_catalog(payload)

        if not self.catalog_path.exists():
            return self._validated_catalog(None)
        payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return self._validated_catalog(payload)

    def load(self) -> dict[str, Any]:
        try:
            return self.load_strict()
        except (OSError, sqlite3.Error, json.JSONDecodeError):
            return self._normalize(None)

    def delete_build(self, build_id: str) -> bool:
        """Delete exactly one canonical Build by stable id.

        Absence from a UI projection is never deletion authority. Callers must name
        the Build explicitly; Players, Characters, progression, and unrelated Builds
        are preserved.
        """
        wanted = str(build_id or "").strip()
        if not wanted:
            raise ValueError("build_id is required")
        catalog = self.load_strict()
        builds = [
            row for row in catalog.get("builds", [])
            if isinstance(row, dict)
        ]
        kept = [
            row for row in builds
            if str(row.get("build_id") or "").strip() != wanted
        ]
        if len(kept) == len(builds):
            return False
        catalog["builds"] = kept
        self.save(catalog)
        verified = self.load_strict()
        if any(
            str(row.get("build_id") or "").strip() == wanted
            for row in verified.get("builds", [])
            if isinstance(row, dict)
        ):
            raise RuntimeError(f"Build deletion readback failed for {wanted!r}")
        return True

    def save(self, catalog: dict[str, Any]) -> None:
        normalized = self._validated_catalog(catalog)
        if self._database_mode:
            payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
            with sqlite3.connect(self.catalog_path) as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(
                    """
                    INSERT INTO build_catalog(singleton_id, payload_json, updated_at)
                    VALUES (1, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(singleton_id) DO UPDATE SET
                        payload_json=excluded.payload_json,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (payload,),
                )
                row = db.execute(
                    "SELECT payload_json FROM build_catalog WHERE singleton_id = 1"
                ).fetchone()
                if row is None:
                    raise RuntimeError("canonical Build catalog could not be read back after save")
                persisted = self._validated_catalog(json.loads(str(row[0] or "")))
                if persisted != normalized:
                    raise RuntimeError("canonical Build catalog did not round-trip exactly")
            return

        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.catalog_path.with_suffix(self.catalog_path.suffix + ".tmp")
        temp.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.catalog_path)

    def import_legacy_roster(self, roster: BuildRoster) -> dict[str, Any]:
        """Create canonical ownership records while preserving character state."""
        # This method can feed a later write. Never turn a corrupt/transient
        # canonical read into an empty catalog that a caller could save over
        # valid user data.
        existing = self.load_strict()
        existing_players_by_tag = {
            self._player_match_key(player.get("gamertag")): player
            for player in existing["players"]
            if isinstance(player, dict) and self._player_match_key(player.get("gamertag"))
        }
        existing_characters_by_id = {
            str(character.get("character_id") or "").strip(): character
            for character in existing["characters"]
            if isinstance(character, dict) and str(character.get("character_id") or "").strip()
        }
        existing_builds_by_id = {
            str(build.get("build_id") or "").strip(): build
            for build in existing["builds"]
            if isinstance(build, dict) and str(build.get("build_id") or "").strip()
        }
        existing_by_character = {
            self._character_match_key(
                character.get("name"),
                character.get("gamertag"),
            ): character
            for character in existing["characters"]
            if isinstance(character, dict)
        }

        catalog = self.new_catalog()
        players: dict[str, dict[str, Any]] = {
            str(player.get("player_id")): copy.deepcopy(player)
            for player in existing["players"]
            if isinstance(player, dict) and str(player.get("player_id") or "").strip()
        }
        characters: dict[str, dict[str, Any]] = {}

        for index, member in enumerate(roster.Members):
            if self._is_empty_member(member):
                continue

            identity = self._identity(member, index)
            gamertag = member.Gamertag.strip()
            tag_key = self._player_match_key(gamertag)
            explicit_player_id = str(getattr(member, "PlayerId", "") or "").strip()
            previous_player = (
                players.get(explicit_player_id)
                if explicit_player_id
                else existing_players_by_tag.get(tag_key) if tag_key else None
            )
            player_id = (
                explicit_player_id
                if explicit_player_id and explicit_player_id in players
                else str(previous_player.get("player_id") or "").strip()
                if previous_player
                else self._stable_id("player", tag_key or identity)
            )
            if player_id not in players:
                players[player_id] = self._normalize_player(
                    {
                        "player_id": player_id,
                        "gamertag": gamertag,
                        "status": "Active",
                    }
                )
            elif gamertag:
                players[player_id]["gamertag"] = gamertag

            match_key = self._character_match_key(member.Name, member.Gamertag)
            explicit_character_id = str(
                getattr(member, "CharacterId", "") or ""
            ).strip()
            previous = (
                existing_characters_by_id.get(explicit_character_id)
                if explicit_character_id
                else existing_by_character.get(match_key)
            )
            previous_id = str(previous.get("character_id", "")).strip() if previous else ""
            # An explicit destination CharacterId is authoritative for a new
            # PlayerBuild too. Requiring it to pre-exist in this catalog silently
            # remaps a legitimate Copy Build destination to a generated ID.
            character_id = (
                explicit_character_id
                if explicit_character_id
                else previous_id or self._stable_id("character", identity)
            )
            explicit_build_id = str(getattr(member, "BuildId", "") or "").strip()
            build_id = (
                explicit_build_id
                if explicit_build_id
                else self._stable_id(
                    "build",
                    f"{character_id}:{member.BuildName.strip().casefold() or index}",
                )
            )

            if character_id not in characters:
                characters[character_id] = {
                    "character_id": character_id,
                    "player_id": player_id,
                    "name": member.Name,
                    "gamertag": gamertag,
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

            # Preserve the compatibility snapshot exactly as the caller supplied it.
            # Canonical identity lives on the catalog records above; generated IDs
            # must not leak back into PlayerBuild merely because it was saved once.
            legacy = member.to_dict()
            payload = copy.deepcopy(legacy)
            payload["PlayerId"] = player_id
            payload["CharacterId"] = character_id
            payload["BuildId"] = build_id
            previous_build = existing_builds_by_id.get(build_id, {})
            build_kind = str(
                getattr(member, "BuildKind", "")
                or previous_build.get("build_kind")
                or "saved"
            ).strip().casefold() or "saved"
            source = copy.deepcopy(previous_build.get("source"))
            if not isinstance(source, dict):
                source = {}
            if str(getattr(member, "SourcePlanId", "") or "").strip():
                source["plan_id"] = str(member.SourcePlanId).strip()
            if str(getattr(member, "SourcePlanName", "") or "").strip():
                source["plan_name"] = str(member.SourcePlanName).strip()
            if str(getattr(member, "SourceSeatId", "") or "").strip():
                source["seat_id"] = str(member.SourceSeatId).strip()
            if build_kind == "comp":
                source.setdefault("kind", "comp_maker")

            record = {
                "build_id": build_id,
                "character_id": character_id,
                "name": member.BuildName,
                "legacy": legacy,
                "payload": payload,
            }
            if build_kind != "saved":
                record["build_kind"] = build_kind
            if source:
                record["source"] = source
            catalog["builds"].append(record)

        # Characters may exist before they have a build. Preserve those records
        # and the player relationship instead of deleting them during a legacy
        # compatibility resync.
        for character_id, character in existing_characters_by_id.items():
            if character_id not in characters:
                characters[character_id] = copy.deepcopy(character)

        catalog["players"] = list(players.values())
        catalog["characters"] = list(characters.values())
        build_ids = {
            str(build.get("build_id") or "").strip()
            for build in catalog["builds"]
            if isinstance(build, dict)
        }
        catalog["team_assignments"] = [
            copy.deepcopy(assignment)
            for assignment in existing.get("team_assignments", [])
            if isinstance(assignment, dict)
            and str(assignment.get("build_id") or "").strip() in build_ids
        ]
        return catalog

    def import_legacy_file(self, legacy_path: Path) -> dict[str, Any]:
        payload = json.loads(Path(legacy_path).read_text(encoding="utf-8"))
        members = [
            PlayerBuild.from_dict(member)
            for member in (payload or {}).get("Members", [])
            if isinstance(member, dict)
        ]
        return self.import_legacy_roster(BuildRoster(Members=members))

    def migrate_if_needed(self, legacy_path: Path) -> dict[str, Any]:
        current = self.load()
        if current["characters"] or current["builds"] or not Path(legacy_path).exists():
            return current
        migrated = self.import_legacy_file(legacy_path)
        self.save(migrated)
        return migrated

    def list_players(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(player) for player in self.load()["players"]]

    def get_player(self, player_id: str) -> dict[str, Any] | None:
        for player in self.load()["players"]:
            if player.get("player_id") == player_id:
                return copy.deepcopy(player)
        return None

    def set_player_avatar(
        self,
        *,
        player_id: str,
        avatar_path: str,
    ) -> dict[str, Any] | None:
        """Persist one player-owned avatar reference without touching eso.db."""
        normalized_path = str(avatar_path or "").strip()
        catalog = self.load()
        for index, player in enumerate(catalog["players"]):
            if player.get("player_id") != player_id:
                continue
            updated = copy.deepcopy(player)
            updated["avatar_path"] = normalized_path
            catalog["players"][index] = updated
            self.save(catalog)
            return copy.deepcopy(updated)
        return None

    def set_player_discord_avatar(
        self,
        *,
        player_id: str,
        avatar_url: str,
        avatar_path: str,
    ) -> dict[str, Any] | None:
        """Persist the current Discord avatar source and its local cached portrait."""
        normalized_url = str(avatar_url or "").strip()
        normalized_path = str(avatar_path or "").strip()
        catalog = self.load()
        for index, player in enumerate(catalog["players"]):
            if player.get("player_id") != player_id:
                continue
            updated = copy.deepcopy(player)
            updated["discord_avatar_url"] = normalized_url
            if normalized_path:
                updated["avatar_path"] = normalized_path
            catalog["players"][index] = updated
            self.save(catalog)
            return copy.deepcopy(updated)
        return None

    def characters_for_player(self, player_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(character)
            for character in self.load()["characters"]
            if character.get("player_id") == player_id
        ]

    def player_for_character(self, character_id: str) -> dict[str, Any] | None:
        character = self.get_character(character_id)
        if character is None:
            return None
        return self.get_player(str(character.get("player_id") or ""))

    def get_character(self, character_id: str) -> dict[str, Any] | None:
        catalog = self.load()
        for character in catalog["characters"]:
            if character.get("character_id") == character_id:
                return copy.deepcopy(character)
        return None

    def set_character_avatar(
        self,
        *,
        character_id: str,
        avatar_path: str,
    ) -> dict[str, Any] | None:
        """Persist one character-owned avatar reference without touching eso.db."""
        normalized_path = str(avatar_path or "").strip()
        catalog = self.load()
        for index, character in enumerate(catalog["characters"]):
            if character.get("character_id") != character_id:
                continue
            updated = copy.deepcopy(character)
            updated["avatar_path"] = normalized_path
            catalog["characters"][index] = updated
            self.save(catalog)
            return copy.deepcopy(updated)
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
            copy.deepcopy(build)
            for build in self.load()["builds"]
            if build.get("character_id") == character_id
        ]

    def assign_build_to_team(
        self,
        *,
        build_id: str,
        team_name: str,
        raid_role: str = "",
        slot_name: str = "",
        status: str = "Active",
        notes: str = "",
    ) -> dict[str, Any]:
        build_id = str(build_id or "").strip()
        team_name = str(team_name or "").strip()
        if not build_id:
            raise ValueError("build_id is required")
        if not team_name:
            raise ValueError("team_name is required")
        if self.get_build(build_id) is None:
            raise ValueError(f"Unknown canonical build: {build_id}")

        catalog = self.load()
        assignment = self._normalize_assignment(
            {
                "team_name": team_name,
                "build_id": build_id,
                "raid_role": raid_role,
                "slot_name": slot_name,
                "status": status,
                "notes": notes,
            }
        )
        assert assignment is not None
        for index, existing in enumerate(catalog["team_assignments"]):
            if existing.get("assignment_id") == assignment["assignment_id"]:
                catalog["team_assignments"][index] = assignment
                self.save(catalog)
                return copy.deepcopy(assignment)
        catalog["team_assignments"].append(assignment)
        self.save(catalog)
        return copy.deepcopy(assignment)

    def unassign_build_from_team(self, *, build_id: str, team_name: str) -> bool:
        build_id = str(build_id or "").strip()
        team_name = str(team_name or "").strip().casefold()
        catalog = self.load()
        kept = [
            assignment
            for assignment in catalog["team_assignments"]
            if not (
                str(assignment.get("build_id") or "").strip() == build_id
                and str(assignment.get("team_name") or "").strip().casefold() == team_name
            )
        ]
        changed = len(kept) != len(catalog["team_assignments"])
        if changed:
            catalog["team_assignments"] = kept
            self.save(catalog)
        return changed

    def assignments_for_build(self, build_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(assignment)
            for assignment in self.load()["team_assignments"]
            if assignment.get("build_id") == build_id
        ]

    def assignments_for_team(self, team_name: str) -> list[dict[str, Any]]:
        wanted = str(team_name or "").strip().casefold()
        return [
            copy.deepcopy(assignment)
            for assignment in self.load()["team_assignments"]
            if str(assignment.get("team_name") or "").strip().casefold() == wanted
        ]
