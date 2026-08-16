from __future__ import annotations

import json
import re
from pathlib import Path
from collections import Counter


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = ROOT / "data" / "raw"

OUTPUT_PATH = RAW_DIR / "uesp_collectibles.json"


# ============================================================
# Configuration
# ============================================================

FILE_PATTERN = "uesp_collectibles_*.htm*"


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


def page_number(path: Path) -> int:
    match = re.search(
        r"uesp_collectibles_(\d+)\.html?$",
        path.name,
        re.IGNORECASE,
    )

    if not match:
        raise ValueError(
            f"Could not determine page number: {path.name}"
        )

    return int(match.group(1))


def load_html(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


# ============================================================
# HTML parser
# ============================================================

def parse_html(html: str):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError(
            "BeautifulSoup is required.\n"
            "Install it with:\n"
            "pip install beautifulsoup4"
        )

    return BeautifulSoup(
        html,
        "html.parser",
    )


# ============================================================
# Definitions
# ============================================================

def extract_definitions(soup) -> list[dict]:
    definitions = []

    # --------------------------------------------------------
    # Definition lists
    # --------------------------------------------------------

    for dl in soup.find_all("dl"):

        current_term = None

        for child in dl.find_all(
            ["dt", "dd"],
            recursive=False,
        ):

            text = clean_text(
                child.get_text(
                    " ",
                    strip=True,
                )
            )

            if not text:
                continue

            if child.name == "dt":

                current_term = text

            elif (
                child.name == "dd"
                and current_term
            ):

                definitions.append(
                    {
                        "term": current_term,
                        "definition": text,
                    }
                )

                current_term = None

    # --------------------------------------------------------
    # Definition-like text
    # --------------------------------------------------------

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
            not left
            or not right
            or len(left) > 80
            or len(right) < 5
        ):
            continue

        definitions.append(
            {
                "term": left,
                "definition": right,
            }
        )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    result = []
    seen = set()

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
# Tables
# ============================================================

def extract_tables(soup) -> list[dict]:

    tables = []

    for index, table in enumerate(
        soup.find_all("table")
    ):

        rows = table.find_all("tr")

        if not rows:
            continue

        headers = None
        header_row_index = None

        # ----------------------------------------------------
        # Find actual header row
        # ----------------------------------------------------

        for row_index, row in enumerate(rows):

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
                header_row_index = row_index
                break

        if not headers:
            continue

        records = []

        # ----------------------------------------------------
        # Extract rows
        # ----------------------------------------------------

        for row in rows[
            (header_row_index or 0) + 1:
        ]:

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
                    "table_index": index,
                    "headers": headers,
                    "records": records,
                }
            )

    return tables


# ============================================================
# Identify collectible table
# ============================================================

def score_table(table: dict) -> int:

    headers = {
        clean_text(header).lower()
        for header in table["headers"]
    }

    score = 0

    expected = {
        "id": 10,
        "name": 10,
        "type": 8,
        "category": 8,
        "subcategory": 8,
        "description": 5,
        "acquisition": 5,
        "impact": 5,
    }

    for header, points in expected.items():

        if header in headers:
            score += points

    # A large table is useful evidence,
    # but NOT enough by itself.
    score += min(
        len(table["records"]) // 100,
        10,
    )

    return score


def choose_collectible_table(
    tables: list[dict],
) -> dict:

    if not tables:
        raise RuntimeError(
            "No usable tables found."
        )

    ranked = sorted(
        tables,
        key=score_table,
        reverse=True,
    )

    return ranked[0]


# ============================================================
# Collectible ID extraction
# ============================================================

