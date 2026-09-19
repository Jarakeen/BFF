from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from models.build_model import BuildRoster, PlayerBuild
from services.build_catalog_service import BuildCatalogService
from services.build_gear_enchantment_compatibility_service import (
    BuildGearEnchantmentCompatibilityService,
)


class CanonicalBuildBridge:
    """Bridge the existing Builds UI model onto the canonical catalog.

    The UI still works with BuildRoster/PlayerBuild for now. The canonical
    character/build catalog is the source of truth; builds.json remains a
    compatibility mirror so existing exports and older tooling continue to
    work during Phase 1.
    """

    _LEGACY_IDENTITY_FIELDS = frozenset(
        {
            "Name",
            "Gamertag",
            "BuildName",
            "Race",
            "EsoClass",
            "Role",
            "Alliance",
            "CharacterId",
            "BuildId",
        }
    )

    def __init__(self, legacy_path: Path, catalog_path: Path | None = None):
        self.legacy_path = Path(legacy_path)
        self.catalog_path = catalog_path or self.legacy_path.with_name("characters.json")
        self.catalog_service = BuildCatalogService(self.catalog_path)
        self.enchantment_compatibility = BuildGearEnchantmentCompatibilityService()

    def _load_catalog_strict(self) -> dict[str, Any]:
        """Read canonical user state without converting corruption into emptiness."""
        if not self.catalog_path.exists():
            return self.catalog_service.new_catalog()
        payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return self.catalog_service._normalize(payload)

    def load(self) -> BuildRoster:
        catalog = self._load_catalog_strict()
        if catalog["builds"]:
            canonical_roster = self.enchantment_compatibility.normalize_roster(
                self._roster_from_catalog(catalog)
            )
            if canonical_roster.Members:
                return canonical_roster

            # Historical/placeholder canonical build rows must not shadow a
            # populated compatibility mirror. Recover the real legacy roster
            # and immediately resync it so the catalog becomes authoritative
            # again on the same load.
            roster = self.enchantment_compatibility.normalize_roster(self._load_legacy())
            if roster.Members:
                self.sync_from_roster(roster)
                return roster
            return canonical_roster

        roster = self.enchantment_compatibility.normalize_roster(self._load_legacy())
        if roster.Members:
            self.sync_from_roster(roster)
        return roster

    def save(self, roster: BuildRoster) -> None:
        """Persist canonical state first, then refresh the compatibility mirror.

        ``characters.json`` is authoritative. A compatibility-mirror failure must
        therefore never prevent an already-valid canonical save from remaining the
        source of truth.
        """
        normalized = self.enchantment_compatibility.normalize_roster(roster)
        self.sync_from_roster(normalized)
        self._save_legacy(normalized)

    def sync_from_roster(self, roster: BuildRoster) -> dict[str, Any]:
        """Resync builds without deleting canonical characters that have none.

        Character identity and progression are independent of build ownership.
        Rebuilding the compatibility roster must therefore be allowed to remove
        every build for a character while preserving that character record.
        """
        normalized = self.enchantment_compatibility.normalize_roster(roster)
        existing = self._load_catalog_strict()
        # import_legacy_roster performs its own normal load after the strict gate
        # above. The gate prevents corrupt canonical state from being silently
        # replaced by compatibility data.
        catalog = self.catalog_service.import_legacy_roster(normalized)

        represented_ids = {
            str(character.get("character_id", "")).strip()
            for character in catalog.get("characters", [])
            if isinstance(character, dict)
        }
        for character in existing.get("characters", []):
            if not isinstance(character, dict):
                continue
            character_id = str(character.get("character_id", "")).strip()
            if not character_id or character_id in represented_ids:
                continue
            catalog["characters"].append(character)
            represented_ids.add(character_id)

        self.catalog_service.save(catalog)
        return catalog

    def _load_legacy(self) -> BuildRoster:
        if not self.legacy_path.exists():
            return BuildRoster()
        data = json.loads(self.legacy_path.read_text(encoding="utf-8"))
        return BuildRoster.from_dict(data)

    def _save_legacy(self, roster: BuildRoster) -> None:
        """Atomically refresh builds.json as a verified compatibility mirror."""
        path = self.legacy_path
        path.parent.mkdir(parents=True, exist_ok=True)
        expected = roster.to_dict()
        payload = json.dumps(expected, ensure_ascii=False, indent=2)

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temp_path.replace(path)
            written = json.loads(path.read_text(encoding="utf-8"))
            if written != expected:
                raise IOError(f"Build compatibility mirror verification failed for {path.resolve()}")
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def _has_meaningful_legacy_data(value: Any) -> bool:
        """Return True when a legacy value contains real user data.

        Numeric zero is a default/empty value. Attribute allocations and other
        counters are stored as zero when the character has not been configured.
        """
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, dict):
            return any(CanonicalBuildBridge._has_meaningful_legacy_data(v) for v in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(CanonicalBuildBridge._has_meaningful_legacy_data(v) for v in value)
        return True

    @classmethod
    def _is_valid_legacy_build(cls, legacy: Any) -> bool:
        """Reject identity-only placeholder rows before reconstructing them.

        Character/build identity belongs in the canonical record itself and
        does not prove that the embedded compatibility payload contains any
        actual build selections. A legacy snapshot becomes authoritative only
        when it contains meaningful non-identity state such as attributes,
        gear, bars, mundus, consumables, or Champion Points.
        """
        if not isinstance(legacy, dict):
            return False
        build_state = {
            key: value
            for key, value in legacy.items()
            if key not in cls._LEGACY_IDENTITY_FIELDS
        }
        return cls._has_meaningful_legacy_data(build_state)

    @classmethod
    def _roster_from_catalog(cls, catalog: dict[str, Any]) -> BuildRoster:
        members: list[PlayerBuild] = []
        characters_by_id = {
            str(character.get("character_id") or "").strip(): character
            for character in catalog.get("characters", [])
            if isinstance(character, dict)
            and str(character.get("character_id") or "").strip()
        }
        for entry in catalog.get("builds", []):
            if not isinstance(entry, dict):
                continue
            legacy = entry.get("legacy")
            if not cls._is_valid_legacy_build(legacy):
                continue
            # The canonical catalog can contain historical placeholder builds;
            # only reconstruct real legacy rows into the compatibility roster.
            build = PlayerBuild.from_dict(legacy)
            character_id = str(entry.get("character_id") or build.CharacterId or "").strip()
            character = characters_by_id.get(character_id, {})
            build.PlayerId = str(
                character.get("player_id")
                or getattr(build, "PlayerId", "")
                or ""
            ).strip()
            build.CharacterId = character_id
            build.BuildId = str(entry.get("build_id") or build.BuildId or "").strip()
            members.append(build)
        return BuildRoster(Members=members)
