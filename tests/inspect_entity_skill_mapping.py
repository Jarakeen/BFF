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
        print(" ENTITY / SKILL MAPPING INSPECTION")
        print("=" * 60)
        print()

        tables = db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        for (table,) in tables:

            columns = db.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()

            column_names = {
                column[1]
                for column in columns
            }

            interesting = (
                "entity_id" in column_names
                or "skill_id" in column_names
                or "ability_id" in column_names
            )

            if not interesting:
                continue

            print("=" * 60)
            print(f"TABLE: {table}")
            print("=" * 60)

            print()
            print("COLUMNS:")

            for column in columns:
                print(f"  {column}")

            print()

            count = db.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            print(f"ROW COUNT: {count}")
            print()

    finally:

        db.close()


if __name__ == "__main__":
    main()
    