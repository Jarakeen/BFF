from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

SOURCE_PATH = ROOT / "data" / "raw" / "drinks_raw.json"
OUTPUT_PATH = ROOT / "data" / "processed" / "drinks.json"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"['’]", "", value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_duration_seconds(ability_desc: str):
    text = clean_text(ability_desc).lower()

    match = re.search(
        r"for\s+(\d+(?:\.\d+)?)\s+hour",
        text,
    )
    if match:
        return float(match.group(1)) * 3600

    match = re.search(
        r"for\s+(\d+(?:\.\d+)?)\s+minute",
        text,
    )
    if match:
        return float(match.group(1)) * 60

    return None


def load_source() -> list[dict]:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            f"Drink source file not found:\n{SOURCE_PATH}"
        )

    with SOURCE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(
            "drinks_raw.json must contain an object."
        )

    records = data.get("minedItemSummary")

    if not isinstance(records, list):
        raise ValueError(
            "drinks_raw.json is missing minedItemSummary."
        )

    return [
        record
        for record in records
        if isinstance(record, dict)
    ]


def convert_drink(record: dict) -> dict | None:
    item_id = clean_text(record.get("itemId"))
    name = clean_text(record.get("name"))

    if not item_id or not name:
        return None

    ability_desc = clean_text(
        record.get("abilityDesc")
    )

    return {
        "id": f"drink_{slugify(name)}",
        "name": name,
        "source_layer": "drinks",

        "source_ids": {
            "itemIds": [item_id],
        },

        "duration_seconds": parse_duration_seconds(
            ability_desc
        ),

        "stats_provided": {
            "max_health": 0,
            "max_magicka": 0,
            "max_stamina": 0,
            "health_recovery": 0,
            "magicka_recovery": 0,
            "stamina_recovery": 0,
        },

        "metadata": {
            "quality": clean_text(
                record.get("quality")
            ),
            "level": clean_text(
                record.get("level")
            ),
            "craft_type": clean_text(
                record.get("craftType")
            ),
            "special_type": clean_text(
                record.get("specialType")
            ),
            "tags": clean_text(
                record.get("tags")
            ),
            "icon": clean_text(
                record.get("icon")
            ),
            "ability_description": ability_desc,
        },

        "raw_records": [record],
    }


def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Drink Processor")
    print("=" * 60)
    print()

    print(f"Source: {SOURCE_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print()

    records = load_source()

    print(
        f"Raw drink records: {len(records):,}"
    )

    drinks: dict[str, dict] = {}
    seen_item_ids: set[str] = set()
    invalid = 0
    duplicate_item_ids = 0

    for record in records:

        item_id = clean_text(
            record.get("itemId")
        )

        if not item_id:
            invalid += 1
            continue

        if item_id in seen_item_ids:
            duplicate_item_ids += 1
            continue

        seen_item_ids.add(item_id)

        drink = convert_drink(record)

        if drink is None:
            invalid += 1
            continue

        drink_id = drink["id"]

        if drink_id not in drinks:
            drinks[drink_id] = drink
        else:
            existing = drinks[drink_id]

            existing["source_ids"]["itemIds"].append(
                item_id
            )

            existing["raw_records"].append(
                record
            )

    processed = list(drinks.values())

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            processed,
            handle,
            ensure_ascii=False,
            indent=2,
        )

    total_source_ids = sum(
        len(drink["source_ids"]["itemIds"])
        for drink in processed
    )

    print()
    print("=" * 60)
    print(" Drink Processing Complete")
    print("=" * 60)
    print()

    print(
        f"Raw records:             {len(records):,}"
    )

    print(
        f"Canonical drinks:        {len(processed):,}"
    )

    print(
        f"Unique ESO item IDs:     {total_source_ids:,}"
    )

    print(
        f"Invalid records:         {invalid:,}"
    )

    print(
        f"Duplicate item IDs:      {duplicate_item_ids:,}"
    )

    print()
    print(
        f"Written: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()