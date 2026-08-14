from __future__ import annotations

import json
import sqlite3
from pathlib import Path


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "data" / "eso.db"
SOURCE_PATH = ROOT / "data" / "processed" / "foods.json"


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


def load_foods() -> list[dict]:

    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            f"Food source file not found:\n{SOURCE_PATH}"
        )

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:

        data = json.load(handle)

    if not isinstance(data, list):
        raise ValueError(
            "foods.json must contain a JSON list."
        )

    return [
        food
        for food in data
        if isinstance(food, dict)
        and food.get("id")
        and food.get("name")
    ]


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Food Importer")
    print("=" * 60)
    print()

    print(f"Source:   {SOURCE_PATH}")
    print(f"Database: {DB_PATH}")
    print()

    foods = load_foods()

    print(
        f"Food records loaded: {len(foods):,}"
    )

    db = sqlite3.connect(DB_PATH)

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
        # Import transaction
        # ----------------------------------------------------

        db.execute("BEGIN")

        created = 0
        existing = 0

        mappings_inserted = 0
        mappings_existing = 0

        errors: list[str] = []

        # ----------------------------------------------------
        # Import foods
        # ----------------------------------------------------

        for food in foods:

            entity_id = str(
                food["id"]
            ).strip()

            name = str(
                food["name"]
            ).strip()

            if not entity_id or not name:
                continue

            # Canonical slug is everything after food_
            slug = entity_id

            if slug.startswith("food_"):
                slug = slug[5:]

            # ------------------------------------------------
            # Canonical entity
            # ------------------------------------------------

            row = db.execute(
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

            if row is None:

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
                        'food',
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

                created += 1

            else:

                if row["entity_type"] != "food":

                    errors.append(
                        f"{name}: entity ID "
                        f"{entity_id!r} already exists "
                        f"as {row['entity_type']!r}"
                    )

                    continue

                existing += 1

            # ------------------------------------------------
            # ESO source mapping
            # ------------------------------------------------

            source_ids = (
                food.get("source_ids")
                or {}
            )

            source_id = str(
                source_ids.get(
                    "itemId",
                    "",
                )
            ).strip()

            if not source_id:
                errors.append(
                    f"{name}: missing ESO itemId"
                )
                continue

            existing_source = db.execute(
                """
                SELECT id
                FROM entity_source
                WHERE entity_id = ?
                  AND source = 'ESO'
                  AND source_entity_type = 'food'
                  AND source_id = ?
                """,
                (
                    entity_id,
                    source_id,
                ),
            ).fetchone()

            if existing_source is None:

                raw_json = json.dumps(
                    food,
                    ensure_ascii=False,
                )

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
                        'food',
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
        # Commit
        # ----------------------------------------------------

        if errors:

            print()
            print(
                f"Errors encountered: {len(errors):,}"
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
                "Food import encountered errors."
            )

        db.commit()

        # ----------------------------------------------------
        # Verify
        # ----------------------------------------------------

        entity_count = db.execute(
            """
            SELECT COUNT(*)
            FROM entity
            WHERE entity_type = 'food'
            """
        ).fetchone()[0]

        source_count = db.execute(
            """
            SELECT COUNT(*)
            FROM entity_source
            WHERE source = 'ESO'
              AND source_entity_type = 'food'
            """
        ).fetchone()[0]

        print()
        print("=" * 60)
        print(" Food Import Complete")
        print("=" * 60)
        print()

        print(
            f"Source records:       {len(foods):,}"
        )

        print(
            f"Entities created:     {created:,}"
        )

        print(
            f"Entities existing:    {existing:,}"
        )

        print(
            f"ESO mappings added:   {mappings_inserted:,}"
        )

        print(
            f"ESO mappings existing:{mappings_existing:,}"
        )

        print()

        print(
            f"DB food entities:     {entity_count:,}"
        )

        print(
            f"DB food mappings:     {source_count:,}"
        )

        print()

    except Exception:

        db.rollback()

        print()
        print(
            "Food import rolled back."
        )

        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()