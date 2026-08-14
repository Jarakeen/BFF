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

        print("ALL ENTITY TYPES:")
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
                f"  {entity_type:<20}"
                f"{count}"
            )

        print()
        print("BUFFS:")
        print()

        rows = db.execute(
            """
            SELECT
                id,
                name
            FROM entity
            WHERE entity_type = 'buff'
            ORDER BY name
            """
        ).fetchall()

        for row in rows:
            print(
                f"  {row}"
            )

        print()
        print("EFFECTS:")
        print()

        rows = db.execute(
            """
            SELECT
                id,
                name
            FROM entity
            WHERE entity_type = 'effect'
            ORDER BY name
            """
        ).fetchall()

        for row in rows:
            print(
                f"  {row}"
            )
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
        
        for row in rows:
            print(
                f"  {row}"
            )

    finally:
        db.close()


    if __name__ == "__main__":
        main()

        print()
    print("EFFECT ENTITY CHECK:")
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
    print("CANONICAL SOURCE COUNT BY SOURCE:")
    print()

   