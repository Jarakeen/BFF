from __future__ import annotations

import argparse
from pathlib import Path

from services.uesp.enriched_parser import EnrichedUespParser
from services.uesp.uesp_client import UespClient, UespClientError
from services.uesp.uesp_store import UespStore



def _boss_links(parser: EnrichedUespParser, page) -> list[str]:
    """Discover bosses only from an explicit Bosses/Encounters section."""
    titles = parser.find_boss_links(page)
    excluded = {
        "arenas", "dungeons", "trials", "murkmire", "dead water village",
        "imperial", "blackguards",
    }
    words = (
        "achievement", "quest", "item", "set", "style", "furnishing",
        "collectible", "monster", "npc", "location", "zone", "guide",
        "strategy", "journal",
    )
    result: list[str] = []
    seen: set[str] = set()
    for title in titles:
        key = title.casefold().strip()
        if not key or key in excluded or any(word in key for word in words):
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(title)
    return result


def import_content(*, client, store, parser, title: str, content_type: str, force: bool) -> None:
    page = client.get_page(title)
    content = parser.parse_content(page, content_type)
    boss_titles = _boss_links(parser, page)
    boss_ids: list[str] = []

    for boss_title in boss_titles:
        page = client.get_page(boss_title)
        boss = parser.parse_boss(page, content_id=content.id, content_name=content.name)
        boss_ids.append(boss.id)
        revision = boss.source.revision_id if boss.source else 0
        if force or not store.is_up_to_date("bosses", boss.id, revision or 0):
            path = store.save_boss(boss)
            print(f"BOSS    {boss.name} -> {path}")
        else:
            print(f"SKIP    {boss.name} (up to date)")

    content.boss_ids = boss_ids
    revision = content.source.revision_id if content.source else 0
    if force or not store.is_up_to_date(content_type, content.id, revision or 0):
        path = store.save_content(content)
        print(f"CONTENT {content.name} -> {path}")
    else:
        print(f"SKIP    {content.name} (up to date)")


def import_boss(*, client, store, parser, title: str, force: bool) -> None:
    page = client.get_page(title)
    boss = parser.parse_boss(page)
    revision = boss.source.revision_id if boss.source else 0
    if force or not store.is_up_to_date("bosses", boss.id, revision or 0):
        path = store.save_boss(boss)
        print(f"BOSS {boss.name} -> {path}")
    else:
        print(f"SKIP {boss.name} (up to date)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Safe enriched UESP encounter crawler")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--content")
    group.add_argument("--boss")
    ap.add_argument("--content-type", choices=("trial", "dungeon", "arena"), default="trial")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--rate-limit", type=float, default=2.0)
    ap.add_argument("--data-root", type=Path, default=Path("data/uesp"))
    args = ap.parse_args()

    store = UespStore(args.data_root)
    client = UespClient(
        cache_dir=args.data_root / ".cache",
        min_request_interval=args.rate_limit,
    )
    parser = EnrichedUespParser()

    try:
        if args.content:
            import_content(
                client=client,
                store=store,
                parser=parser,
                title=args.content,
                content_type=args.content_type,
                force=args.force,
            )
        else:
            import_boss(
                client=client,
                store=store,
                parser=parser,
                title=args.boss,
                force=args.force,
            )
    except UespClientError as exc:
        print(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
