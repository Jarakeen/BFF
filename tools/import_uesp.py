from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.uesp_client import UespClient
from services.uesp.uesp_parser import UespParser, slugify
from services.uesp.uesp_encounter_store import UespEncounterStore


def import_content(
    title: str,
    database_path: Path,
    cache_dir: Path,
    force: bool = False,
) -> None:
    client = UespClient(cache_dir=cache_dir)
    parser = UespParser()

    connection = sqlite3.connect(database_path)
    store = UespEncounterStore(connection)

    try:
        print(f"Fetching content: {title}")

        page = client.get_page(
            title,
            use_cache=not force,
        )

        content_type = parser.detect_content_type(page, "trial")
        content = parser.parse_content(page, content_type)

        boss_titles = parser.find_boss_links(page)

        content.boss_ids = [
            slugify(title)
            for title in boss_titles
        ]
        print(
            f"Content: {content.name} "
            f"({content.content_type})"
        )

        print(f"Boss links found: {len(content.boss_ids)}")

        store.save_content(content)

        content.boss_ids = [
            slugify(title)
            for title in boss_titles
        ]

        if not boss_titles:
            print("No linked bosses found.")
            return

        for index, boss_title in enumerate(boss_titles, start=1):
            print(f"[{index}/{len(boss_titles)}] Fetching boss: {boss_title}")

            boss_page = client.get_page(
                boss_title,
                use_cache=not force,
            )

            boss = parser.parse_boss(
                boss_page,
                content_id=content.id,
                content_name=content.name,
            )

            store.save_boss(boss)

            print(
                f"    saved: {boss.name} "
                f"(abilities={len(boss.abilities)}, "
                f"mechanics={len(boss.mechanics)}, "
                f"phases={len(boss.phases)})"
            )

        print()
        print("IMPORT PASSED")
        print(f"  content: {content.name}")
        print(f"  bosses:  {len(boss_titles)}")

    finally:
        connection.close()


def import_boss(
    title: str,
    database_path: Path,
    cache_dir: Path,
    content_id: str = "",
    content_name: str = "",
    force: bool = False,
) -> None:
    client = UespClient(cache_dir=cache_dir)
    parser = UespParser()

    connection = sqlite3.connect(database_path)
    store = UespEncounterStore(connection)

    try:
        print(f"Fetching boss: {title}")

        page = client.get_page(
            title,
            use_cache=not force,
        )

        boss = parser.parse_boss(
            page,
            content_id=content_id,
            content_name=content_name,
        )

        store.save_boss(boss)

        print()
        print("BOSS IMPORT PASSED")
        print(f"  boss:      {boss.name}")
        print(f"  abilities: {len(boss.abilities)}")
        print(f"  mechanics: {len(boss.mechanics)}")
        print(f"  phases:    {len(boss.phases)}")

    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import ESO encounter data from UESP."
    )

    parser.add_argument(
        "--content",
        help='Import one trial/dungeon/arena, e.g. "Rockgrove".',
    )

    parser.add_argument(
        "--boss",
        help='Import one boss, e.g. "Online:Xalvakka".',
    )

    parser.add_argument(
        "--content-id",
        default="",
        help="Content ID to associate with --boss.",
    )

    parser.add_argument(
        "--content-name",
        default="",
        help="Content name to associate with --boss.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the local API cache and fetch fresh data.",
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=REPO_ROOT / "data" / "eso.db",
        help="SQLite database path.",
    )

    parser.add_argument(
        "--cache",
        type=Path,
        default=REPO_ROOT / "data" / "uesp" / ".cache",
        help="UESP API cache directory.",
    )

    args = parser.parse_args()

    if bool(args.content) == bool(args.boss):
        parser.error("Specify exactly one of --content or --boss.")

    if not args.db.exists():
        parser.error(f"Database does not exist: {args.db}")

    if args.content:
        import_content(
            title=args.content,
            database_path=args.db,
            cache_dir=args.cache,
            force=args.force,
        )
    else:
        import_boss(
            title=args.boss,
            database_path=args.db,
            cache_dir=args.cache,
            content_id=args.content_id,
            content_name=args.content_name,
            force=args.force,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())