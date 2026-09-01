"""
Black Feather Foundry
ESO-Hub Skill -> Champion Point Crawler
=======================================

Purpose
-------
Crawls ESO-Hub skill pages and extracts the Champion Points listed in:

    Champion Points that buff <Skill Name>

Important:
- Does NOT require a sitemap.
- Uses the ESO-Hub /en/skills/ index for URL discovery.
- Extracts CPs only from the skill's CP section.
- Preserves relationship conditions such as "only while slotted".
- Uses the champion_point table in eso.db as the authoritative CP-name list.
- Writes research/raw/skill_champion_points.json.
- Caches fetched HTML so interrupted runs can resume without re-downloading pages.

Dependencies:
    pip install requests beautifulsoup4
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "eso.db"
RAW_DIR = ROOT / "research" / "raw"

OUTPUT_PATH = RAW_DIR / "skill_champion_points.json"
CACHE_DIR = RAW_DIR / "eso_hub_skill_cache"

INDEX_URL = "https://eso-hub.com/en/skills/"
BASE_URL = "https://eso-hub.com"

REQUEST_TIMEOUT = (5, 20)
REQUEST_DELAY = 0.75
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_name(value: str) -> str:
    value = normalize_text(value).lower()
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def slugify_name(value: str) -> str:
    value = normalize_name(value)
    return value.replace(" ", "-")


def cache_name(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "__")
    path = re.sub(r"[^A-Za-z0-9_.-]+", "_", path)
    return CACHE_DIR / f"{path or 'index'}.html"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def load_skills() -> list[dict]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    rows = db.execute(
        """
        SELECT
            id,
            base_ability_id,
            name,
            index_name,
            skill_line,
            class_type,
            is_passive,
            is_player,
            is_crafted
        FROM skill
        WHERE name IS NOT NULL
        ORDER BY id
        """
    ).fetchall()

    db.close()

    return [dict(row) for row in rows]


def load_champion_points() -> dict[str, dict]:
    """
    Returns CPs keyed by normalized name.

    We deliberately use the database as the authoritative CP vocabulary.
    This prevents random names appearing elsewhere on the ESO-Hub page from
    being mistaken for Champion Points.
    """
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Discover the actual schema because the CP importer has changed during
    # development and we do not want this crawler tied to one optional column.
    columns = {
        row[1]
        for row in db.execute("PRAGMA table_info(champion_point)").fetchall()
    }

    if "name" not in columns:
        db.close()
        raise RuntimeError(
            "champion_point table does not contain a 'name' column."
        )

    rows = db.execute(
        "SELECT * FROM champion_point WHERE name IS NOT NULL"
    ).fetchall()

    result = {}
    for row in rows:
        record = dict(row)
        name = normalize_text(record["name"])
        result[normalize_name(name)] = {
            "id": record.get("id"),
            "name": name,
        }

    db.close()
    return result


# ---------------------------------------------------------------------------
# HTML fetching / caching
# ---------------------------------------------------------------------------

def fetch_html(url: str, force: bool = False) -> str | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_name(url)

    if path.exists() and not force:
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
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

            if response.status_code in (403, 401):
                print(f"    HTTP {response.status_code}: {url}")
                return None

            print(
                f"    HTTP {response.status_code} "
                f"(attempt {attempt}/{MAX_RETRIES}): {url}"
            )

        except requests.RequestException as exc:
            print(
                f"    Request error "
                f"(attempt {attempt}/{MAX_RETRIES}): {exc}"
            )

        if attempt < MAX_RETRIES:
            time.sleep(2 * attempt)

    return None


# ---------------------------------------------------------------------------
# URL discovery
# ---------------------------------------------------------------------------

def discover_skill_urls() -> list[dict]:
    """
    ESO-Hub does not need to expose a sitemap for this.

    The main /en/skills/ page contains a large collection of skill links.
    We collect every unique /en/skills/... URL and the visible anchor text.
    """
    print()
    print("Discovering ESO-Hub skill URLs...")
    html = fetch_html(INDEX_URL)

    if not html:
        raise RuntimeError("Could not fetch ESO-Hub skill index.")

    soup = BeautifulSoup(html, "html.parser")

    found: dict[str, dict] = {}

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        absolute = urljoin(BASE_URL, href)

        if not absolute.startswith(BASE_URL + "/en/skills/"):
            continue

        # Ignore the root skills index itself.
        parsed = urlparse(absolute)
        if parsed.path.rstrip("/") == "/en/skills":
            continue

        text = normalize_text(anchor.get_text(" ", strip=True))

        # Remove fragments/query strings so cache keys stay stable.
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        if clean not in found:
            found[clean] = {
                "url": clean,
                "anchor_text": text,
                "slug": parsed.path.rstrip("/").split("/")[-1],
            }
        elif len(text) > len(found[clean]["anchor_text"]):
            found[clean]["anchor_text"] = text

    urls = list(found.values())

    print(f"ESO-Hub skill URLs discovered: {len(urls)}")
    return urls


def choose_skill_url(skill: dict, urls: list[dict]) -> dict | None:
    """
    Match a canonical DB skill to an ESO-Hub URL.

    Prefer:
      1. Exact visible anchor-name match.
      2. Exact slug match.
      3. Slug containing the normalized skill name.

    We deliberately do NOT silently choose among multiple exact matches.
    Duplicate ESO-Hub skill names are reported as ambiguous.
    """
    target = normalize_name(skill["name"])
    slug_target = slugify_name(skill["name"])

    exact_name = [
        item for item in urls
        if normalize_name(item["anchor_text"]) == target
    ]

    if len(exact_name) == 1:
        return exact_name[0]

    exact_slug = [
        item for item in urls
        if item["slug"].lower() == slug_target
    ]

    if len(exact_slug) == 1:
        return exact_slug[0]

    containing = [
        item for item in urls
        if target and target in normalize_name(item["anchor_text"])
    ]

    if len(containing) == 1:
        return containing[0]

    if len(exact_name) > 1:
        # Prefer a URL whose slug exactly matches the skill name.
        slug_matches = [
            item for item in exact_name
            if item["slug"].lower() == slug_target
        ]
        if len(slug_matches) == 1:
            return slug_matches[0]

    return None


# ---------------------------------------------------------------------------
# CP-section extraction
# ---------------------------------------------------------------------------

CP_HEADING_RE = re.compile(
    r"champion\s+points\s+that\s+buff",
    re.IGNORECASE,
)

CONDITION_RE = re.compile(
    r"^\(\s*(.*?)\s*\)$",
    re.IGNORECASE,
)


def is_heading_tag(tag: Tag) -> bool:
    return bool(tag.name and re.fullmatch(r"h[1-6]", tag.name.lower()))


def heading_text(tag: Tag) -> str:
    return normalize_text(tag.get_text(" ", strip=True))


def find_cp_heading(soup: BeautifulSoup, skill_name: str) -> Tag | None:
    """
    Find the actual skill CP heading, not the site's navigation item
    simply named "Champion Points".
    """
    expected = normalize_name(
        f"Champion Points that buff {skill_name}"
    )

    # First choice: exact normalized heading text.
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = normalize_name(heading_text(tag))
        if text == expected:
            return tag

    # ESO-Hub may render the heading as a div/span rather than a semantic
    # heading. Search text nodes for the full phrase.
    phrase = f"Champion Points that buff {skill_name}".lower()

    for node in soup.find_all(string=True):
        text = normalize_text(str(node))
        if phrase in text.lower():
            # Walk upward looking for a sensible section container.
            current = node.parent
            for _ in range(5):
                if current is None:
                    break

                current_text = normalize_text(
                    current.get_text(" ", strip=True)
                )

                if "champion points that buff" in current_text.lower():
                    return current

                current = current.parent

    return None


def section_boundary(tag: Tag) -> Tag | None:
    """
    Find the next heading after a CP section.

    This prevents us from accidentally collecting CP names from the rest
    of the 600KB+ page.
    """
    current = tag

    while current is not None:
        sibling = current.find_next_sibling()

        while sibling is not None:
            if isinstance(sibling, Tag) and is_heading_tag(sibling):
                return sibling

            # Some layouts use a div with heading-like classes.
            if isinstance(sibling, Tag):
                cls = " ".join(sibling.get("class", []))
                txt = normalize_text(sibling.get_text(" ", strip=True))
                if (
                    "heading" in cls.lower()
                    and len(txt) < 200
                ):
                    return sibling

            sibling = sibling.find_next_sibling()

        current = current.parent
        if current is not None and is_heading_tag(current):
            return current

    return None


def extract_cp_section(
    soup: BeautifulSoup,
    skill_name: str,
    cp_vocab: dict[str, dict],
) -> tuple[list[dict], str | None]:
    """
    Extract ALL CP entries from the actual CP section.

    Key design:
    We don't identify CPs by HTML class names. Those are liable to change.

    Instead:
      - find the exact CP section heading
      - inspect only that bounded section
      - match visible text against the CP names already in our DB
      - capture the following parenthesized condition when present
    """
    heading = find_cp_heading(soup, skill_name)

    if heading is None:
        return [], "CP section not found"

    # Determine the content container.
    if isinstance(heading, Tag):
        container = heading.parent

        # Walk upward until the text is large enough to contain several
        # entries, but stop before swallowing the whole page.
        best = container

        for _ in range(4):
            if container is None:
                break

            text = normalize_text(container.get_text(" ", strip=True))

            if (
                "champion points that buff" in text.lower()
                and len(text) < 5000
            ):
                best = container

            container = container.parent

        container = best

    else:
        container = heading.parent

    # We need the text after the heading but before the next section.
    # Use a bounded DOM walk rather than the entire page.
    boundary = section_boundary(heading)

    nodes: list[Tag | NavigableString] = []

    if isinstance(heading, Tag):
        # Collect siblings within the heading's immediate parent first.
        parent = heading.parent

        if parent is not None:
            started = False
            for child in parent.children:
                if child is heading:
                    started = True
                    continue

                if not started:
                    continue

                if isinstance(child, Tag):
                    if boundary is not None and child is boundary:
                        break
                    nodes.append(child)
                elif isinstance(child, NavigableString):
                    nodes.append(child)

    # If the heading isn't directly useful as a sibling container, fall
    # back to the bounded container text.
    if not nodes and container is not None:
        nodes = list(container.find_all(["div", "li", "span", "a", "p"]))

    # ------------------------------------------------------------------
    # Build a clean stream of text chunks.
    # ------------------------------------------------------------------
    chunks: list[str] = []

    for node in nodes:
        if isinstance(node, NavigableString):
            text = normalize_text(str(node))
            if text:
                chunks.append(text)
            continue

        if not isinstance(node, Tag):
            continue

        # Avoid nested duplication by only considering leaf-ish elements.
        if node.find(["div", "li", "p", "a"], recursive=False):
            continue

        text = normalize_text(node.get_text(" ", strip=True))
        if text:
            chunks.append(text)

    # De-duplicate adjacent identical chunks caused by nested spans.
    cleaned: list[str] = []
    for chunk in chunks:
        if not cleaned or chunk != cleaned[-1]:
            cleaned.append(chunk)

    # ------------------------------------------------------------------
    # Match CP names.
    # ------------------------------------------------------------------
    cp_names = sorted(cp_vocab.keys(), key=len, reverse=True)

    results: list[dict] = []
    seen: set[str] = set()

    for index, chunk in enumerate(cleaned):
        normalized_chunk = normalize_name(chunk)

        matched_name = None

        # Exact CP text.
        if normalized_chunk in cp_vocab:
            matched_name = normalized_chunk

        # A CP name can occasionally have trailing condition text.
        if matched_name is None:
            for cp_name in cp_names:
                if normalized_chunk.startswith(cp_name + " "):
                    remainder = normalized_chunk[len(cp_name):].strip()
                    if remainder:
                        matched_name = cp_name
                        break

        if matched_name is None:
            continue

        if matched_name in seen:
            continue

        condition = None

        # Look at following chunks for the site's parenthesized qualifier.
        for following in cleaned[index + 1:index + 4]:
            m = CONDITION_RE.match(following)
            if m:
                condition = normalize_text(m.group(1))
                break

            # Sometimes HTML strips the parentheses into text.
            lower = following.lower()
            if lower == "only while slotted":
                condition = "only while slotted"
                break

        cp_record = cp_vocab[matched_name]

        results.append(
            {
                "champion_point_id": cp_record["id"],
                "champion_point_name": cp_record["name"],
                "condition": condition,
                "source": "ESO-Hub",
            }
        )

        seen.add(matched_name)

    return results, None


# ---------------------------------------------------------------------------
# Main crawler
# ---------------------------------------------------------------------------

class ESOHubSkillCPCrawler:
    def __init__(self) -> None:
        self.skills = load_skills()
        self.cp_vocab = load_champion_points()

        self.urls: list[dict] = []
        self.results: list[dict] = []

        self.stats = {
            "skills_total": len(self.skills),
            "urls_discovered": 0,
            "skills_matched_to_url": 0,
            "skills_without_url": 0,
            "pages_fetched": 0,
            "pages_failed": 0,
            "skills_with_cp": 0,
            "skills_without_cp": 0,
            "cp_links": 0,
        }

    def run(self) -> None:
        print("=" * 55)
        print(" Black Feather Foundry")
        print(" ESO-Hub Skill -> Champion Point Crawler")
        print("=" * 55)
        print()
        print(f"Database: {DB_PATH}")
        print(f"Output:   {OUTPUT_PATH}")
        print(f"Skills:   {len(self.skills)}")
        print(f"CP names: {len(self.cp_vocab)}")

        self.urls = discover_skill_urls()
        self.stats["urls_discovered"] = len(self.urls)

        for number, skill in enumerate(self.skills, start=1):
            name = skill["name"]

            print(
                f"[{number}/{len(self.skills)}] "
                f"{name}",
                end="",
                flush=True,
            )

            match = choose_skill_url(skill, self.urls)

            if match is None:
                print(" -> NO URL")
                self.stats["skills_without_url"] += 1
                continue

            self.stats["skills_matched_to_url"] += 1
            print(f" -> {match['url']}")

            html = fetch_html(match["url"])

            if not html:
                self.stats["pages_failed"] += 1
                continue

            self.stats["pages_fetched"] += 1

            soup = BeautifulSoup(html, "html.parser")

            cp_entries, error = extract_cp_section(
                soup,
                name,
                self.cp_vocab,
            )

            record = {
                "skill_id": skill["id"],
                "skill_name": name,
                "skill_base_ability_id": skill["base_ability_id"],
                "skill_line": skill["skill_line"],
                "url": match["url"],
                "champion_points": cp_entries,
            }

            if error:
                record["parse_status"] = error
                self.stats["skills_without_cp"] += 1
            elif cp_entries:
                record["parse_status"] = "ok"
                self.stats["skills_with_cp"] += 1
                self.stats["cp_links"] += len(cp_entries)
            else:
                record["parse_status"] = "section_found_but_no_cp_matches"
                self.stats["skills_without_cp"] += 1

            self.results.append(record)

            # Save continuously so an interrupted crawl still leaves useful
            # data behind.
            self.write_output()

        self.write_output()
        self.print_report()

    def write_output(self) -> None:
        RAW_DIR.mkdir(parents=True, exist_ok=True)

        payload = {
            "source": "ESO-Hub",
            "source_index": INDEX_URL,
            "generated_by": "eso_hub_skill_cp_crawler.py",
            "skills": self.results,
        }

        OUTPUT_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def print_report(self) -> None:
        print()
        print("=" * 55)
        print(" ESO-Hub Skill -> Champion Point Crawl Complete")
        print("=" * 55)
        print()
        print(f"Skills in database:       {self.stats['skills_total']}")
        print(f"ESO-Hub URLs discovered:  {self.stats['urls_discovered']}")
        print(f"Skills matched to URL:    {self.stats['skills_matched_to_url']}")
        print(f"Skills without URL:       {self.stats['skills_without_url']}")
        print(f"Pages fetched:            {self.stats['pages_fetched']}")
        print(f"Pages failed:             {self.stats['pages_failed']}")
        print(f"Skills with CP data:      {self.stats['skills_with_cp']}")
        print(f"Skills without CP data:   {self.stats['skills_without_cp']}")
        print(f"Champion Point links:     {self.stats['cp_links']}")

        print()
        print("=== WALL OF ELEMENTS CHECK ===")

        wall = [
            r for r in self.results
            if normalize_name(r["skill_name"]) == "wall of elements"
        ]

        if not wall:
            print("(Wall of Elements was not crawled)")
        else:
            for record in wall:
                print(record["url"])
                for cp in record["champion_points"]:
                    condition = cp["condition"] or ""
                    print(
                        f"  {cp['champion_point_name']}"
                        + (f" | {condition}" if condition else "")
                    )

            count = sum(len(r["champion_points"]) for r in wall)
            print(f"Total Wall of Elements CP links: {count}")

        print()
        print("Output:")
        print(f"  {OUTPUT_PATH}")


def main() -> None:
    try:
        ESOHubSkillCPCrawler().run()
    except KeyboardInterrupt:
        print("\nCrawler stopped by user.")
        sys.exit(130)
    except Exception as exc:
        print()
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
