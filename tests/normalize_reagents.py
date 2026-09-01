import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
TRANSITIONS_PATH = ROOT / "data" / "processed" / "update_51_effect_transitions.json"
OUTPUT_PATH = ROOT / "data" / "processed" / "reagents_normalized.json"

SOURCE_CANDIDATES = [
    "reagents_raw.json",
    "reagent_raw.json",
    "alchemy_reagents_raw.json",
    "alchemy_reagent_raw.json",
    "reagents.json",
]


def slugify(value):
    value = str(value or "").casefold().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def load_source():
    for filename in SOURCE_CANDIDATES:
        path = RAW_DIR / filename
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return path, json.load(handle)

    names = "\n".join(
        f"  - {name}" for name in SOURCE_CANDIDATES
    )
    raise FileNotFoundError(
        "No reagent source file found.\n"
        "Expected one of:\n"
        f"{names}\n\n"
        "Put the actual reagent JSON in research/raw and rerun."
    )


def extract_records(data):
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        raise ValueError("Reagent source must be a JSON list or object.")

    for key in (
        "reagents",
        "items",
        "data",
        "records",
        "minedItemSummary",
    ):
        value = data.get(key)
        if isinstance(value, list):
            return value

    raise ValueError(
        "Could not find a reagent record list in the JSON object."
    )


def first_value(record, keys):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def extract_traits(record):
    candidates = [
        record.get("traits"),
        record.get("effects"),
        record.get("alchemyTraits"),
        record.get("alchemy_traits"),
    ]

    for value in candidates:
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]

        if isinstance(value, dict):
            return [
                str(v).strip()
                for v in value.values()
                if str(v).strip()
            ]

        if isinstance(value, str) and value.strip():
            parts = re.split(r"\s*[|,;]\s*", value)
            return [x for x in parts if x]

    # Some exports store traits as trait1/trait2/trait3/trait4.
    traits = []
    for key in (
        "trait1", "trait2", "trait3", "trait4",
        "effect1", "effect2", "effect3", "effect4",
    ):
        value = record.get(key)
        if value not in (None, ""):
            traits.append(str(value).strip())

    return traits


def normalize_trait(trait, transitions):
    clean = trait.strip()
    folded = clean.casefold()

    for transition in transitions:
        old_traits = [
            x.casefold()
            for x in transition.get("old_traits", [])
        ]

        if folded in old_traits:
            return {
                "source_trait": clean,
                "canonical_trait": transition.get("new_trait"),
                "status": transition.get(
                    "status",
                    "consolidated",
                ),
                "update": transition.get("update"),
            }

    return {
        "source_trait": clean,
        "canonical_trait": clean,
        "status": "unchanged",
        "update": None,
    }


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Alchemy Reagent Normalizer")
    print("=" * 60)
    print()
    print("DATABASE: READ ONLY")
    print()

    source_path, source_data = load_source()

    with TRANSITIONS_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        transitions_data = json.load(handle)

    records = extract_records(source_data)
    trait_transitions = transitions_data.get(
        "alchemy_trait_transitions",
        [],
    )

    normalized = []
    seen_ids = set()
    duplicate_ids = []

    for record in records:
        if not isinstance(record, dict):
            continue

        name = first_value(
            record,
            ("name", "itemName", "reagentName"),
        )

        if not name:
            continue

        item_id = first_value(
            record,
            (
                "itemId",
                "itemID",
                "id",
                "item_id",
            ),
        )

        if item_id is not None:
            item_id = str(item_id)

        canonical_id = f"reagent:{slugify(name)}"

        if canonical_id in seen_ids:
            duplicate_ids.append(canonical_id)

        seen_ids.add(canonical_id)

        source_traits = extract_traits(record)

        traits = [
            normalize_trait(
                trait,
                trait_transitions,
            )
            for trait in source_traits
        ]

        normalized.append({
            "id": canonical_id,
            "name": name,
            "source_layer": "alchemy_reagents",
            "source_ids": {
                "itemId": item_id,
            },
            "traits": traits,
            "icon": first_value(
                record,
                ("icon", "itemIcon"),
            ),
            "description": first_value(
                record,
                ("description", "abilityDesc"),
            ),
            "update_51": {
                "is_existing_reagent": True,
            },
            "raw": record,
        })

    output = {
        "schema_version": 1,
        "source": str(source_path),
        "record_count": len(normalized),
        "duplicate_ids": sorted(set(duplicate_ids)),
        "trait_transition_count": sum(
            1
            for reagent in normalized
            for trait in reagent["traits"]
            if trait["status"] == "consolidated"
        ),
        "reagents": normalized,
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
            indent=2,
            ensure_ascii=False,
        )

    print("=" * 60)
    print(" NORMALIZATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Source:                  {source_path.name}")
    print(f"Source records:          {len(records)}")
    print(f"Reagents normalized:     {len(normalized)}")
    print(
        "Traits using Update 51: "
        f"{output['trait_transition_count']}"
    )
    print(f"Duplicate IDs:           {len(set(duplicate_ids))}")
    print()
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
