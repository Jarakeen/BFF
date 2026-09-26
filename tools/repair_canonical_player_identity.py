from __future__ import annotations

"""Repair two canonical Build Catalog Player identities without merging Personnel rows."""

import argparse
import copy
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_user_database_path
from services.build_catalog_service import BuildCatalogService
from services.user_build_catalog_pydantic_schema import validate_user_build_catalog_payload


def _key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _player_label(row: dict) -> str:
    return str(row.get("gamertag") or row.get("display_name") or "").strip()


def _exact_player(catalog: dict, label: str) -> dict:
    target = _key(label)
    matches = [
        row
        for row in catalog["players"]
        if target in {_key(row.get("gamertag")), _key(row.get("display_name"))}
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one canonical Player matching {label!r}; found {len(matches)}."
        )
    return matches[0]


def _describe(catalog: dict, player: dict) -> list[str]:
    player_id = str(player["player_id"])
    characters = [
        row for row in catalog["characters"]
        if str(row.get("player_id") or "") == player_id
    ]
    lines = [f"PLAYER {player_id} | {_player_label(player)}"]
    for character in characters:
        character_id = str(character["character_id"])
        lines.append(f"  CHARACTER {character_id} | {character.get('name') or ''}")
        for build in catalog["builds"]:
            if str(build.get("character_id") or "") == character_id:
                lines.append(f"    BUILD {build.get('build_id')} | {build.get('name') or ''}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--survivor", required=True)
    parser.add_argument("--donor", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    path = get_user_database_path()
    service = BuildCatalogService(path)
    catalog = service.load_strict()
    survivor = _exact_player(catalog, args.survivor)
    donor = _exact_player(catalog, args.donor)
    if survivor["player_id"] == donor["player_id"]:
        raise RuntimeError("Survivor and donor already resolve to the same canonical Player.")

    print(f"DB: {path}")
    print("SURVIVOR")
    print("\n".join(_describe(catalog, survivor)))
    print("DONOR")
    print("\n".join(_describe(catalog, donor)))
    print(f"Build count before: {len(catalog['builds'])}")

    if not args.apply:
        print("DRY RUN ONLY: no data changed.")
        return 0

    revised = copy.deepcopy(catalog)
    survivor_id = str(survivor["player_id"])
    donor_id = str(donor["player_id"])
    for character in revised["characters"]:
        if str(character.get("player_id") or "") == donor_id:
            character["player_id"] = survivor_id
            # Keep the character's own name; align only its player/gamertag projection.
            if "gamertag" in character:
                character["gamertag"] = _player_label(survivor)
    revised["players"] = [
        row for row in revised["players"]
        if str(row.get("player_id") or "") != donor_id
    ]
    revised = validate_user_build_catalog_payload(revised)
    if len(revised["builds"]) != len(catalog["builds"]):
        raise RuntimeError("Canonical repair would change Saved Build count.")

    backup = path.with_name(path.name + ".before-canonical-player-repair")
    if not backup.exists():
        source = sqlite3.connect(path)
        target = sqlite3.connect(backup)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        try:
            service.save_on_connection(revised, db)
            db.execute(
                """
                UPDATE roster_member
                SET canonical_player_id = ?
                WHERE canonical_player_id = ?
                """,
                (survivor_id, donor_id),
            )
            stale = db.execute(
                "SELECT COUNT(*) AS n FROM roster_member WHERE canonical_player_id = ?",
                (donor_id,),
            ).fetchone()
            if int(stale["n"]) != 0:
                raise RuntimeError("Personnel still references donor canonical Player after repair.")
            db.commit()
        except Exception:
            db.rollback()
            raise

    read_back = service.load_strict()
    if len(read_back["builds"]) != len(catalog["builds"]):
        raise RuntimeError("Post-repair Saved Build count changed.")
    if any(str(row.get("player_id") or "") == donor_id for row in read_back["characters"]):
        raise RuntimeError("Post-repair character still references donor canonical Player.")
    if any(str(row.get("player_id") or "") == donor_id for row in read_back["players"]):
        raise RuntimeError("Post-repair donor canonical Player still exists.")

    print(f"Backup: {backup}")
    print(f"Build count after: {len(read_back['builds'])}")
    print("CANONICAL PLAYER REPAIR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