def extract_collectible_id(
    record: dict,
) -> str:

    preferred = [
        "ID",
        "Id",
        "id",
        "Collectible ID",
        "Collectible Id",
        "Collectible",
    ]

    for key in preferred:

        if key not in record:
            continue

        value = clean_text(
            record[key]
        )

        if value:
            return value

    # Fallback: find an ID-looking field.
    for key, value in record.items():

        normalized = clean_text(value)

        if (
            normalized
            and re.fullmatch(
                r"\d+",
                normalized,
            )
        ):

            if "id" in key.lower():

                return normalized

    return ""


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" UESP Collectibles Local Parser")
    print("=" * 60)
    print()

    files = sorted(
        RAW_DIR.glob(FILE_PATTERN),
        key=page_number,
    )

    if not files:
        raise FileNotFoundError(
            "No UESP collectible HTML files found."
        )

    print(
        f"HTML pages found: {len(files):,}"
    )

    print()

    all_records = []
    all_definitions = []

    page_stats = []

    seen_ids = set()
    duplicate_ids = []
    missing_ids = []

    # --------------------------------------------------------
    # Parse every page
    # --------------------------------------------------------

    for path in files:

        number = page_number(path)

        print(
            f"[PAGE {number:04d}] "
            f"{path.name} "
            f"({path.stat().st_size:,} bytes)"
        )

        html = load_html(path)

        soup = parse_html(html)

        definitions = extract_definitions(
            soup
        )

        all_definitions.extend(
            definitions
        )

        tables = extract_tables(
            soup
        )

        if not tables:

            raise RuntimeError(
                f"No tables found in {path.name}"
            )

        table = choose_collectible_table(
            tables
        )

        print(
            f"           headers: "
            f"{len(table['headers'])}"
        )

        print(
            f"           records: "
            f"{len(table['records']):,}"
        )

        print(
            f"           score: "
            f"{score_table(table)}"
        )

        page_record_count = 0

        for record in table["records"]:

            collectible_id = (
                extract_collectible_id(
                    record
                )
            )

            if not collectible_id:

                missing_ids.append(
                    {
                        "page": number,
                        "record": record,
                    }
                )

            elif collectible_id in seen_ids:

                duplicate_ids.append(
                    {
                        "id": collectible_id,
                        "page": number,
                        "record": record,
                    }
                )

            else:

                seen_ids.add(
                    collectible_id
                )

            all_records.append(
                {
                    "source_page": number,
                    "source_file": path.name,
                    "collectible_id": (
                        collectible_id
                    ),
                    "fields": record,
                }
            )

            page_record_count += 1

        page_stats.append(
            {
                "page": number,
                "file": path.name,
                "bytes": path.stat().st_size,
                "records": page_record_count,
                "headers": table["headers"],
            }
        )

        print()

    # --------------------------------------------------------
    # Deduplicate definitions
    # --------------------------------------------------------

    unique_definitions = []
    definition_seen = set()

    for definition in all_definitions:

        key = (
            definition["term"],
            definition["definition"],
        )

        if key in definition_seen:
            continue

        definition_seen.add(key)

        unique_definitions.append(
            definition
        )

    # --------------------------------------------------------
    # Field statistics
    # --------------------------------------------------------

    field_counts = Counter()

    for item in all_records:

        for field in item["fields"]:

            field_counts[field] += 1

    # --------------------------------------------------------
    # Type/category statistics
    # --------------------------------------------------------

    type_counts = Counter()
    category_counts = Counter()
    subcategory_counts = Counter()

    for item in all_records:

        fields = item["fields"]

        for key, counter in (
            ("Type", type_counts),
            ("Category", category_counts),
            ("Subcategory", subcategory_counts),
        ):

            if key not in fields:
                continue

            value = clean_text(
                fields[key]
            )

            if value:
                counter[value] += 1

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    output = {
        "source": {
            "name": "UESP ESO Logs",
            "record": "collectibles",
            "url": (
                "https://esolog.uesp.net/"
                "viewlog.php?record=collectibles"
            ),
        },

        "crawl": {
            "mode": "local_html",
            "pages": len(files),
            "records": len(all_records),
            "unique_collectible_ids": len(
                seen_ids
            ),
            "duplicate_ids": len(
                duplicate_ids
            ),
            "missing_ids": len(
                missing_ids
            ),
        },

        "definitions": (
            unique_definitions
        ),

        "pages": page_stats,

        "field_coverage": dict(
            sorted(
                field_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),

        "statistics": {
            "types": dict(
                type_counts.most_common()
            ),
            "categories": dict(
                category_counts.most_common()
            ),
            "subcategories": dict(
                subcategory_counts.most_common()
            ),
        },

        "duplicates": duplicate_ids,

        "missing_ids": missing_ids,

        "collectibles": all_records,
    }

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

    print("=" * 60)
    print(" UESP Collectibles Parse Complete")
    print("=" * 60)
    print()

    print(
        f"Pages parsed:             "
        f"{len(files):,}"
    )

    print(
        f"Records collected:        "
        f"{len(all_records):,}"
    )

    print(
        f"Unique collectible IDs:    "
        f"{len(seen_ids):,}"
    )

    print(
        f"Duplicate IDs:             "
        f"{len(duplicate_ids):,}"
    )

    print(
        f"Missing IDs:               "
        f"{len(missing_ids):,}"
    )

    print(
        f"Definitions captured:      "
        f"{len(unique_definitions):,}"
    )

    print(
        f"Distinct fields:           "
        f"{len(field_counts):,}"
    )

    print()

    print(
        "Top Types:"
    )

    for name, count in (
        type_counts.most_common(15)
    ):

        print(
            f"  {name}: {count:,}"
        )

    print()

    print(
        "Top Categories:"
    )

    for name, count in (
        category_counts.most_common(15)
    ):

        print(
            f"  {name}: {count:,}"
        )

    print()

    print(
        f"Output:"
    )

    print(
        f"  {OUTPUT_PATH}"
    )

    print()

    if duplicate_ids:

        print(
            "WARNING: duplicate collectible "
            "IDs were found."
        )

    if missing_ids:

        print(
            "WARNING: records without "
            "collectible IDs were found."
        )

    print()

    print(
        "STATUS: PARSE COMPLETE"
    )


if __name__ == "__main__":
    main()