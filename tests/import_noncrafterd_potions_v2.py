import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "eso.db"
SOURCE_PATH = ROOT / "data" / "processed" / "noncrafted_potions_normalized.json"
REPORT_PATH = ROOT / "data" / "processed" / "noncrafted_potions_import_report.json"


def load_source():
    with SOURCE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    potions = data.get("potions")

    if not isinstance(potions, list):
        raise ValueError(
            "Normalized source does not contain a 'potions' list."
        )

    return potions


def get_columns(db, table):
    return {
        row[1]
        for row in db.execute(
            f"PRAGMA table_info({table})"
        )
    }


def find_existing_potion(db, entity_id, name):
    rows = db.execute(
        """
        SELECT id, entity_type, name, slug
        FROM entity
        WHERE id = ?
           OR (
                entity_type = 'potion'
                AND lower(name) = lower(?)
              )
        """,
        (entity_id, name),
    ).fetchall()

    if not rows:
        return None

    if len(rows) > 1:
        # Prefer exact canonical ID if it exists.
        for row in rows:
            if row[0] == entity_id:
                return row

        raise RuntimeError(
            f"Ambiguous existing potion entity for {name!r}"
        )

    return rows[0]


def source_mapping_exists(db, entity_id, source_id):
    return db.execute(
        """
        SELECT id
        FROM entity_source
        WHERE entity_id = ?
          AND source = 'ESO'
          AND source_entity_type = 'potion'
          AND source_id = ?
        """,
        (entity_id, source_id),
    ).fetchone()


