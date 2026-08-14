import json
import re
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "eso.db"
SOURCE_PATH = BASE_DIR / "data" / "raw" / "noncrafted_potions.json"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "potions_normalized.json"


def strip_color_codes(text):
    return re.sub(r"\|c[0-9a-fA-F]{6}|\|r", "", text or "")


def slugify(value):
    value = (value or "").casefold().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def parse_number(value):
    if value is None:
        return None

    value = value.replace(",", "").strip()

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


def parse_restore_lines(description):
    results = []

    for line in description.splitlines():
        clean = strip_color_codes(line).strip()

        match = re.search(
            r"Restore\s+([0-9,]+(?:-[0-9,]+)?)\s+"
            r"(Health|Magicka|Stamina)(?:\s+and\s+"
            r"(Magicka|Stamina))?(?:\s+and\s+"
            r"(Magicka|Stamina))?\s+immediately",
            clean,
            re.IGNORECASE,
        )

        if not match:
            continue

        amount = parse_number(match.group(1))
        resources = [match.group(2)]

        if match.group(3):
            resources.append(match.group(3))

        if match.group(4):
            resources.append(match.group(4))

        results.append({
            "resources": [r.casefold() for r in resources],
            "amount": amount,
            "raw": clean,
        })

    return results


def parse_buff_names(description, canonical_buffs):
    """
    Match only against canonical buff names already present in
    the database. This prevents inventing potion-specific buff IDs.
    """

    clean = strip_color_codes(description)
    found = []

    for name, entity_id in canonical_buffs:
        pattern = re.compile(
            r"\b" + re.escape(name) + r"\b",
            re.IGNORECASE,
        )

        if pattern.search(clean):
            found.append({
                "entity_id": entity_id,
                "name": name,
            })

    return found


def parse_durations(description):
    clean = strip_color_codes(description)

    values = []

    for match in re.finditer(
        r"for\s+([0-9.]+(?:-[0-9.]+)?)\s+seconds",
        clean,
        re.IGNORECASE,
    ):
        values.append(parse_number(match.group(1)))

    return values


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Potion Normalizer / Relationship Parser")
    print("=" * 60)
    print()
    print("DATABASE: READ ONLY")
    print("OUTPUT: processed/potions_normalized.json")
    print()

    with SOURCE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    records = data.get("minedItemSummary", [])

    if not isinstance(records, list):
        raise ValueError(
            "Potion source does not contain minedItemSummary."
        )

    db = sqlite3.connect(DB_PATH)

    canonical_buffs = db.execute(
        """
        SELECT name, id
        FROM entity
        WHERE entity_type = 'buff'
        ORDER BY length(name) DESC, name
        """
    ).fetchall()

    db.close()

    normalized = []
    unresolved_buffs = []
    duplicate_item_ids = set()
    seen_item_ids = set()

    for record in records:
        item_id = str(record.get("itemId", "")).strip()
        name = record.get("name", "").strip()
        description = record.get("abilityDesc", "") or ""

        if not item_id or not name:
            continue

        if item_id in seen_item_ids:
            duplicate_item_ids.add(item_id)

        seen_item_ids.add(item_id)

        buffs = parse_buff_names(
            description,
            canonical_buffs,
        )

        parsed = {
            "id": f"potion:{slugify(name)}",
            "name": name,
            "source_layer": "potions",
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
                if str(record.get("abilityCooldown", "")).isdigit()
                else None
            ),
            "ability_description_raw": description,
            "restores": parse_restore_lines(description),
            "grants_buffs": buffs,
            "durations_seconds": parse_durations(description),
            "raw": record,
        }

        normalized.append(parsed)

        for buff in buffs:
            pass

        # Identify explicit "Grants" buff names that did not resolve.
        clean = strip_color_codes(description)

        for match in re.finditer(
            r"\bGrants(?:\s+you)?\s+(.+?)(?=\s+which|\s+that|\s+and\s+which|\s+for\s+|\n|$)",
            clean,
            re.IGNORECASE,
        ):
            candidate_text = match.group(1).strip()

            for candidate in re.split(
                r",\s*|\s+and\s+",
                candidate_text,
            ):
                candidate = candidate.strip(" .")

                if not candidate:
                    continue

                if not any(
                    b["name"].casefold() == candidate.casefold()
                    for b in buffs
                ):
                    unresolved_buffs.append({
                        "item_id": item_id,
                        "potion": name,
                        "candidate": candidate,
                        "description": clean,
                    })

    output = {
        "source": str(SOURCE_PATH),
        "record_count": len(normalized),
        "canonical_buff_count": len(canonical_buffs),
        "duplicate_item_ids": sorted(duplicate_item_ids),
        "unresolved_buff_mentions": unresolved_buffs,
        "potions": normalized,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(
            output,
            handle,
            indent=2,
            ensure_ascii=False,
        )

    buff_relationships = sum(
        len(p["grants_buffs"])
        for p in normalized
    )

    restore_relationships = sum(
        len(p["restores"])
        for p in normalized
    )

    print("=" * 60)
    print(" NORMALIZATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Source records:          {len(records)}")
    print(f"Potions normalized:      {len(normalized)}")
    print(f"Buff relationships:      {buff_relationships}")
    print(f"Restore effects:         {restore_relationships}")
    print(f"Unresolved buff mentions:{len(unresolved_buffs)}")
    print(f"Duplicate item IDs:      {len(duplicate_item_ids)}")
    print()
    print(f"Output: {OUTPUT_PATH}")

    if unresolved_buffs:
        print()
        print("UNRESOLVED BUFF MENTIONS:")
        for item in unresolved_buffs:
            print(
                f"  {item['potion']}: "
                f"{item['candidate']}"
            )


if __name__ == "__main__":
    main()
