from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup


# ============================================================
# Configuration
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

OUTPUT_PATH = (
    ROOT
    / "data"
    / "raw"
    / "uesp_collectibles.json"
)

BASE_URL = "https://esolog.uesp.net/viewlog.php"

RECORD_TYPE = "collectibles"

PAGE_SIZE = 1000

REQUEST_DELAY = 1.0

TIMEOUT = 30

USER_AGENT = (
    "Black Feather Foundry / ESO Data Research"
)


# ============================================================
# HTTP
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
    }
)


def fetch_page(start: int = 0) -> str:

    params = {
        "record": RECORD_TYPE,
    }

    if start:
        params["start"] = start

    url = f"{BASE_URL}?{urlencode(params)}"

    print()
    print(f"Fetching: {url}")

    response = session.get(
        url,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    print(
        f"HTTP {response.status_code} "
        f"({len(response.text):,} bytes)"
    )

    return response.text


# ============================================================
# Helpers
# ============================================================

def clean_text(value: str | None) -> str:

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def extract_total_records(
    soup: BeautifulSoup,
) -> int | None:

    text = clean_text(
        soup.get_text(" ", strip=True)
    )

    patterns = [
        r"of\s+([\d,]+)\s+records",
        r"([\d,]+)\s+records",
        r"Total[^0-9]*([\d,]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            try:
                return int(
                    match.group(1).replace(",", "")
                )
            except ValueError:
                pass

    return None


def extract_definitions(
    soup: BeautifulSoup,
) -> list[dict]:

    definitions: list[dict] = []

    # Capture definition-like blocks without assuming
    # a single exact UESP markup structure.
    for element in soup.find_all(
        ["dl", "dt", "dd"]
    ):

        if element.name == "dl":

            children = list(
                element.find_all(
                    ["dt", "dd"],
                    recursive=False,
                )
            )

            current_name = None

            for child in children:

                text = clean_text(
                    child.get_text(
                        " ",
                        strip=True,
                    )
                )

                if not text:
                    continue

                if child.name == "dt":

                    current_name = text

                elif (
                    child.name == "dd"
                    and current_name
                ):

                    definitions.append(
                        {
                            "term": current_name,
                            "definition": text,
                        }
                    )

                    current_name = None

    # Also capture obvious definition paragraphs.
    for element in soup.find_all(
        ["p", "div"]
    ):

        text = clean_text(
            element.get_text(
                " ",
                strip=True,
            )
        )

        if not text:
            continue

        if ":" not in text:
            continue

        if len(text) > 500:
            continue

        left, right = text.split(
            ":",
            1,
        )

        left = clean_text(left)
        right = clean_text(right)

        if (
            left
            and right
            and len(left) <= 80
            and len(right) >= 5
        ):

            definitions.append(
                {
                    "term": left,
                    "definition": right,
                }
            )

    # Deduplicate while preserving order.
    seen = set()
    result = []

    for item in definitions:

        key = (
            item["term"],
            item["definition"],
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


# ============================================================
# Table extraction
# ============================================================

def extract_tables(
    soup: BeautifulSoup,
) -> list[dict]:

    tables = []

    for table_index, table in enumerate(
        soup.find_all("table")
    ):

        rows = table.find_all("tr")

        if not rows:
            continue

        headers = []

        # Find the first useful header row.
        for row in rows:

            cells = row.find_all(
                ["th", "td"]
            )

            values = [
                clean_text(
                    cell.get_text(
                        " ",
                        strip=True,
                    )
                )
                for cell in cells
            ]

            if not values:
                continue

            if row.find("th"):

                headers = values
                break

        if not headers:
            continue

        records = []

        for row in rows:

            cells = row.find_all(
                ["td", "th"]
            )

            if not cells:
                continue

            values = [
                clean_text(
                    cell.get_text(
                        " ",
                        strip=True,
                    )
                )
                for cell in cells
            ]

            if values == headers:
                continue

            if len(values) != len(headers):
                continue

            record = {}

            for header, value in zip(
                headers,
                values,
            ):

                if not header:
                    continue

                record[header] = value

            if record:
                records.append(record)

        if records:

            tables.append(
                {
                    "table_index": table_index,
                    "headers": headers,
                    "records": records,
                }
            )

    return tables


# ============================================================
# Page parsing
# ============================================================

def parse_page(
    html: str,
    start: int,
) -> dict:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    total_records = (
        extract_total_records(soup)
    )

    definitions = extract_definitions(
        soup
    )

    tables = extract_tables(
        soup
    )

    return {
        "start": start,
        "total_records": total_records,
        "definitions": definitions,
        "tables": tables,
    }


# ============================================================
# Select collectible table
# ============================================================

def choose_collectible_table(
    tables: list[dict],
) -> dict | None:

    if not tables:
        return None

    # Prefer the table with the most records.
    # The collectible log should have the largest table.
    return max(
        tables,
        key=lambda table: len(
            table["records"]
        ),
    )


# ============================================================
# Main crawler
# ============================================================

def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" UESP Collectibles Crawler")
    print("=" * 60)
    print()

    all_records: list[dict] = []
    all_definitions: list[dict] = []

    seen_collectible_ids: set[str] = set()

    pages = []

    total_records = None

    start = 0

    while True:

        html = fetch_page(start)

        parsed = parse_page(
            html,
            start,
        )

        pages.append(
            {
                "start": start,
                "total_records": (
                    parsed["total_records"]
                ),
            }
        )

        if (
            total_records is None
            and parsed["total_records"]
        ):

            total_records = (
                parsed["total_records"]
            )

            print(
                f"Reported total: "
                f"{total_records:,}"
            )

        all_definitions.extend(
            parsed["definitions"]
        )

        table = choose_collectible_table(
            parsed["tables"]
        )

        if table is None:

            raise RuntimeError(
                f"No data table found "
                f"on page starting at {start}."
            )

        records = table["records"]

        print(
            f"Records on page: "
            f"{len(records):,}"
        )

        if not records:

            break

        new_records = 0

        for record in records:

            # Try common collectible ID columns.
            collectible_id = ""

            for key in (
                "ID",
                "Id",
                "id",
                "Collectible ID",
                "Collectible",
            ):

                if key in record:

                    collectible_id = (
                        clean_text(
                            record[key]
                        )
                    )

                    if collectible_id:
                        break

            # Preserve records even when an ID
            # cannot be determined.
            if (
                collectible_id
                and collectible_id
                in seen_collectible_ids
            ):

                continue

            if collectible_id:

                seen_collectible_ids.add(
                    collectible_id
                )

            all_records.append(
                {
                    "page_start": start,
                    "collectible_id": (
                        collectible_id
                    ),
                    "fields": record,
                }
            )

            new_records += 1

        print(
            f"New records collected: "
            f"{new_records:,}"
        )

        # Stop if we've reached the reported total.
        if (
            total_records is not None
            and len(all_records)
            >= total_records
        ):

            break

        # If fewer than PAGE_SIZE records
        # appeared, we've reached the end.
        if len(records) < PAGE_SIZE:

            break

        start += PAGE_SIZE

        time.sleep(
            REQUEST_DELAY
        )

    # --------------------------------------------------------
    # Deduplicate definitions
    # --------------------------------------------------------

    unique_definitions = []

    seen_definitions = set()

    for definition in all_definitions:

        key = (
            definition["term"],
            definition["definition"],
        )

        if key in seen_definitions:
            continue

        seen_definitions.add(key)

        unique_definitions.append(
            definition
        )

    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------

    missing_ids = sum(
        1
        for record in all_records
        if not record["collectible_id"]
    )

    type_counts = {}

    category_counts = {}

    for record in all_records:

        fields = record["fields"]

        for key in fields:

            normalized = key.lower()

            if normalized == "type":

                value = fields[key]

                if value:
                    type_counts[value] = (
                        type_counts.get(
                            value,
                            0,
                        )
                        + 1
                    )

            if normalized == "category":

                value = fields[key]

                if value:
                    category_counts[value] = (
                        category_counts.get(
                            value,
                            0,
                        )
                        + 1
                    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    output = {
        "source": {
            "name": "UESP ESO Logs",
            "record": RECORD_TYPE,
            "url": BASE_URL,
        },

        "crawl": {
            "timestamp_utc": datetime.now(
                timezone.utc
            ).isoformat(),

            "reported_total": total_records,

            "pages_fetched": len(pages),

            "records_collected": len(
                all_records
            ),

            "missing_collectible_ids": (
                missing_ids
            ),

            "definitions_captured": bool(
                unique_definitions
            ),
        },

        "definitions": (
            unique_definitions
        ),

        "pages": pages,

        "statistics": {
            "types": dict(
                sorted(
                    type_counts.items(),
                    key=lambda x: (
                        -x[1],
                        x[0],
                    ),
                )
            ),

            "categories": dict(
                sorted(
                    category_counts.items(),
                    key=lambda x: (
                        -x[1],
                        x[0],
                    ),
                )
            ),
        },

        "collectibles": all_records,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            output,
            handle,
            ensure_ascii=False,
            indent=2,
        )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(" UESP Collectibles Crawl Complete")
    print("=" * 60)
    print()

    print(
        f"Reported total:       "
        f"{total_records:,}"
        if total_records is not None
        else "Reported total:       unknown"
    )

    print(
        f"Pages fetched:        "
        f"{len(pages):,}"
    )

    print(
        f"Records collected:    "
        f"{len(all_records):,}"
    )

    print(
        f"Missing IDs:          "
        f"{missing_ids:,}"
    )

    print(
        f"Definitions captured: "
        f"{len(unique_definitions):,}"
    )

    print()

    print(
        f"Output: {OUTPUT_PATH}"
    )

    print()

    if total_records is not None:

        if (
            len(all_records)
            == total_records
        ):

            print(
                "STATUS: COMPLETE"
            )

        else:

            print(
                "STATUS: RECORD COUNT "
                "MISMATCH"
            )

            print(
                f"Expected: {total_records:,}"
            )

            print(
                f"Got:      {len(all_records):,}"
            )


if __name__ == "__main__":
    main()