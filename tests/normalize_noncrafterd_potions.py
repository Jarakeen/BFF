import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "eso.db"
SOURCE_PATH = ROOT / "data" / "raw" / "noncrafted_potions.json"
OUTPUT_PATH = ROOT / "data" / "processed" / "noncrafted_potions_normalized.json"


def strip_color_codes(text):
    return re.sub(r"\|c[0-9a-fA-F]{6}|\|r", "", text or "")


def slugify(value):
    value = str(value or "").casefold().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def parse_number(value):
    if value is None:
        return None

    value = str(value).replace(",", "").strip()

    if "-" in value:
        parts = value.split("-", 1)
        try:
            return {
                "min": float(parts[0]),
                "max": float(parts[1]),
            }
        except ValueError:
            return None

    try:
        return {"value": float(value)}
    except ValueError:
        return None


def parse_restore_effects(description):
    results = []

    for line in strip_color_codes(description).splitlines():
        clean = line.strip()

        match = re.search(
            r"Restore\s+([0-9,]+(?:-[0-9,]+)?)\s+"
            r"(Health|Magicka|Stamina)"
            r"(?:\s+and\s+(Magicka|Stamina))?"
            r"(?:\s+and\s+(Magicka|Stamina))?"
            r"\s+immediately",
            clean,
            re.IGNORECASE,
        )

        if not match:
            continue

        resources = [match.group(2)]
        if match.group(3):
            resources.append(match.group(3))
        if match.group(4):
            resources.append(match.group(4))

        results.append({
            "resources": [x.casefold() for x in resources],
            "amount": parse_number(match.group(1)),
            "raw": clean,
        })

    return results


def parse_durations(description):
    clean = strip_color_codes(description)

    return [
        parse_number(match.group(1))
        for match in re.finditer(
            r"for\s+([0-9.]+(?:-[0-9.]+)?)\s+seconds",
            clean,
            re.IGNORECASE,
        )
    ]


def load_canonical_effects():
    db = sqlite3.connect(DB_PATH)

    buffs = db.execute(
        """
        SELECT id, name
        FROM entity
        WHERE entity_type = 'buff'
        """
    ).fetchall()

    debuffs = db.execute(
        """
        SELECT id, name
        FROM entity
        WHERE entity_type = 'debuff'
        """
    ).fetchall()

    status_effects = db.execute(
        """
        SELECT id, name
        FROM entity
        WHERE entity_type = 'status_effect'
        """
    ).fetchall()

    db.close()

    return {
        "buff": buffs,
        "debuff": debuffs,
        "status_effect": status_effects,
    }


def match_named_effects(description, canonical):
    clean = strip_color_codes(description)
    found = []

    for entity_type, records in canonical.items():
        for entity_id, name in records:
            pattern = re.compile(
                r"\b" + re.escape(name) + r"\b",
                re.IGNORECASE,
            )

            match = pattern.search(clean)

            if match:
                found.append({
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "name": name,
                    "match_method": "explicit_name",
                    "raw_match": match.group(0),
                })

    return found


def add_semantic_alias(
    found,
    canonical,
    phrase,
    entity_type,
    canonical_name,
):
    folded = canonical_name.casefold()

    for entity_id, name in canonical.get(
        entity_type,
        [],
    ):
        if name.casefold() == folded:
            if entity_id not in {
                item["entity_id"]
                for item in found
            }:
                found.append({
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "name": name,
                    "match_method": "semantic_alias",
                    "raw_match": phrase,
                })
            return


# Non-crafted potion descriptions sometimes use stat language
# instead of the canonical buff name. These aliases describe the
# historical source data. Update 51 transitions are handled
# separately by update_51_effect_transitions.json.
SEMANTIC_ALIASES = {
    "spell damage": ("buff", "Major Sorcery"),
    "weapon damage": ("buff", "Major Brutality"),
    "spell critical": ("buff", "Major Prophecy"),
    "weapon critical": ("buff", "Major Savagery"),
    "health recovery": ("buff", "Major Fortitude"),
    "stamina recovery": ("buff", "Major Endurance"),
    "stamina regeneration": ("buff", "Major Endurance"),
    "magicka recovery": ("buff", "Major Intellect"),
}


def parse_effects(description, canonical):
    clean = strip_color_codes(description)
    found = match_named_effects(clean, canonical)

    for phrase, (
        entity_type,
        canonical_name,
    ) in SEMANTIC_ALIASES.items():
        if re.search(
            r"\b" + re.escape(phrase) + r"\b",
            clean,
            re.IGNORECASE,
        ):
            add_semantic_alias(
                found,
                canonical,
                phrase,
                entity_type,
                canonical_name,
            )

    return found


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Non-Crafted Potion Normalizer")
    print("=" * 60)
    print()
    print("DATABASE: READ ONLY")
    print()

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        source = json.load(handle)

    records = source.get("minedItemSummary", [])

    if not isinstance(records, list):
        raise ValueError(
            "noncrafted_potions.json does not contain "
            "a minedItemSummary list."
        )

    canonical = load_canonical_effects()

    normalized = []
    seen_item_ids = set()
    duplicate_item_ids = set()

    for record in records:
        item_id = str(record.get("itemId", "")).strip()
        name = str(record.get("name", "")).strip()

        if not item_id or not name:
            continue

        if item_id in seen_item_ids:
            duplicate_item_ids.add(item_id)

        seen_item_ids.add(item_id)

        description = record.get(
            "abilityDesc",
            "",
        ) or ""

        effects = parse_effects(
            description,
            canonical,
        )

        normalized.append({
            "id": f"potion:{slugify(name)}",
            "name": name,
            "source_layer": "noncrafted_potions",
            "source_ids": {
                "itemId": item_id,
            },
            "icon": record.get("icon"),
            "level": record.get("level"),
            "quality": record.get("quality"),
            "craft_type": record.get("craftType"),
            "special_type": record.get("specialType"),
            "is_consumable": record.get("isConsumable"),
            "ability_cooldown_ms": (
                int(record["abilityCooldown"])
                if str(
                    record.get("abilityCooldown", "")
                ).isdigit()
                else None
            ),
            "ability_description_raw": description,
            "restores": parse_restore_effects(
                description
            ),
            "effects": effects,
            "durations_seconds": parse_durations(
                description
            ),
            "raw": record,
        })

    output = {
        "schema_version": 1,
        "source": str(SOURCE_PATH),
        "record_count": len(normalized),
        "duplicate_item_ids": sorted(
            duplicate_item_ids
        ),
        "canonical_entity_counts": {
            key: len(value)
            for key, value in canonical.items()
        },
        "potions": normalized,
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

    effect_count = sum(
        len(p["effects"])
        for p in normalized
    )

    restore_count = sum(
        len(p["restores"])
        for p in normalized
    )

    print("=" * 60)
    print(" NORMALIZATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Source records:           {len(records)}")
    print(f"Potions normalized:       {len(normalized)}")
    print(f"Effect relationships:     {effect_count}")
    print(f"Restore effects:          {restore_count}")
    print(
        f"Duplicate item IDs:       "
        f"{len(duplicate_item_ids)}"
    )
    print()
    print("CANONICAL EFFECTS AVAILABLE:")
    for key, value in canonical.items():
        print(f"  {key}: {len(value)}")
    print()
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
