from __future__ import annotations

"""Read-only inventory of raw weapon-enchantment export metadata.

This tool never opens or mutates eso.db. It inspects the raw minedItemSummary JSON
used by the weapon-enchantment importer and reports fields that may carry cadence,
ability, or enchantment identity metadata not currently imported.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "raw" / "weapon_enchantments.json"

INTEREST_TERMS = (
    "cooldown",
    "ability",
    "enchant",
    "proc",
    "duration",
    "effect",
    "id",
)


def _records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("weapon-enchantment raw source must be a JSON object")
    rows = payload.get("minedItemSummary")
    if not isinstance(rows, list):
        raise ValueError("weapon-enchantment raw source is missing minedItemSummary")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("minedItemSummary contains a non-object record")
    return rows


def audit_source(path: Path) -> tuple[Counter[str], dict[str, Counter[str]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = _records(payload)

    key_counts: Counter[str] = Counter()
    interesting_values: dict[str, Counter[str]] = {}

    for row in rows:
        for key, value in row.items():
            key_text = str(key)
            key_counts[key_text] += 1
            folded = key_text.casefold()
            if not any(term in folded for term in INTEREST_TERMS):
                continue

            bucket = interesting_values.setdefault(key_text, Counter())
            if value is None:
                bucket["<null>"] += 1
            elif isinstance(value, (str, int, float, bool)):
                rendered = str(value).strip()
                bucket[rendered if rendered else "<empty>"] += 1
            else:
                bucket[f"<{type(value).__name__}>"] += 1

    return key_counts, interesting_values


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory raw UESP weapon-enchantment JSON keys without modifying any database."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to weapon_enchantments.json",
    )
    parser.add_argument(
        "--sample-values",
        type=int,
        default=8,
        help="Maximum distinct sample values printed per interesting field.",
    )
    args = parser.parse_args()

    key_counts, interesting = audit_source(args.source)

    print(f"source={args.source}")
    print(f"record_fields={len(key_counts)}")
    print("all_fields=")
    for key in sorted(key_counts, key=str.casefold):
        print(f"  {key}: {key_counts[key]}")

    print("interesting_fields=")
    if not interesting:
        print("  <none>")
        return 0

    for key in sorted(interesting, key=str.casefold):
        values = interesting[key]
        print(f"  {key}:")
        for value, count in values.most_common(max(0, args.sample_values)):
            print(f"    {value!r}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
