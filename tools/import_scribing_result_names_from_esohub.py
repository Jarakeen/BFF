from __future__ import annotations

import argparse
import html
import sqlite3
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import DEFAULT_DATABASE
from services.scribing_catalog import compatible_focus, grimoire_names


BASE_URL = "https://eso-hub.com/en/scribing/combination"
SOURCE_KEY = "eso_hub:scribing_combination_pages"
PROBE_GRIMOIRE = "Soul Burst"
PROBE_FOCUS = "Damage Shield"
PROBE_RESULT = "Warding Burst"


@dataclass(frozen=True)
class ResultRow:
    combination_id: int
    grimoire_name: str
    focus_name: str
    result_name: str
    page_url: str


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(str(data or "").split())
        if value:
            self.parts.append(value)


def _extract_value(parts: list[str], label: str) -> str:
    target = label.casefold()
    for index, part in enumerate(parts):
        folded = part.casefold()
        if folded == target:
            for candidate in parts[index + 1 :]:
                if candidate:
                    return candidate.strip()
            return ""
        if folded.startswith(target):
            remainder = part[len(label) :].strip()
            if remainder:
                return remainder
    return ""


def parse_combination_page(page_html: str, combination_id: int, page_url: str) -> ResultRow | None:
    parser = _TextCollector()
    parser.feed(page_html)
    parts = parser.parts

    result_name = html.unescape(_extract_value(parts, "Name:"))
    combination = html.unescape(_extract_value(parts, "Combination:"))
    if not result_name or not combination:
        return None

    matched_grimoire = ""
    matched_focus = ""
    for grimoire in grimoire_names():
        prefix = f"{grimoire} and "
        if combination.startswith(prefix):
            focus = combination[len(prefix) :].strip()
            if focus in compatible_focus(grimoire):
                matched_grimoire = grimoire
                matched_focus = focus
                break

    if not matched_grimoire or not matched_focus:
        return None

    return ResultRow(
        combination_id=int(combination_id),
        grimoire_name=matched_grimoire,
        focus_name=matched_focus,
        result_name=result_name.strip(),
        page_url=page_url,
    )


