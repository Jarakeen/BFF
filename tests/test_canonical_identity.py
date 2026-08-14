import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "eso.db"
)


TEST_ENTITIES = [
    (
        "ability:wall_of_elements",
        "ability",
        "Wall of Elements",
        "wall_of_elements",
    ),
    (
        "debuff:major_breach",
        "debuff",
        "Major Breach",
        "major_breach",
    ),
    (
        "gear_set:puncturing_remedy",
        "gear_set",
        "Puncturing Remedy",
        "puncturing_remedy",
    ),
]


TEST_SOURCES = [
    (
        "debuff:major_breach",
        "ESO",
        "effect",
        "100988",
        "Major Breach",
    ),
    (
        "debuff:major_breach",
        "ESO",
        "effect",
        "103628",
        "Major Breach",
    ),
    (
        "debuff:major_breach",
        "ESO",
        "effect",
        "108951",
        "Major Breach",
    ),
]


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Canonical Identity Test")
    print("=" * 60)

    db = sqlite3.connect(DB_PATH)

    try:
        db.execute("PRAGMA foreign_keys = ON")

        print()
        print("Inserting canonical entities...")

        for entity in TEST_ENTITIES:
            db.execute(
                """
                INSERT INTO entity (
                    id,
                    entity_type,
                    name,
                    slug
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id)
                DO UPDATE SET
                    entity_type = excluded.entity_type,
                    name = excluded.name,
                    slug = excluded.slug
                """,
                entity,
            )

        print("  Entities inserted: 3")

        print()
        print("Inserting source mappings...")

        for source in TEST_SOURCES:
            db.execute(
                """
                INSERT INTO entity_source (
                    entity_id,
                    source,
                    source_entity_type,
                    source_id,
                    source_name
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(
                    entity_id,
                    source,
                    source_entity_type,
                    source_id
                )
                DO UPDATE SET
                    source_name = excluded.source_name
                """,
                source,
            )

        db.commit()

        print("  Source mappings inserted: 3")

        print()
        print("Checking canonical entities...")

        rows = db.execute(
            """
            SELECT
                id,
                entity_type,
                name,
                slug
            FROM entity
            WHERE id IN (
                'ability:wall_of_elements',
                'debuff:major_breach',
                'gear_set:puncturing_remedy'
            )
            ORDER BY id
            """
        ).fetchall()

        for row in rows:
            print(f"  {row}")

        print()
        print("Checking Major Breach source IDs...")

        rows = db.execute(
            """
            SELECT
                entity_id,
                source,
                source_entity_type,
                source_id,
                source_name
            FROM entity_source
            WHERE entity_id = 'debuff:major_breach'
            ORDER BY source_id
            """
        ).fetchall()

        for row in rows:
            print(f"  {row}")

        if len(rows) != 3:
            raise RuntimeError(
                "Expected exactly 3 Major Breach "
                "source mappings."
            )

        print()
        print("Testing duplicate protection...")

        db.execute(
            """
            INSERT INTO entity_source (
                entity_id,
                source,
                source_entity_type,
                source_id,
                source_name
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(
                entity_id,
                source,
                source_entity_type,
                source_id
            )
            DO NOTHING
            """,
            (
                "debuff:major_breach",
                "ESO",
                "effect",
                "100988",
                "Major Breach",
            ),
        )

        db.commit()

        count = db.execute(
            """
            SELECT COUNT(*)
            FROM entity_source
            WHERE entity_id = 'debuff:major_breach'
            """
        ).fetchone()[0]

        if count != 3:
            raise RuntimeError(
                f"Duplicate protection failed. "
                f"Expected 3, got {count}."
            )

        print("  PASS: duplicate source ID ignored")

        print()
        print("=" * 60)
        print(" CANONICAL IDENTITY TEST PASSED")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()