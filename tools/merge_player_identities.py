from __future__ import annotations

"""Safely merge two exact Personnel player identities in production user data."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import get_data_dir, get_user_database_path
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService


def _exact_member(roster: RosterService, name: str):
    target = " ".join(str(name or "").strip().split()).casefold()
    matches = [
        member
        for member in roster.list_members()
        if " ".join(str(member.PlayerName or "").strip().split()).casefold() == target
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one Personnel record named {name!r}; found {len(matches)}."
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--survivor", required=True, help="Exact Player name to keep.")
    parser.add_argument("--donor", required=True, help="Exact duplicate Player name to absorb.")
    parser.add_argument("--apply", action="store_true", help="Actually perform the atomic merge.")
    args = parser.parse_args()

    database_path = get_user_database_path()
    database = EsoDatabase(database_path)
    roster = RosterService(database)
    builds = BuildService(get_data_dir() / "builds.json")
    service = RosterPlayerIdentityService(database, builds)

    survivor = _exact_member(roster, args.survivor)
    donor = _exact_member(roster, args.donor)
    print(f"DB: {database_path}")
    print(f"SURVIVOR: id={survivor.Id} | {survivor.PlayerName} | {survivor.CharacterName}")
    print(f"DONOR:    id={donor.Id} | {donor.PlayerName} | {donor.CharacterName}")

    if not args.apply:
        print("DRY RUN ONLY: no data changed. Re-run with --apply to merge.")
        return 0

    result = service.merge_players(
        survivor_id=int(survivor.Id),
        donor_id=int(donor.Id),
        source="explicit_cli_merge",
        notes=f"Explicit duplicate identity merge: {donor.PlayerName} -> {survivor.PlayerName}",
        create_backups=True,
    )
    print(f"MERGED: {args.donor} -> {result.canonical_name}")
    print(f"Learned aliases: {', '.join(result.learned_aliases) or '(none)'}")
    print(f"Database backup: {result.database_backup or '(not created)'}")
    if result.catalog_backup:
        print(f"Catalog backup: {result.catalog_backup}")
    if result.build_backup:
        print(f"Build backup: {result.build_backup}")
    print("ATOMIC PLAYER IDENTITY MERGE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
