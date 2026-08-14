import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "eso.db"
)


def main():

    db = sqlite3.connect(DB_PATH)

    try:

        print("=" * 60)
        print(" CANONICAL EFFECT CHECK")
        print("=" * 60)

        print()
        print("ENTITY COUNTS:")
        print()

        rows = db.execute(
            """
            SELECT
                entity_type,
                COUNT(*)
            FROM entity
            GROUP BY entity_type
            ORDER BY entity_type
            """
        ).fetchall()

        for entity_type, count in rows:
            print(
                f"  {entity_type:<20}{count}"
            )

        print()
        print("SOURCE COUNTS:")
        print()

        rows = db.execute(
            """
            SELECT
                source,
                COUNT(*)
            FROM entity_source
            GROUP BY source
            ORDER BY source
            """
        ).fetchall()

        for source, count in rows:
            print(
                f"  {source:<25}{count}"
            )

        print()
        print("BUFF / DEBUFF ENTITIES:")
        print()

        rows = db.execute(
            """
            SELECT
                id,
                entity_type,
                name
            FROM entity
            WHERE entity_type IN (
                'buff',
                'debuff'
            )
            ORDER BY entity_type, name
            """
        ).fetchall()

        for row in rows:
            print(
                f"  {row}"
            )

        print()
        print("MAJOR BREACH:")
        print()

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
            ORDER BY source, source_id
            """
        ).fetchall()

        for row in rows:
            print(
                f"  {row}"
            )

        print()
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()