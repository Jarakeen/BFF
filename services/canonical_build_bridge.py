from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.build_model import BuildRoster, PlayerBuild
from services.build_catalog_service import BuildCatalogService


class CanonicalBuildBridge:
    """Bridge the existing Builds UI model onto the canonical catalog.

    The UI still works with BuildRoster/PlayerBuild for now. The canonical
    character/build catalog is the source of truth; builds.json remains a
    compatibility mirror so existing exports and older tooling continue to
    work during Phase 1.
    """

    def __init__(self, legacy_path: Path, catalog_path: Path | None = None):
        self.legacy_path = Path(legacy_path)
        self.catalog_path = catalog_path or self.legacy_path.with_name("characters.json")
        self.catalog_service = BuildCatalogService(self.catalog_path)

    def load(self) -> BuildRoster:
        catalog = self.catalog_service.load()
        if catalog["builds"]:
            canonical_roster = self._roster_from_catalog(catalog)
            if canonical_roster.Members:
                return canonical_roster

            # Historical/placeholder canonical build rows must not shadow a
            # populated compatibility mirror. Recover the real legacy roster
            # and immediately resync it so the catalog becomes authoritative
            # again on the same load.
            roster = self._load_legacy()
            if roster.Members:
                self.sync_from_roster(roster)
                return roster
            return canonical_roster

        roster = self._load_legacy()
        if roster.Members:
            self.sync_from_roster(roster)
        return roster

    def save(self, roster: BuildRoster) -> None:
        self._save_legacy(roster)
        self.sync_from_roster(roster)

    def sync_from_roster(self, roster: BuildRoster) -> dict[str, Any]:
        catalog = self.catalog_service.import_legacy_roster(roster)
        self.catalog_service.save(catalog)
        return catalog

    def _load_legacy(self) -> BuildRoster:
        if not self.legacy_path.exists():
            return BuildRoster()
        try:
            data = json.loads(self.legacy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return BuildRoster()
        return BuildRoster.from_dict(data)

    def _save_legacy(self, roster: BuildRoster) -> None:
        self.legacy_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_path.write_text(
            json.dumps(roster.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
        """Reject placeholder/empty legacy rows before reconstructing them."""
        return isinstance(legacy, dict) and cls._has_meaningful_legacy_data(legacy)

    @classmethod
    def _roster_from_catalog(cls, catalog: dict[str, Any]) -> BuildRoster:
        members: list[PlayerBuild] = []
        for entry in catalog.get("builds", []):
            if not isinstance(entry, dict):
                continue
            legacy = entry.get("legacy")
            if not cls._is_valid_legacy_build(legacy):
                continue
            # The canonical catalog can contain historical placeholder builds;
            # only reconstruct real legacy rows into the compatibility roster.
            members.append(PlayerBuild.from_dict(legacy))
        return BuildRoster(Members=members)