def effect_source_matches(db, effect_id, potion_name):
    """
    Existing effect_source records use source_type='Potions'.
    This function checks whether the potion's normalized effect
    can be represented by an existing potion source.

    We do NOT create new effect/effect_variant/effect_source rows
    here. This importer is identity + source mapping only.
    """

    return db.execute(
        """
        SELECT es.id, es.effect_variant_id, ev.effect_id
        FROM effect_source es
        JOIN effect_variant ev
          ON ev.id = es.effect_variant_id
        WHERE es.source_type = 'Potions'
          AND (
                lower(es.source_name) = lower(?)
                OR lower(es.source_name) LIKE lower(?) 
              )
        """,
        (
            potion_name,
            f"%{potion_name}%",
        ),
    ).fetchall()


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Non-Crafted Potion Importer v2")
    print("=" * 60)
    print()
    print("DATABASE OPERATION:")
    print("  entity")
    print("  entity_source")
    print()
    print("EFFECT TABLES:")
    print("  READ ONLY")
    print()
    print("TRANSACTIONAL: YES")
    print("NO NEW EFFECTS WILL BE CREATED")
    print()

    potions = load_source()

    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    try:
        entity_columns = get_columns(db, "entity")
        source_columns = get_columns(db, "entity_source")

        required_entity = {
            "id",
            "entity_type",
            "name",
            "slug",
        }

        required_source = {
            "entity_id",
            "source",
            "source_entity_type",
            "source_id",
            "source_name",
            "raw_json",
        }

        missing = required_entity - entity_columns
        if missing:
            raise RuntimeError(
                "entity missing columns: "
                + ", ".join(sorted(missing))
            )

        missing = required_source - source_columns
        if missing:
            raise RuntimeError(
                "entity_source missing columns: "
                + ", ".join(sorted(missing))
            )

        # Confirm the existing effect architecture exists.
        for table in (
            "effect",
            "effect_variant",
            "effect_source",
        ):
            if not db.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type='table'
                  AND name=?
                """,
                (table,),
            ).fetchone():
                raise RuntimeError(
                    f"Required existing table missing: {table}"
                )

        db.execute("BEGIN")

        created = 0
        existing = 0
        mappings_inserted = 0
        mappings_existing = 0
        source_matches = 0
        source_unmatched = 0
        errors = []

        for potion in potions:
            entity_id = potion["id"]
            name = potion["name"]
            slug = entity_id.split(":", 1)[1]

            existing_row = find_existing_potion(
                db,
                entity_id,
                name,
            )

            if existing_row is None:
                db.execute(
                    """
                    INSERT INTO entity (
                        id,
                        entity_type,
                        name,
                        slug
                    )
                    VALUES (?, 'potion', ?, ?)
                    """,
                    (
                        entity_id,
                        name,
                        slug,
                    ),
                )
                created += 1

            else:
                if existing_row[1] != "potion":
                    errors.append(
                        f"{name}: existing entity has "
                        f"type {existing_row[1]!r}"
                    )
                    continue

                # If an old/noncanonical potion ID exists under the
                # same name, don't silently create a second identity.
                if existing_row[0] != entity_id:
                    errors.append(
                        f"{name}: existing potion identity is "
                        f"{existing_row[0]!r}, expected {entity_id!r}"
                    )
                    continue

                existing += 1

            source_id = str(
                potion.get("source_ids", {}).get(
                    "itemId",
                    "",
                )
            ).strip()

            if not source_id:
                errors.append(
                    f"{name}: missing ESO itemId"
                )
                continue

            raw_json = json.dumps(
                potion.get("raw", {}),
                ensure_ascii=False,
            )

            if source_mapping_exists(
                db,
                entity_id,
                source_id,
            ):
                mappings_existing += 1
            else:
                db.execute(
                    """
                    INSERT INTO entity_source (
                        entity_id,
                        source,
                        source_entity_type,
                        source_id,
                        source_name,
                        raw_json
                    )
                    VALUES (
                        ?,
                        'ESO',
                        'potion',
                        ?,
                        ?,
                        ?
                    )
                    """,
                    (
                        entity_id,
                        source_id,
                        name,
                        raw_json,
                    ),
                )
                mappings_inserted += 1

            # Validate that the existing potion effect layer is
            # present, but do not create or modify effect records.
            effects_for_potion = potion.get(
                "effects",
                [],
            )

            for effect in effects_for_potion:
                effect_id = effect.get("entity_id")
                effect_type = effect.get("entity_type")

                if not effect_id or not effect_type:
                    errors.append(
                        f"{name}: malformed normalized effect"
                    )
                    continue

                effect_exists = db.execute(
                    """
                    SELECT 1
                    FROM entity
                    WHERE id = ?
                      AND entity_type = ?
                    """,
                    (
                        effect_id,
                        effect_type,
                    ),
                ).fetchone()

                if effect_exists is None:
                    errors.append(
                        f"{name}: canonical "
                        f"{effect_type} entity missing: "
                        f"{effect_id}"
                    )
                    continue

                # The normalized potion effect is already resolved to
                # the canonical entity. Count the existing Potions
                # source layer only as validation metadata.
                matches = effect_source_matches(
                    db,
                    effect_id,
                    name,
                )

                if matches:
                    source_matches += 1
                else:
                    source_unmatched += 1

        if errors:
            db.rollback()

            report = {
                "status": "aborted",
                "database_changes_committed": False,
                "potions_processed": len(potions),
                "entities_created": created,
                "entities_existing": existing,
                "mappings_inserted": mappings_inserted,
                "mappings_existing": mappings_existing,
                "effect_source_matches": source_matches,
                "effect_source_unmatched": source_unmatched,
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
            print(f"Errors: {len(errors)}")
            print("No database changes were committed.")
            print()
            for error in errors:
                print(f"  {error}")

            raise RuntimeError(
                "Non-crafted potion import v2 failed."
            )

        db.commit()

        report = {
            "status": "complete",
            "database_changes_committed": True,
            "potions_processed": len(potions),
            "entities_created": created,
            "entities_existing": existing,
            "mappings_inserted": mappings_inserted,
            "mappings_existing": mappings_existing,
            "effect_source_matches": source_matches,
            "effect_source_unmatched": source_unmatched,
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
        print(" IMPORT COMPLETE")
        print("=" * 60)
        print()
        print(f"Potions processed:        {len(potions)}")
        print(f"Entities created:         {created}")
        print(f"Entities already present: {existing}")
        print(f"Mappings inserted:        {mappings_inserted}")
        print(f"Mappings already present: {mappings_existing}")
        print(f"Effect source matches:    {source_matches}")
        print(f"Effect source unmatched:  {source_unmatched}")
        print("Errors:                   0")
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
