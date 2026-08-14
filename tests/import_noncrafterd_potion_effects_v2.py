import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "eso.db"
SOURCE_PATH = ROOT / "data" / "processed" / "noncrafted_potions_normalized.json"
REPORT_PATH = ROOT / "data" / "processed" / "noncrafted_potion_effect_import_v2_report.json"


# The canonical entity layer uses names such as "Major Fortitude",
# while the raw effect layer uses the underlying effect name "Fortitude".
# Keep that distinction explicit here.
BUFF_TO_EFFECT = {
    "Major Fortitude": "Fortitude",
    "Minor Fortitude": "Fortitude",
    "Major Intellect": "Intellect",
    "Minor Intellect": "Intellect",
    "Major Endurance": "Endurance",
    "Minor Endurance": "Endurance",
    "Major Brutality": "Brutality",
    "Minor Brutality": "Brutality",
    "Major Savagery": "Savagery",
    "Minor Savagery": "Savagery",
    "Major Prophecy": "Prophecy",
    "Minor Prophecy": "Prophecy",
    "Major Sorcery": "Sorcery",
    "Minor Sorcery": "Sorcery",
    "Major Expedition": "Expedition",
    "Minor Expedition": "Expedition",
    "Major Heroism": "Heroism",
    "Minor Heroism": "Heroism",
    "Major Protection": "Protection",
    "Minor Protection": "Protection",
    "Major Resolve": "Resolve",
    "Minor Resolve": "Resolve",
    "Major Evasion": "Evasion",
    "Minor Evasion": "Evasion",
    "Major Mending": "Mending",
    "Minor Mending": "Mending",
    "Major Vitality": "Vitality",
    "Minor Vitality": "Vitality",
    "Major Force": "Force",
    "Minor Force": "Force",
}


def load_source():
    with SOURCE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    potions = data.get("potions")

    if not isinstance(potions, list):
        raise ValueError(
            "Normalized source does not contain 'potions'."
        )

    return potions


def get_effect(db, effect_name):
    rows = db.execute(
        """
        SELECT id, name, category
        FROM effect
        WHERE lower(name) = lower(?)
        """,
        (effect_name,),
    ).fetchall()

    if len(rows) == 1:
        return rows[0]

    if len(rows) == 0:
        return None

    raise RuntimeError(
        f"Ambiguous effect name {effect_name!r}: "
        + ", ".join(str(row[0]) for row in rows)
    )


def get_variants(db, effect_id):
    return db.execute(
        """
        SELECT id, effect_id, type, description, icon, raw_json
        FROM effect_variant
        WHERE effect_id = ?
        ORDER BY id
        """,
        (effect_id,),
    ).fetchall()


def choose_potion_variant(db, effect_id):
    variants = get_variants(db, effect_id)

    if not variants:
        return None, "missing"

    potion_variants = [
        row for row in variants
        if str(row[2] or "").casefold() == "potion"
    ]

    if len(potion_variants) == 1:
        return potion_variants[0], "existing_potion"

    if len(potion_variants) > 1:
        raise RuntimeError(
            f"Effect {effect_id} has multiple potion variants: "
            + ", ".join(str(row[0]) for row in potion_variants)
        )

    # Existing database variants may not label the type "potion".
    # Do not guess yet. The caller can inspect the source records.
    return None, "no_potion_variant"


def potion_source_name(effect_name, potion_name):
    return (
        f"{effect_name} "
        f"{effect_name} "
        f"{potion_name}"
    )


def source_exists(
    db,
    variant_id,
    source_name,
):
    return db.execute(
        """
        SELECT id
        FROM effect_source
        WHERE effect_variant_id = ?
          AND source_type = 'Potions'
          AND lower(source_name) = lower(?)
        """,
        (
            variant_id,
            source_name,
        ),
    ).fetchone()


