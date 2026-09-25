from __future__ import annotations

"""Surgically restore missing reusable Saved Builds from a FoundryDock snapshot.

Preview-only by default. --apply creates a full safety snapshot of the current
user database, then merges only reusable Saved Build records and the exact
Player/Character records those Builds depend on. Raid Plans, revisions, Teams,
Personnel, assignments, and unrelated current catalog records are preserved.
"""

import argparse
import copy
import json
import sqlite3
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.config import get_user_database_path
from services.build_catalog_service import BuildCatalogService
from services.user_safety_snapshot_service import UserSafetySnapshotService


def _load_catalog(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT payload_json FROM build_catalog WHERE singleton_id = 1"
        ).fetchone()
    if row is None:
        raise RuntimeError(f"No canonical build_catalog found in {path}")
    payload = json.loads(str(row[0]))
    return BuildCatalogService._normalize(payload)


def _key(value: object) -> str:
    return str(value or "").strip().casefold()


def _is_saved(build: dict) -> bool:
    return _key(build.get("build_kind") or "saved") != "comp"


def _dependencies(catalog: dict, builds: list[dict]) -> tuple[list[dict], list[dict]]:
    character_ids = {_key(build.get("character_id")) for build in builds}
    characters = [
        copy.deepcopy(row)
        for row in catalog.get("characters", [])
        if _key(row.get("character_id")) in character_ids
    ]
    player_ids = {_key(row.get("player_id")) for row in characters}
    players = [
        copy.deepcopy(row)
        for row in catalog.get("players", [])
        if _key(row.get("player_id")) in player_ids
    ]
    return players, characters


def plan_restore(current: dict, source: dict) -> dict:
    current_build_ids = {_key(row.get("build_id")) for row in current.get("builds", [])}
    source_saved = [
        copy.deepcopy(row)
        for row in source.get("builds", [])
        if _is_saved(row) and _key(row.get("build_id")) not in current_build_ids
    ]
    players, characters = _dependencies(source, source_saved)

    current_player_ids = {_key(row.get("player_id")) for row in current.get("players", [])}
    current_character_ids = {_key(row.get("character_id")) for row in current.get("characters", [])}
    add_players = [row for row in players if _key(row.get("player_id")) not in current_player_ids]
    add_characters = [
        row for row in characters if _key(row.get("character_id")) not in current_character_ids
    ]
    return {
        "builds": source_saved,
        "characters": add_characters,
        "players": add_players,
    }


def apply_restore(database: Path, source: Path, restore: dict) -> Path:
    snapshot = UserSafetySnapshotService(database_path=database).create(
        "before-saved-build-recovery"
    )
    if snapshot is None:
        raise RuntimeError("Could not create pre-recovery safety snapshot.")

    current = _load_catalog(database)
    merged = copy.deepcopy(current)
    merged["players"].extend(copy.deepcopy(restore["players"]))
    merged["characters"].extend(copy.deepcopy(restore["characters"]))
    merged["builds"].extend(copy.deepcopy(restore["builds"]))

    service = BuildCatalogService(database)
    service.save(merged)
    verified = service.load_strict()
    expected_ids = {_key(row.get("build_id")) for row in restore["builds"]}
    actual_ids = {_key(row.get("build_id")) for row in verified.get("builds", [])}
    missing = expected_ids - actual_ids
    if missing:
        raise RuntimeError(
            "Saved Build recovery failed read-back verification: "
            + ", ".join(sorted(missing))
        )
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover missing Saved Builds from a safety snapshot.")
    parser.add_argument("source", type=Path, help="Known-good foundrydock.db safety snapshot")
    parser.add_argument("--database", type=Path, default=get_user_database_path())
    parser.add_argument("--apply", action="store_true", help="Apply after previewing; default is read-only")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    database = args.database.expanduser().resolve()
    if source == database:
        raise SystemExit("Source snapshot and live database must be different files.")

    current = _load_catalog(database)
    recovery = _load_catalog(source)
    restore = plan_restore(current, recovery)

    print(f"Live database: {database}")
    print(f"Recovery source: {source}")
    print(f"Missing reusable Saved Builds: {len(restore['builds'])}")
    for build in restore["builds"]:
        payload = build.get("payload") if isinstance(build.get("payload"), dict) else {}
        legacy = build.get("legacy") if isinstance(build.get("legacy"), dict) else {}
        detail = payload or legacy
        print(
            "  + "
            + str(build.get("name") or detail.get("BuildName") or build.get("build_id"))
            + " | "
            + str(detail.get("Gamertag") or "")
            + " | "
            + str(detail.get("Name") or "")
        )
    print(f"Required missing Characters: {len(restore['characters'])}")
    print(f"Required missing Players: {len(restore['players'])}")

    if not args.apply:
        print("PREVIEW ONLY. No data changed.")
        return 0

    snapshot = apply_restore(database, source, restore)
    print(f"Applied recovery. Pre-write safety snapshot: {snapshot}")
    print(f"Verified {len(restore['builds'])} recovered Saved Build(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
