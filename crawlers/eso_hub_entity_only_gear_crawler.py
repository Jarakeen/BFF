"""Black Feather Foundry
ESO-Hub entity-only gear-set crawler
====================================

Purpose
-------
Recover source-backed set metadata for canonical gear-set entities that are
selectable in FoundryDock but not yet normalized into gear_set / gear_set_piece /
gear_set_bonus.

This crawler is READ-ONLY with respect to eso.db. It:
- reads entity + entity_source
- follows stored ESO-Hub set URLs
- caches HTML under research/raw
- extracts page type, location, set bonus text, and modified skill names
- writes research/raw/eso_hub_entity_only_gear_sets.json

Dependencies:
    pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "eso.db"
RAW_DIR = ROOT / "research" / "raw"
DEFAULT_OUTPUT = RAW_DIR / "eso_hub_entity_only_gear_sets.json"
CACHE_DIR = RAW_DIR / "eso_hub_entity_only_gear_cache"

REQUEST_TIMEOUT = (5, 20)
REQUEST_DELAY = 0.75
MAX_RETRIES = 3

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0 Safari/537.36 "
            "Black-Feather-Foundry/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def cache_path(url: str) -> Path:
    parsed = urlparse(url)
    token = parsed.path.strip("/").replace("/", "__")
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", token)
    return CACHE_DIR / f"{token or 'set'}.html"


def fetch_html(url: str, *, force: bool = False) -> str | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(url)
    if path.exists() and not force:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            pass

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                text = response.text
                path.write_text(text, encoding="utf-8")
                time.sleep(REQUEST_DELAY)
                return text
            if response.status_code == 429:
                wait = min(10 * attempt, 30)
                print(f"    HTTP 429; waiting {wait}s...")
                time.sleep(wait)
                continue
            if response.status_code in (401, 403, 404):
                print(f"    HTTP {response.status_code}: {url}")
                return None
            print(
                f"    HTTP {response.status_code} "
                f"(attempt {attempt}/{MAX_RETRIES}): {url}"
            )
        except requests.RequestException as exc:
            print(
                f"    Request error (attempt {attempt}/{MAX_RETRIES}): {exc}"
            )
        if attempt < MAX_RETRIES:
            time.sleep(2 * attempt)
    return None


def _label_value(soup: BeautifulSoup, label: str) -> str:
    target = label.casefold().rstrip(":")
    strings = [normalize_text(value) for value in soup.stripped_strings]
    for index, value in enumerate(strings):
        clean = value.casefold().rstrip(":")
        if clean == target and index + 1 < len(strings):
            candidate = strings[index + 1]
            if candidate and candidate.casefold() != clean:
                return candidate
    return ""


def _bonus_lines(soup: BeautifulSoup) -> tuple[str, ...]:
    """Extract only the focal set's tooltip bonuses.

    ESO-Hub set pages render many unrelated set cards farther down the page.
    The focal tooltip appears after the page title and before the first Weapons
    section. Some pages split the item-count marker and description into
    separate text nodes, so reconstruct those nodes instead of scanning every
    stripped string on the page.
    """

    marker = re.compile(r"^\(\d+\s+items?\)\s*", re.IGNORECASE)
    exact_marker = re.compile(r"^\(\d+\s+items?\)$", re.IGNORECASE)
    h1 = soup.find("h1")
    strings = list(soup.find_all(string=True))
    start = 0
    if h1 is not None:
        title_string = h1.find(string=True)
        if title_string in strings:
            start = strings.index(title_string) + 1

    stop_prefixes = (
        "compare this armor set with other sets",
        "this armor set modifies the following skills",
        "champion points that buff",
        "top builds using",
        "images of ",
        "available weapon traits",
        "available enchantments",
        "frequently asked questions",
        "other sets in ",
        "[mobile]",
        "[desktop]",
        "skyscraper",
        "window.ramp.",
    )

    result: list[str] = []
    pending: str | None = None
    for raw in strings[start:]:
        parent = getattr(raw, "parent", None)
        if isinstance(parent, Tag) and parent.name in {"script", "style", "noscript"}:
            continue

        text = normalize_text(str(raw))
        if not text:
            continue
        lowered = text.casefold()
        if lowered == "weapons":
            break

        if pending is not None and any(
            lowered.startswith(prefix) for prefix in stop_prefixes
        ):
            if pending not in result:
                result.append(pending)
            pending = None
            continue

        if marker.match(text):
            if pending and pending not in result:
                result.append(pending)
            pending = text
            continue

        if pending is not None:
            # ESO-Hub may split one bonus across several nested spans, e.g.
            # "(2 items)" + "Adds" + "526 Critical Chance," + proc text.
            # Continue collecting until the next item-count marker or an
            # explicit section/ad boundary rather than swallowing page chrome.
            pending = normalize_text(f"{pending} {text}")

    if pending and pending not in result:
        result.append(pending)

    return tuple(result)


def _modified_skills(soup: BeautifulSoup) -> tuple[str, ...]:
    """Extract skill links from ESO-Hub's modified-skills section.

    The section label is not consistently a heading tag, so walk document text
    in order from the label until the next known section boundary and retain
    only anchor text in that interval.
    """

    strings = list(soup.find_all(string=True))
    start: int | None = None
    for index, raw in enumerate(strings):
        text = normalize_text(str(raw)).casefold()
        if text.startswith("this armor set modifies the following skills"):
            start = index + 1
            break
    if start is None:
        return ()

    stop_prefixes = (
        "champion points that buff",
        "top builds using",
        "images of ",
        "available weapon traits",
        "available enchantments",
        "frequently asked questions",
        "other sets in ",
    )
    result: list[str] = []
    for raw in strings[start:]:
        text = normalize_text(str(raw))
        if not text:
            continue
        lowered = text.casefold()
        if any(lowered.startswith(prefix) for prefix in stop_prefixes):
            break
        parent = getattr(raw, "parent", None)
        if isinstance(parent, Tag) and parent.name == "a":
            if text not in result:
                result.append(text)
    return tuple(result)


def parse_set_page(html: str, *, expected_name: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = normalize_text(h1.get_text(" ", strip=True)) if h1 else ""

    bonuses = _bonus_lines(soup)
    set_type = _label_value(soup, "Type")
    location = _label_value(soup, "Location")
    modified_skills = _modified_skills(soup)

    unresolved: list[str] = []
    if not title:
        unresolved.append("missing page title")
    if expected_name and title and expected_name.casefold() not in title.casefold():
        unresolved.append(
            f"page title does not match expected set name: {title!r}"
        )
    if not bonuses:
        unresolved.append("no '(N items)' set bonus text extracted")
    if not set_type:
        unresolved.append("set Type label/value not extracted")
    if str(set_type).casefold() in {"arena", "trial"} and not modified_skills:
        unresolved.append("modified-skill section was not extracted")

    return {
        "name": expected_name,
        "url": url,
        "page_title": title,
        "type": set_type,
        "location": location,
        "bonuses": list(bonuses),
        "modified_skills": list(modified_skills),
        "unresolved": unresolved,
    }


def entity_only_sources(database: Path) -> tuple[dict, ...]:
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            """
            SELECT e.id AS entity_id, e.name, es.raw_json
            FROM entity e
            LEFT JOIN gear_set gs
              ON LOWER(TRIM(gs.name)) = LOWER(TRIM(e.name))
            JOIN entity_source es
              ON es.entity_id = e.id
            WHERE e.entity_type = 'gear_set'
              AND e.name IS NOT NULL
              AND TRIM(e.name) <> ''
              AND gs.id IS NULL
            ORDER BY e.name COLLATE NOCASE, e.id
            """
        ).fetchall()

    result: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        raw = str(row["raw_json"] or "").strip()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        url = normalize_text(str(payload.get("url") or ""))
        key = str(row["entity_id"])
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "entity_id": key,
                "name": str(row["name"]),
                "url": url,
            }
        )
    return tuple(result)


def crawl(
    database: Path,
    *,
    output: Path,
    force: bool = False,
    limit: int | None = None,
) -> tuple[dict, ...]:
    sources = entity_only_sources(database)
    if limit is not None:
        sources = sources[: max(0, int(limit))]

    rows: list[dict] = []
    for index, source in enumerate(sources, start=1):
        name = source["name"]
        url = source["url"]
        print(f"[{index}/{len(sources)}] {name}")
        if not url:
            rows.append(
                {
                    **source,
                    "page_title": "",
                    "type": "",
                    "location": "",
                    "bonuses": [],
                    "modified_skills": [],
                    "unresolved": ["entity_source raw_json has no URL"],
                }
            )
            continue
        html = fetch_html(url, force=force)
        if not html:
            rows.append(
                {
                    **source,
                    "page_title": "",
                    "type": "",
                    "location": "",
                    "bonuses": [],
                    "modified_skills": [],
                    "unresolved": ["source page could not be fetched"],
                }
            )
            continue
        rows.append(parse_set_page(html, expected_name=name, url=url))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crawl source-backed entity-only ESO-Hub gear-set pages"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    rows = crawl(
        args.db,
        output=args.output,
        force=args.force,
        limit=args.limit,
    )
    unresolved = tuple(row for row in rows if row["unresolved"])
    arena = tuple(
        row for row in rows
        if str(row.get("type") or "").casefold() == "arena"
    )
    with_bonuses = tuple(row for row in rows if row["bonuses"])

    print()
    print("ESO-HUB ENTITY-ONLY GEAR CRAWL")
    print(f"database={args.db}")
    print(f"output={args.output}")
    print(f"row_count={len(rows)}")
    print(f"arena_type_count={len(arena)}")
    print(f"with_bonus_text_count={len(with_bonuses)}")
    print(f"unresolved_count={len(unresolved)}")
    for row in unresolved[:20]:
        print(f"UNRESOLVED {row['name']!r}: {'; '.join(row['unresolved'])}")
    if len(unresolved) > 20:
        print(f"... {len(unresolved) - 20} more unresolved")

    print()
    print(
        "NEXT_STEP=review the cached/extracted source evidence; only after bonus "
        "and type coverage is clean should an additive gear_set normalizer write "
        "canonical rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
