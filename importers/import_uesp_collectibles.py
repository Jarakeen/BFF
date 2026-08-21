from __future__ import annotations

import json
import sqlite3
from pathlib import Path


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "data" / "eso.db"
SOURCE_PATH = ROOT / "data" / "processed" / "uesp_collectibles.json"


# ============================================================
# Helpers
# ============================================================

def get_columns(
    db: sqlite3.Connection,
    table: str,
) -> set[str]:

    return {
        row[1]
        for row in db.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }


def load_source() -> list[dict]:

    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            f"UESP collectible source not found:\n"
            f"{SOURCE_PATH}"
        )

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:

        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(
            "uesp_collectibles.json must contain "
            "a JSON object."
        )

    collectibles = data.get(
        "collectibles"
    )

    if not isinstance(
        collectibles,
        list,
    ):
        raise ValueError(
            "uesp_collectibles.json is missing "
            "the collectibles list."
        )

    return [
        item
        for item in collectibles
        if isinstance(item, dict)
    ]


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" UESP Collectibles Importer")
    print("=" * 60)
    print()

    print(
        f"Source:   {SOURCE_PATH}"
    )

    print(
        f"Database: {DB_PATH}"
    )

    print()

    collectibles = load_source()

    print(
        f"Source records: "
        f"{len(collectibles):,}"
    )

    print()

    db = sqlite3.connect(
        DB_PATH
    )

    db.row_factory = sqlite3.Row

    db.execute(
        "PRAGMA foreign_keys = ON"
    )

    try:

        # ----------------------------------------------------
        # Validate schema
        # ----------------------------------------------------

        entity_columns = get_columns(
            db,
            "entity",
        )

        entity_source_columns = get_columns(
            db,
            "entity_source",
        )

        required_entity = {
            "id",
            "entity_type",
            "name",
            "slug",
        }

        required_source = {
            "id",
            "entity_id",
            "source",
            "source_entity_type",
            "source_id",
            "source_name",
            "raw_json",
        }

        missing_entity = (
            required_entity
            - entity_columns
        )

        missing_source = (
            required_source
            - entity_source_columns
        )

        if missing_entity:

            raise RuntimeError(
                "entity is missing columns: "
                + ", ".join(
                    sorted(missing_entity)
                )
            )

        if missing_source:

            raise RuntimeError(
                "entity_source is missing columns: "
                + ", ".join(
                    sorted(missing_source)
                )
            )

        # ----------------------------------------------------
        # Begin transaction
        # ----------------------------------------------------

        db.execute("BEGIN")

        entities_created = 0
        entities_existing = 0

        mappings_inserted = 0
        mappings_existing = 0

        errors: list[str] = []

        # ----------------------------------------------------
        # Import collectibles
        # ----------------------------------------------------

        for item in collectibles:

            fields = item.get(
                "fields"
            )

            if not isinstance(
                fields,
                dict,
            ):
                errors.append(
                    "Record is missing fields object."
                )
                continue

            # ------------------------------------------------
            # Source identity
            # ------------------------------------------------

            source_id = str(
                item.get(
                    "collectible_id",
                    fields.get("id", ""),
                )
            ).strip()

            name = str(
                fields.get(
                    "name",
                    "",
                )
            ).strip()

            if not source_id:

                errors.append(
                    "Collectible missing ID."
                )

                continue

            if not name:

                errors.append(
                    f"Collectible {source_id}: "
                    f"missing name."
                )

                continue

            # ------------------------------------------------
            # Canonical identity
            # ------------------------------------------------

            entity_id = (
                f"collectible:{source_id}"
            )

            slug = f"collectible-{source_id}"

            # ------------------------------------------------
            # Canonical entity
            # ------------------------------------------------

            existing = db.execute(
                """
                SELECT
                    id,
                    entity_type,
                    name,
                    slug
                FROM entity
                WHERE id = ?
                """,
                (entity_id,),
            ).fetchone()

            if existing is None:

                db.execute(
                    """
                    INSERT INTO entity (
                        id,
                        entity_type,
                        name,
                        slug
                    )
                    VALUES (
                        ?,
                        'collectible',
                        ?,
                        ?
                    )
                    """,
                    (
                        entity_id,
                        name,
                        slug,
                    ),
                )

                entities_created += 1

            else:

                if (
                    existing["entity_type"]
                    != "collectible"
                ):

                    errors.append(
                        f"{name}: canonical entity "
                        f"{entity_id!r} already exists "
                        f"as "
                        f"{existing['entity_type']!r}"
                    )

                    continue

                entities_existing += 1

            # ------------------------------------------------
            # Full UESP source record
            # ------------------------------------------------

            raw_json = json.dumps(
                item,
                ensure_ascii=False,
            )

            existing_source = db.execute(
                """
                SELECT id
                FROM entity_source
                WHERE entity_id = ?
                  AND source = 'UESP'
                  AND source_entity_type = 'collectible'
                  AND source_id = ?
                """,
                (
                    entity_id,
                    source_id,
                ),
            ).fetchone()

            if existing_source is None:

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
                        'UESP',
                        'collectible',
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

            else:

                mappings_existing += 1

        # ----------------------------------------------------
        # Abort on source errors
        # ----------------------------------------------------

        if errors:

            print()
            print(
                f"Errors encountered: "
                f"{len(errors):,}"
            )

            for error in errors[:25]:

                print(
                    "  ERROR:",
                    error,
                )

            if len(errors) > 25:

                print(
                    f"  ... and "
                    f"{len(errors) - 25:,} more"
                )

            raise RuntimeError(
                "Collectible import encountered "
                "validation errors."
            )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        db.commit()

        # ----------------------------------------------------
        # Verify
        # ----------------------------------------------------

        entity_count = db.execute(
            """
            SELECT COUNT(*)
            FROM entity
            WHERE entity_type = 'collectible'
            """
        ).fetchone()[0]

        source_count = db.execute(
            """
            SELECT COUNT(*)
            FROM entity_source
            WHERE source = 'UESP'
              AND source_entity_type = 'collectible'
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Final report
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print(" UESP Collectibles Import Complete")
        print("=" * 60)
        print()

        print(
            f"Source records:        "
            f"{len(collectibles):,}"
        )

        print(
            f"Entities created:      "
            f"{entities_created:,}"
        )

        print(
            f"Entities existing:     "
            f"{entities_existing:,}"
        )

        print(
            f"UESP mappings added:   "
            f"{mappings_inserted:,}"
        )

        print(
            f"UESP mappings existing:"
            f"{mappings_existing:,}"
        )

        print()

        print(
            f"DB collectible entities:"
            f" {entity_count:,}"
        )

        print(
            f"DB collectible mappings:"
            f" {source_count:,}"
        )

        print()

        # ----------------------------------------------------
        # Integrity check
        # ----------------------------------------------------

        if entity_count != len(collectibles):

            print(
                "WARNING: DB entity count does not "
                "match source record count."
            )

        if source_count != len(collectibles):

            print(
                "WARNING: DB mapping count does not "
                "match source record count."
            )

        print(
            "STATUS: IMPORT COMPLETE"
        )

    except Exception:

        db.rollback()

        print()
        print(
            "Collectible import rolled back."
        )

        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()