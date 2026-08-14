import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "eso.db"
SOURCE_PATH = ROOT / "data" / "processed" / "noncrafted_potions_normalized.json"
REPORT_PATH = ROOT / "data" / "processed" / "noncrafted_potion_effect_import_report.json"


def load_source():
    with SOURCE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    potions = data.get("potions")
    if not isinstance(potions, list):
        raise ValueError("Normalized source does not contain 'potions'.")

    return potions


def canonical_effect_name(db, entity_id):
    row = db.execute(
        """
        SELECT entity_type, name
        FROM entity
        WHERE id = ?
        """,
        (entity_id,),
    ).fetchone()

    if row is None:
        return None, None

    return row[0], row[1]


def find_effects(db, effect_name):
    return db.execute(
        """
        SELECT id, name, category
        FROM effect
        WHERE lower(name) = lower(?)
        """,
        (effect_name,),
    ).fetchall()


def find_variants(db, effect_id):
    return db.execute(
        """
        SELECT id, effect_id, type, description, icon, raw_json
        FROM effect_variant
        WHERE effect_id = ?
        ORDER BY id
        """,
        (effect_id,),
    ).fetchall()


def find_potion_source(db, variant_id, source_name):
    return db.execute(
        """
        SELECT id
        FROM effect_source
        WHERE effect_variant_id = ?
          AND source_type = 'Potions'
          AND lower(source_name) = lower(?)
        """,
        (variant_id, source_name),
    ).fetchone()


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Non-Crafted Potion Effect Relationship Importer")
    print("=" * 60)
    print()
    print("DATABASE OPERATION:")
    print("  effect")
    print("  effect_variant")
    print("  effect_source")
    print()
    print("TRANSACTIONAL: YES")
    print("NO entity changes")
    print()

    potions = load_source()

    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    try:
        required_tables = {
            "effect",
            "effect_variant",
            "effect_source",
            "entity",
        }

        existing_tables = {
            row[0]
            for row in db.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        missing = required_tables - existing_tables
        if missing:
            raise RuntimeError(
                "Missing required tables: "
                + ", ".join(sorted(missing))
            )

        db.execute("BEGIN")

        source_inserted = 0
        source_existing = 0
        variant_created = 0
        effect_matches = 0
        effect_unmatched = 0
        ambiguous = 0
        errors = []

        for potion in potions:
            potion_name = potion["name"]

            for normalized_effect in potion.get("effects", []):
                entity_id = normalized_effect.get("entity_id")
                entity_type = normalized_effect.get("entity_type")
                effect_display_name = normalized_effect.get("name")

                if not entity_id or not entity_type:
                    errors.append(
                        f"{potion_name}: malformed normalized effect"
                    )
                    continue

                actual_type, canonical_name = canonical_effect_name(
                    db,
                    entity_id,
                )

                if actual_type != entity_type:
                    errors.append(
                        f"{potion_name}: canonical entity missing or "
                        f"type mismatch: {entity_id}"
                    )
                    continue

                if not canonical_name:
                    errors.append(
                        f"{potion_name}: canonical effect name missing: "
                        f"{entity_id}"
                    )
                    continue

                effect_name = effect_display_name or canonical_name

                matches = find_effects(
                    db,
                    effect_name,
                )

                if len(matches) == 0:
                    effect_unmatched += 1
                    errors.append(
                        f"{potion_name}: no effect row found for "
                        f"{effect_name!r}"
                    )
                    continue

                if len(matches) > 1:
                    ambiguous += 1
                    errors.append(
                        f"{potion_name}: ambiguous effect row for "
                        f"{effect_name!r}: "
                        + ", ".join(str(row[0]) for row in matches)
                    )
                    continue

                effect_id, db_effect_name, category = matches[0]
                effect_matches += 1

                variants = find_variants(
                    db,
                    effect_id,
                )

                if not variants:
                    # We create the minimum required variant because
                    # effect_source cannot exist without one. The source
                    # is still tied to the canonical effect row.
                    db.execute(
                        """
                        INSERT INTO effect_variant (
                            effect_id,
                            type,
                            description,
                            icon,
                            raw_json
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            effect_id,
                            "potion",
                            normalized_effect.get(
                                "raw_match",
                                canonical_name,
                            ),
                            None,
                            json.dumps(
                                normalized_effect,
                                ensure_ascii=False,
                            ),
                        ),
                    )

                    variant_id = db.execute(
                        "SELECT last_insert_rowid()"
                    ).fetchone()[0]

                    variant_created += 1
                elif len(variants) == 1:
                    variant_id = variants[0][0]
                else:
                    # Prefer an existing potion variant.
                    potion_variants = [
                        row for row in variants
                        if str(row[2] or "").casefold() == "potion"
                    ]

                    if len(potion_variants) == 1:
                        variant_id = potion_variants[0][0]
                    elif len(potion_variants) > 1:
                        ambiguous += 1
                        errors.append(
                            f"{potion_name}: multiple potion variants "
                            f"for effect {effect_name!r}"
                        )
                        continue
                    else:
                        # Do not guess between unrelated variants.
                        ambiguous += 1
                        errors.append(
                            f"{potion_name}: multiple effect variants "
                            f"and none identified as potion for "
                            f"{effect_name!r}"
                        )
                        continue

                # Existing Potions source naming convention in this DB
                # is "<Effect> <Effect> <Potion>" for the mined potion
                # effect sources. Reuse it when present; otherwise create
                # the same convention for this normalized relationship.
                source_name = (
                    f"{canonical_name} "
                    f"{canonical_name} "
                    f"{potion_name}"
                )

                existing = find_potion_source(
                    db,
                    variant_id,
                    source_name,
                )

                if existing:
                    source_existing += 1
                    continue

                raw_text = normalized_effect.get(
                    "raw_match"
                ) or potion.get(
                    "ability_description_raw",
                    "",
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
                        normalized_effect.get(
                            "condition"
                        ),
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
                "effect_matches": effect_matches,
                "effect_unmatched": effect_unmatched,
                "variants_created": variant_created,
                "sources_inserted": source_inserted,
                "sources_existing": source_existing,
                "ambiguous": ambiguous,
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
            print(f"Effect matches:       {effect_matches}")
            print(f"Effect unmatched:     {effect_unmatched}")
            print(f"Variants created:     {variant_created}")
            print(f"Sources inserted:     {source_inserted}")
            print(f"Sources existing:     {source_existing}")
            print(f"Ambiguous:            {ambiguous}")
            print(f"Errors:               {len(errors)}")
            print()
            print("No database changes were committed.")
            print()
            for error in errors[:100]:
                print(f"  {error}")

            raise RuntimeError(
                "Non-crafted potion effect import failed."
            )

        db.commit()

        report = {
            "status": "complete",
            "database_changes_committed": True,
            "potions_processed": len(potions),
            "effect_matches": effect_matches,
            "effect_unmatched": effect_unmatched,
            "variants_created": variant_created,
            "sources_inserted": source_inserted,
            "sources_existing": source_existing,
            "ambiguous": ambiguous,
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
        print(" EFFECT IMPORT COMPLETE")
        print("=" * 60)
        print()
        print(f"Potions processed:      {len(potions)}")
        print(f"Effect matches:         {effect_matches}")
        print(f"Variants created:       {variant_created}")
        print(f"Sources inserted:       {source_inserted}")
        print(f"Sources already there:  {source_existing}")
        print("Ambiguous:              0")
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