def fetch_combination(combination_id: int, timeout: float) -> ResultRow | None:
    url = f"{BASE_URL}/{int(combination_id)}"
    request = Request(
        url,
        headers={
            "User-Agent": "BlackFeatherFoundry/1.0 (+https://github.com/Jarakeen/BFF)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = str(response.geturl())
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        if exc.code in {404, 410}:
            return None
        raise
    except URLError:
        raise

    return parse_combination_page(body, int(combination_id), final_url)


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS scribing_result_name_reference_source (
            source_key TEXT PRIMARY KEY,
            source_kind TEXT NOT NULL,
            source_url TEXT NOT NULL,
            probe_verified INTEGER NOT NULL DEFAULT 0,
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scribing_result_name_reference (
            source_key TEXT NOT NULL,
            grimoire_name TEXT NOT NULL,
            focus_name TEXT NOT NULL,
            result_name TEXT NOT NULL,
            combination_id INTEGER,
            page_url TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (source_key, grimoire_name, focus_name),
            FOREIGN KEY (source_key)
                REFERENCES scribing_result_name_reference_source(source_key)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_scribing_result_name_reference_lookup
            ON scribing_result_name_reference(grimoire_name, focus_name);
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Crawl ESO-Hub's public Scribing combination pages and import the "
            "explicit Grimoire + Focus -> resulting skill names into FoundryDock."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE), help=f"Target DB (default: {DEFAULT_DATABASE})")
    parser.add_argument("--start-id", type=int, default=1, help="First public combination id to inspect")
    parser.add_argument("--end-id", type=int, default=250, help="Last public combination id to inspect")
    parser.add_argument("--delay", type=float, default=0.10, help="Delay between requests in seconds")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout in seconds")
    args = parser.parse_args()

    database = Path(args.database).expanduser().resolve()
    if not database.is_file():
        raise FileNotFoundError(f"Database not found: {database}")
    if args.start_id < 1 or args.end_id < args.start_id:
        raise ValueError("Invalid combination id range")

    rows_by_pair: dict[tuple[str, str], ResultRow] = {}
    errors: list[str] = []
    inspected = 0

    for combination_id in range(args.start_id, args.end_id + 1):
        inspected += 1
        try:
            row = fetch_combination(combination_id, args.timeout)
        except (HTTPError, URLError, TimeoutError) as exc:
            errors.append(f"{combination_id}: {exc}")
            row = None

        if row is not None:
            pair = (row.grimoire_name, row.focus_name)
            existing = rows_by_pair.get(pair)
            if existing is not None and existing.result_name != row.result_name:
                raise ValueError(
                    "Conflicting result names for "
                    f"{row.grimoire_name} + {row.focus_name}: "
                    f"{existing.result_name!r} vs {row.result_name!r}"
                )
            rows_by_pair[pair] = row
            print(
                f"[{combination_id:03d}] {row.grimoire_name} + "
                f"{row.focus_name} -> {row.result_name}"
            )

        if args.delay > 0 and combination_id != args.end_id:
            time.sleep(args.delay)

    probe = rows_by_pair.get((PROBE_GRIMOIRE, PROBE_FOCUS))
    probe_verified = bool(probe and probe.result_name == PROBE_RESULT)

    expected_pairs = {
        (grimoire, focus)
        for grimoire in grimoire_names()
        for focus in compatible_focus(grimoire)
    }
    missing_pairs = sorted(expected_pairs - set(rows_by_pair), key=lambda item: (item[0].casefold(), item[1].casefold()))

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO scribing_result_name_reference_source(
                source_key, source_kind, source_url, probe_verified, imported_at
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_key) DO UPDATE SET
                source_kind = excluded.source_kind,
                source_url = excluded.source_url,
                probe_verified = excluded.probe_verified,
                imported_at = CURRENT_TIMESTAMP
            """,
            (SOURCE_KEY, "public_web_reference", BASE_URL, 1 if probe_verified else 0),
        )
        connection.execute(
            "DELETE FROM scribing_result_name_reference WHERE source_key = ?",
            (SOURCE_KEY,),
        )
        for row in rows_by_pair.values():
            connection.execute(
                """
                INSERT INTO scribing_result_name_reference(
                    source_key, grimoire_name, focus_name, result_name,
                    combination_id, page_url
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    SOURCE_KEY,
                    row.grimoire_name,
                    row.focus_name,
                    row.result_name,
                    row.combination_id,
                    row.page_url,
                ),
            )
        connection.commit()

    print()
    print("========================================")
    print(" PUBLIC SCRIBING RESULT-NAME IMPORT")
    print("========================================")
    print(f"Combination ids inspected: {inspected:,}")
    print(f"Result pairs imported:      {len(rows_by_pair):,}")
    print(f"Expected catalog pairs:     {len(expected_pairs):,}")
    print(f"Missing pairs:              {len(missing_pairs):,}")
    print(f"Request errors:             {len(errors):,}")
    print(f"Probe verified:             {probe_verified}")
    if probe:
        print(f"Probe result:               {probe.result_name}")

    if missing_pairs:
        print()
        print("Missing Grimoire + Focus pairs:")
        for grimoire, focus in missing_pairs[:40]:
            print(f"  - {grimoire} + {focus}")
        if len(missing_pairs) > 40:
            print(f"  ... {len(missing_pairs) - 40:,} more")

    if errors:
        print()
        print("Request errors (first 20):")
        for message in errors[:20]:
            print(f"  - {message}")

    if not probe_verified:
        print()
        print("The known Soul Burst + Damage Shield -> Warding Burst probe did not verify.")
        print("Rows were stored for inspection, but the app will not promote this source.")
        return 4
    if missing_pairs:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
