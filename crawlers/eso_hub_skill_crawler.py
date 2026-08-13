"""
Black Feather Foundry
ESO-Hub Skill Crawler

Crawls individual ESO-Hub skill pages and extracts:

    - weapon
    - buffs
    - debuffs
    - status effects
    - armor sets that modify the skill
    - champion points that buff the skill

The crawler resumes from an existing output file when possible.

Source:
    data/raw/eso_hub_skill_urls.json

Output:
    data/raw/eso_hub_skill_data.json
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

URL_MAP_PATH = (
    ROOT
    / "data"
    / "raw"
    / "eso_hub_skill_urls.json"
)

OUTPUT_PATH = (
    ROOT
    / "data"
    / "raw"
    / "eso_hub_skill_data.json"
)


# ============================================================
# SETTINGS
# ============================================================

REQUEST_DELAY = 0.35
TIMEOUT = 25

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)


# ============================================================
# TEXT / URL HELPERS
# ============================================================

def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_name(value: str | None) -> str:
    value = normalize_text(value).lower()
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9']+", " ", value)

    return re.sub(r"\s+", " ", value).strip()


def clean_url(value: str | None) -> str | None:
    if not value:
        return None

    value = value.strip()

    # Handle accidental Markdown links:
    # [https://example.com](https://example.com)
    match = re.search(
        r"\]\((https?://[^)]+)\)",
        value,
    )

    if match:
        value = match.group(1)

    value = value.strip("'\"")

    if not value.startswith("http"):
        return None

    return value.rstrip(")")


# ============================================================
# URL FILTERING
# ============================================================

def is_skill_url(url: str) -> bool:
    """
    Accept individual ESO-Hub skill pages and reject obvious
    skill-line/category landing pages.
    """

    clean = clean_url(url)

    if not clean:
        return False

    if "eso-hub.com/en/skills/" not in clean:
        return False

    path = clean.split(
        "eso-hub.com/en/skills/",
        1,
    )[1]

    parts = [
        part
        for part in path.split("/")
        if part
    ]

    if len(parts) < 3:
        return False

    last = normalize_name(parts[-1])

    rejected = {
        "class",
        "weapon",
        "armor",
        "world",
        "guild",
        "craft",
        "alliance war",
        "pvp",
        "destruction staff",
        "restoration staff",
        "two handed",
        "dual wield",
        "one hand and shield",
        "bow",
    }

    return last not in rejected


# ============================================================
# GENERIC ESO-HUB RELATIONSHIP EXTRACTION
# ============================================================

def find_relationship_section(
    soup: BeautifulSoup,
    heading_phrase: str,
) -> Tag | None:
    """
    Find the exact ESO-Hub relationship section.

    Verified ESO-Hub structure:

        <div class="mb-6">
            <div class="text-lg font-semibold ...">
                SECTION TITLE
            </div>
            <ul>
                <li>
                    <a href="...">
                        ENTRY
                    </a>
                </li>
            </ul>
        </div>

    We deliberately target the styled section-heading div.
    This avoids accidentally finding unrelated page text such
    as the larger "Buffs & Debuffs" navigation heading.
    """

    target = normalize_name(heading_phrase)

    for heading in soup.find_all(
        "div",
        class_=lambda classes: (
            classes
            and "text-lg" in classes
            and "font-semibold" in classes
        ),
    ):
        text = normalize_text(
            heading.get_text(
                " ",
                strip=True,
            )
        )

        normalized = normalize_name(text)

        if not normalized.startswith(target):
            continue

        container = heading.parent

        if not isinstance(container, Tag):
            continue

        return container

    return None


def extract_relationship_items(
    soup: BeautifulSoup,
    heading_phrase: str,
    allow_condition: bool = False,
) -> list[dict]:
    """
    Extract link relationships from one ESO-Hub section.
    """

    container = find_relationship_section(
        soup,
        heading_phrase,
    )

    if container is None:
        return []

    ul = container.find(
        "ul",
        recursive=False,
    )

    if ul is None:
        return []

    results = []
    seen = set()

    for li in ul.find_all(
        "li",
        recursive=False,
    ):
        link = li.find(
            "a",
            href=True,
        )

        if link is None:
            continue

        name = normalize_text(
            link.get_text(
                " ",
                strip=True,
            )
        )

        if not name:
            continue

        key = normalize_name(name)

        if not key or key in seen:
            continue

        item = {
            "name": name,
            "source": "ESO-Hub",
        }

        href = clean_url(
            link.get("href")
        )

        if href:
            item["url"] = href

        if allow_condition:
            span = li.find("span")

            if span is not None:
                condition = normalize_text(
                    span.get_text(
                        " ",
                        strip=True,
                    )
                )

                if (
                    condition.startswith("(")
                    and condition.endswith(")")
                ):
                    condition = (
                        condition[1:-1].strip()
                    )

                if condition:
                    item["condition"] = condition

        results.append(item)
        seen.add(key)

    return results


# ============================================================
# RELATIONSHIP CATEGORIES
# ============================================================

def parse_buffs(
    soup: BeautifulSoup,
) -> list[dict]:
    return extract_relationship_items(
        soup,
        "Buffs",
    )


def parse_debuffs(
    soup: BeautifulSoup,
) -> list[dict]:
    return extract_relationship_items(
        soup,
        "Debuffs",
    )


def parse_status_effects(
    soup: BeautifulSoup,
) -> list[dict]:
    return extract_relationship_items(
        soup,
        "Status effects",
    )


def parse_modifying_sets(
    soup: BeautifulSoup,
) -> list[dict]:
    return extract_relationship_items(
        soup,
        "Armor sets that modify",
    )


def parse_cp_items(
    soup: BeautifulSoup,
) -> list[dict]:
    return extract_relationship_items(
        soup,
        "Champion Points that buff",
        allow_condition=True,
    )


# ============================================================
# WEAPON EXTRACTION
# ============================================================

def parse_weapon(
    soup: BeautifulSoup,
) -> list[dict]:
    """
    Extract ESO-Hub's weapon category and skill line
    from the 'Found in' block.

    Returns:
        []       for non-weapon skills
        [dict]   for weapon skills
    """

    found_in_dd = None

    for dt in soup.find_all("dt"):

        label = dt.get_text(
            " ",
            strip=True,
        ).casefold()

        if label != "found in":
            continue

        parent = dt.parent

        if parent is None:
            continue

        found_in_dd = parent.find("dd")

        if found_in_dd is not None:
            break

    if found_in_dd is None:
        return []

    links = found_in_dd.find_all(
        "a",
        href=True,
    )

    if not links:
        return []

    result = {}

    for link in links:

        href = link.get(
            "href",
            "",
        ).strip()

        text = link.get_text(
            " ",
            strip=True,
        )

        if not text or not href:
            continue

        normalized = href.rstrip("/")

        if normalized.endswith(
            "/en/skills/weapon"
        ):
            result["category"] = text
            result["category_url"] = href

        elif (
            normalized.startswith(
                "https://eso-hub.com/en/skills/weapon/"
            )
            or normalized.startswith(
                "/en/skills/weapon/"
            )
        ):
            result["skill_line"] = text
            result["skill_line_url"] = href

    if "category" not in result:
        return []

    return [result]


# ============================================================
# SKILL NAME
# ============================================================

def extract_skill_name(
    soup: BeautifulSoup,
) -> str | None:

    for tag in soup.find_all(
        ["h1", "h2"],
    ):
        text = normalize_text(
            tag.get_text(
                " ",
                strip=True,
            )
        )

        if not text:
            continue

        text = re.sub(
            r"\s+Skill\s*-\s*ESO\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        if normalize_name(text) in {
            "eso hub",
            "skills",
            "skills database",
        }:
            continue

        return text

    if soup.title:
        title = normalize_text(
            soup.title.get_text(
                " ",
                strip=True,
            )
        )

        title = re.sub(
            r"\s*[-|]\s*ESO[- ]Hub.*$",
            "",
            title,
            flags=re.IGNORECASE,
        )

        if title:
            return title

    return None


# ============================================================
# PAGE FETCHER
# ============================================================

class PageFetcher:

    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def fetch(
        self,
        url: str,
    ) -> str | None:

        try:
            response = self.session.get(
                url,
                timeout=TIMEOUT,
            )

            if response.status_code != 200:
                print(
                    f" -> HTTP {response.status_code}"
                )
                return None

            return response.text

        except requests.RequestException as exc:
            print(
                f" -> REQUEST ERROR: {exc}"
            )
            return None


# ============================================================
# CRAWLER
# ============================================================

class ESOHubSkillCrawler:

    def __init__(self):
        self.fetcher = PageFetcher()

        self.url_map = []
        self.results = []

        self.saved_urls = set()

        self.stats = {
            "urls_loaded": 0,
            "skill_urls": 0,
            "non_skill_urls": 0,
            "duplicates": 0,
            "pages_attempted": 0,
            "pages_fetched": 0,
            "pages_failed": 0,
            "skills_found": 0,
        }

    # --------------------------------------------------------
    # URL LOADING
    # --------------------------------------------------------

    def load_url_map(self):

        if not URL_MAP_PATH.exists():
            raise FileNotFoundError(
                f"URL map not found:\n"
                f"{URL_MAP_PATH}"
            )

        data = json.loads(
            URL_MAP_PATH.read_text(
                encoding="utf-8",
            )
        )

        if isinstance(data, list):
            raw_items = data

        elif isinstance(data, dict):
            raw_items = (
                data.get("urls")
                or data.get("skill_urls")
                or data.get("resolved")
                or []
            )

            if isinstance(raw_items, dict):
                raw_items = list(
                    raw_items.values()
                )

        else:
            raise RuntimeError(
                "Unexpected URL map format: "
                f"{type(data).__name__}"
            )

        seen = set()

        for item in raw_items:

            if isinstance(item, dict):
                url = (
                    item.get("eso_hub_url")
                    or item.get("url")
                )

            elif isinstance(item, str):
                url = item

            else:
                continue

            url = clean_url(url)

            if not url:
                continue

            self.stats["urls_loaded"] += 1

            if url in seen:
                self.stats["duplicates"] += 1
                continue

            seen.add(url)

            if not is_skill_url(url):
                self.stats["non_skill_urls"] += 1
                continue

            self.stats["skill_urls"] += 1

            self.url_map.append(
                {
                    "eso_hub_url": url,
                }
            )

    # --------------------------------------------------------
    # RESUME
    # --------------------------------------------------------

    def load_existing_results(self):

        if not OUTPUT_PATH.exists():
            return

        try:
            data = json.loads(
                OUTPUT_PATH.read_text(
                    encoding="utf-8",
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ):
            print(
                "Existing output could not be read. "
                "Starting fresh."
            )
            return

        if isinstance(data, dict):
            existing = data.get(
                "skills",
                [],
            )
        elif isinstance(data, list):
            existing = data
        else:
            existing = []

        if not isinstance(existing, list):
            return

        for record in existing:

            if not isinstance(record, dict):
                continue

            url = clean_url(
                record.get("eso_hub_url")
            )

            if not url:
                continue

            if url in self.saved_urls and "pierce-armor" not in url:
                continue
                

            self.results.append(record)
            self.saved_urls.add(url)

        self.stats["skills_found"] = (
            len(self.results)
        )

        if self.results:
            print(
                f"Existing skills loaded: "
                f"{len(self.results)}"
            )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    def save(self):

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output = {
            "source": "ESO-Hub",
            "generated_by": (
                "eso_hub_skill_crawler_v2.py"
            ),
            "statistics": self.stats,
            "skills": self.results,
        }

        payload = json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )

        temp_path = None

        try:
            fd, temp_name = tempfile.mkstemp(
                prefix="eso_hub_skill_data_",
                suffix=".tmp",
                dir=str(OUTPUT_PATH.parent),
                text=True,
            )

            temp_path = Path(temp_name)

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(payload)

            os.replace(
                temp_path,
                OUTPUT_PATH,
            )

            temp_path = None

        finally:
            if (
                temp_path is not None
                and temp_path.exists()
            ):
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    # --------------------------------------------------------
    # CRAWL
    # --------------------------------------------------------

    def crawl(self):

        total = len(self.url_map)

        print()
        print("=" * 60)
        print(" ESO-Hub Skill Crawler")
        print("=" * 60)
        print()

        print(
            f"URLs loaded:        "
            f"{self.stats['urls_loaded']}"
        )

        print(
            f"Individual skills: "
            f"{self.stats['skill_urls']}"
        )

        print(
            f"Landing pages skipped: "
            f"{self.stats['non_skill_urls']}"
        )

        print(
            f"Duplicates:         "
            f"{self.stats['duplicates']}"
        )

        print(
            f"Already saved:      "
            f"{len(self.saved_urls)}"
        )

        print()

        for index, row in enumerate(
            self.url_map,
            1,
        ):

            url = row["eso_hub_url"]

            if url in self.saved_urls:
                continue

            self.stats["pages_attempted"] += 1

            print(
                f"[{index}/{total}] "
                f"{url}",
                end="",
                flush=True,
            )

            html = self.fetcher.fetch(url)

            if html is None:
                self.stats["pages_failed"] += 1
                print()
                continue

            self.stats["pages_fetched"] += 1

            soup = BeautifulSoup(
                    html,
                    "html.parser",
                )   

            if "pierce-armor" in url:
                print("\n--- WEAPON HTML DEBUG ---")

                for tag in soup.find_all(
                    ["a", "div", "h2", "h3", "h4"]
                ):
                    text = " ".join(tag.stripped_strings)

                    if (
                        "one hand and shield" in text.lower()
                        or text.strip().lower() == "weapon"
                    ):
                        print(
                            tag.prettify()[:5000]
                        )

            skill_name = extract_skill_name(
                soup
            )

            if not skill_name:
                print(
                    " -> NO SKILL NAME"
                )
                continue

            weapon = parse_weapon(
                soup
            )

            if "pierce-armor" in url:
                print()
                print("WEAPON TEST:", weapon)

            buffs = parse_buffs(
                soup
            )

            debuffs = parse_debuffs(
                soup
            )

            status_effects = parse_status_effects(
                soup
            )

            modifying_sets = parse_modifying_sets(
                soup
            )

            champion_points = parse_cp_items(
                soup
            )

            record = {
                "skill_name": skill_name,
                "eso_hub_url": url,

                "weapon": weapon,

                "buffs": buffs,
                "debuffs": debuffs,
                "status_effects": status_effects,

                "modifying_sets": modifying_sets,

                "champion_points": champion_points,

                "source": "ESO-Hub",
            }

            self.results.append(record)
            self.saved_urls.add(url)

            self.stats["skills_found"] = (
                len(self.results)
            )

            self.save()

            print(
                f" -> {skill_name}"
                f" | weapon={len(weapon)}"
                f" | buffs={len(buffs)}"
                f" | debuffs={len(debuffs)}"
                f" | effects={len(status_effects)}"
                f" | sets={len(modifying_sets)}"
                f" | CP={len(champion_points)}"
            )

            time.sleep(
                REQUEST_DELAY
            )

    # --------------------------------------------------------
    # VALIDATION / SPOT CHECK
    # --------------------------------------------------------

    def spot_check(
        self,
        skill_name: str,
    ):

        target = normalize_name(
            skill_name
        )

        matches = [
            row
            for row in self.results
            if normalize_name(
                row.get("skill_name")
            ) == target
        ]

        if not matches:
            print(
                f"{skill_name}: not found"
            )
            return

        row = matches[0]

        print()
        print(
            f"Skill: {row.get('skill_name')}"
        )
        print(
            f"  Weapon:          "
            f"{len(row.get('weapon', []))}"
        )
        print(
            f"  Buffs:           "
            f"{len(row.get('buffs', []))}"
        )
        print(
            f"  Debuffs:         "
            f"{len(row.get('debuffs', []))}"
        )
        print(
            f"  Status Effects:  "
            f"{len(row.get('status_effects', []))}"
        )
        print(
            f"  Modifying Sets:  "
            f"{len(row.get('modifying_sets', []))}"
        )
        print(
            f"  Champion Points: "
            f"{len(row.get('champion_points', []))}"
        )

        for field in (
            "buffs",
            "debuffs",
            "status_effects",
            "modifying_sets",
        ):
            items = row.get(field, [])

            if not items:
                continue

            print(
                f"  {field}:"
            )

            for item in items:
                condition = item.get(
                    "condition"
                )

                if condition:
                    print(
                        f"    - {item['name']}"
                        f" ({condition})"
                    )
                else:
                    print(
                        f"    - {item['name']}"
                    )

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    def run(self):

        print()
        print("=" * 60)
        print(" Black Feather Foundry")
        print(" ESO-Hub Skill Crawler")
        print("=" * 60)
        print()

        print(
            f"Source: {URL_MAP_PATH}"
        )

        print(
            f"Output: {OUTPUT_PATH}"
        )

        self.load_url_map()
        self.load_existing_results()

        # Make sure the JSON exists before crawling.
        self.save()

        print()
        print(
            f"URL records loaded: "
            f"{len(self.url_map)}"
        )

        print(
            f"Skills already saved: "
            f"{len(self.results)}"
        )

        print()

        self.crawl()

        self.save()

        print()
        print("=" * 60)
        print(" CRAWL COMPLETE")
        print("=" * 60)
        print()

        print(
            f"URLs loaded:           "
            f"{self.stats['urls_loaded']}"
        )

        print(
            f"Individual skills:     "
            f"{self.stats['skill_urls']}"
        )

        print(
            f"Landing pages skipped: "
            f"{self.stats['non_skill_urls']}"
        )

        print(
            f"Duplicates:            "
            f"{self.stats['duplicates']}"
        )

        print(
            f"Pages fetched:         "
            f"{self.stats['pages_fetched']}"
        )

        print(
            f"Pages failed:          "
            f"{self.stats['pages_failed']}"
        )

        print(
            f"Total skills saved:    "
            f"{len(self.results)}"
        )

        print()
        print(
            f"Saved: {OUTPUT_PATH}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    try:
        crawler = ESOHubSkillCrawler()
        crawler.run()

    except KeyboardInterrupt:
        print()
        print()
        print(
            "Crawler stopped by user."
        )
        sys.exit(1)

    except Exception as exc:
        print()
        print(
            f"ERROR: {exc}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

     