def resolve_effect_name(entity_type, entity_name):
    if entity_type == "buff":
        return BUFF_TO_EFFECT.get(
            entity_name,
            entity_name,
        )

    if entity_type == "debuff":
        # Current canonical debuff names generally map directly to
        # the raw effect name. This deliberately avoids inventing
        # Major/Minor conversions.
        return entity_name

    if entity_type == "status_effect":
        return entity_name

    return entity_name


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Non-Crafted Potion Effect Relationship Importer v2")
    print("=" * 60)
    print()
    print("DATABASE OPERATION:")
    print("  effect_source ONLY")
    print()
    print("DATABASE:")
    print("  entity/effect/effect_variant READ ONLY")
    print()
    print("TRANSACTIONAL: YES")
    print("NO NEW EFFECTS")
    print("NO NEW EFFECT VARIANTS")
    print("NO ENTITY CHANGES")
    print()

    potions = load_source()

    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    try:
        db.execute("BEGIN")

        source_inserted = 0
        source_existing = 0
        effect_resolved = 0
        variant_resolved = 0
        variant_missing = 0
        errors = []

        for potion in potions:
            potion_name = potion["name"]

            for normalized_effect in potion.get("effects", []):
                entity_id = normalized_effect.get("entity_id")
                entity_type = normalized_effect.get("entity_type")
                canonical_name = normalized_effect.get("name")

                if not entity_id or not entity_type:
                    errors.append(
                        f"{potion_name}: malformed normalized effect"
                    )
                    continue

                entity_row = db.execute(
                    """
                    SELECT entity_type, name
                    FROM entity
                    WHERE id = ?
                    """,
                    (entity_id,),
                ).fetchone()

                if entity_row is None:
                    errors.append(
                        f"{potion_name}: canonical entity missing: "
                        f"{entity_id}"
                    )
                    continue

                actual_type, actual_name = entity_row

                if actual_type != entity_type:
                    errors.append(
                        f"{potion_name}: entity type mismatch for "
                        f"{entity_id}: expected {entity_type}, "
                        f"found {actual_type}"
                    )
                    continue

                canonical_name = actual_name or canonical_name

                raw_effect_name = resolve_effect_name(
                    entity_type,
                    canonical_name,
                )

                effect_row = get_effect(
                    db,
                    raw_effect_name,
                )

                if effect_row is None:
                    errors.append(
                        f"{potion_name}: raw effect not found for "
                        f"{canonical_name!r} -> "
                        f"{raw_effect_name!r}"
                    )
                    continue

                effect_id, effect_name, category = effect_row
                effect_resolved += 1

                variant, variant_status = choose_potion_variant(
                    db,
                    effect_id,
                )

                if variant is None:
                    if variant_status == "missing":
                        variant_missing += 1
                        errors.append(
                            f"{potion_name}: effect {effect_name!r} "
                            f"has no effect_variant"
                        )
                    else:
                        errors.append(
                            f"{potion_name}: effect {effect_name!r} "
                            f"has no uniquely identified potion "
                            f"variant"
                        )
                    continue

                variant_id = variant[0]
                variant_resolved += 1

                source_name = potion_source_name(
                    effect_name,
                    potion_name,
                )

                existing = source_exists(
                    db,
                    variant_id,
                    source_name,
                )

                if existing:
                    source_existing += 1
                    continue

                raw_text = (
                    normalized_effect.get("raw_match")
                    or potion.get(
                        "ability_description_raw",
                        "",
                    )
                )

                db.execute(
                    """
                    INSERT INTO effect_source (
                        effect_variant_id,
                        source_type,
                        source_name,
                        condition,
                        raw_text
                    )
                    VALUES (?, 'Potions', ?, ?, ?)
                    """,
                    (
                        variant_id,
                        source_name,
                        normalized_effect.get("condition"),
                        raw_text,
                    ),
                )

                source_inserted += 1

        if errors:
            db.rollback()

            report = {
                "status": "aborted",
                "database_changes_committed": False,
                "potions_processed": len(potions),
                "effect_resolved": effect_resolved,
                "variant_resolved": variant_resolved,
                "variant_missing": variant_missing,
                "sources_inserted": source_inserted,
                "sources_existing": source_existing,
                "errors": errors,
            }

            with REPORT_PATH.open(
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    report,
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )

            print("=" * 60)
            print(" IMPORT ABORTED")
            print("=" * 60)
            print()
            print(f"Effect resolved:       {effect_resolved}")
            print(f"Variant resolved:      {variant_resolved}")
            print(f"Variant missing:       {variant_missing}")
            print(f"Sources inserted:      {source_inserted}")
            print(f"Sources existing:      {source_existing}")
            print(f"Errors:                {len(errors)}")
            print()
            print("No database changes were committed.")
            print()
            for error in errors[:100]:
                print(f"  {error}")

            raise RuntimeError(
                "Non-crafted potion effect import v2 failed."
            )

        db.commit()

        report = {
            "status": "complete",
            "database_changes_committed": True,
            "potions_processed": len(potions),
            "effect_resolved": effect_resolved,
            "variant_resolved": variant_resolved,
            "variant_missing": variant_missing,
            "sources_inserted": source_inserted,
            "sources_existing": source_existing,
            "errors": [],
        }

        with REPORT_PATH.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                report,
                handle,
                indent=2,
                ensure_ascii=False,
            )

        print("=" * 60)
        print(" EFFECT IMPORT V2 COMPLETE")
        print("=" * 60)
        print()
        print(f"Potions processed:      {len(potions)}")
        print(f"Effects resolved:       {effect_resolved}")
        print(f"Variants resolved:      {variant_resolved}")
        print(f"Variants missing:       {variant_missing}")
        print(f"Sources inserted:       {source_inserted}")
        print(f"Sources already there:  {source_existing}")
        print("Errors:                 0")
        print()
        print("Database changes committed.")
        print(f"Report: {REPORT_PATH}")

    except Exception:
        if db.in_transaction:
            db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
