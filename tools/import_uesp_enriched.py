from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_identity_corrections import boss_title_is_excluded
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



def _merge_boss_titles(discovered: list[str], explicit: list[str] | None) -> list[str]:
    """Merge discovered and operator-supplied boss page titles deterministically.

    Explicit titles are a recovery mechanism for content pages where UESP does
    not expose bosses through the section shape understood by find_boss_links().
    They are never inferred from prose.
    """
    result: list[str] = []
    seen: set[str] = set()
    for title in [*discovered, *(explicit or [])]:
        clean = title.strip()
        if not clean:
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(clean)
    return result



def _get_page(client: UespClient, title: str, refresh: bool):
    return client.get_page(title, use_cache=not refresh)



def import_content(
    *,
    client,
    store,
    parser,
    title: str,
    content_type: str,
    force: bool,
    explicit_boss_titles: list[str] | None = None,
) -> None:
    page = _get_page(client, title, force)
    content = parser.parse_content(page, content_type)
    discovered_titles = _boss_links(parser, page)
    merged_titles = _merge_boss_titles(discovered_titles, explicit_boss_titles)
    boss_titles = [
        boss_title
        for boss_title in merged_titles
        if not boss_title_is_excluded(content.id, boss_title)
    ]
    boss_ids: list[str] = []

    excluded_count = len(merged_titles) - len(boss_titles)
    if excluded_count:
        print(
            "BOSS IDENTITY CORRECTION: "
            f"excluded {excluded_count} reviewed false boss title(s) from {content.name}"
        )

    if explicit_boss_titles:
        print(
            "BOSS RECOVERY OVERRIDE: "
            f"{len(explicit_boss_titles)} explicit title(s); "
            f"{len(discovered_titles)} discovered title(s)"
        )

    for boss_title in boss_titles:
        page = _get_page(client, boss_title, force)
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
    page = _get_page(client, title, force)
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
    ap.add_argument("--force", action="store_true", help="Re-fetch UESP pages and re-write structured records.")
    ap.add_argument("--rate-limit", type=float, default=2.0)
    ap.add_argument("--data-root", type=Path, default=Path("data/uesp"))
    ap.add_argument(
        "--boss-title",
        action="append",
        default=[],
        help=(
            "Explicit UESP boss page title to include while importing --content. "
            "Repeat for multiple bosses. Used only as a deterministic recovery "
            "override when section-based boss discovery is incomplete."
        ),
    )
    args = ap.parse_args()

    if args.boss and args.boss_title:
        ap.error("--boss-title is only valid together with --content")

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
                explicit_boss_titles=args.boss_title,
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
