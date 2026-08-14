import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "eso.db"
)


def main():

    db = sqlite3.connect(
        DB_PATH
    )

    try:

        print("=" * 60)
        print(" RELATIONSHIP TABLE INSPECTION")
        print("=" * 60)
        print()

        rows = db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        tables = [
            row[0]
            for row in rows
        ]

        keywords = (
            "link",
            "relation",
            "skill",
            "source",
            "effect",
            "set",
            "champion",
        )

        relevant = [
            table
            for table in tables
            if any(
                keyword in table.casefold()
                for keyword in keywords
            )
        ]

        print("RELEVANT TABLES:")
        print()

        for table in relevant:
            print(
                f"  {table}"
            )

        print()

        for table in relevant:

            print("=" * 60)
            print(
                f"TABLE: {table}"
            )
            print("=" * 60)

            print()
            print("COLUMNS:")

            columns = db.execute(
                f"""
                PRAGMA table_info(
                    "{table}"
                )
                """
            ).fetchall()

            for column in columns:

                print(
                    f"  {column}"
                )

            print()
            print("FOREIGN KEYS:")

            foreign_keys = db.execute(
                f"""
                PRAGMA foreign_key_list(
                    "{table}"
                )
                """
            ).fetchall()

            if foreign_keys:

                for fk in foreign_keys:
                    print(
                        f"  {fk}"
                    )

            else:

                print(
                    "  None"
                )

            print()
            print("INDEXES:")

            indexes = db.execute(
                f"""
                PRAGMA index_list(
                    "{table}"
                )
                """
            ).fetchall()

            if indexes:

                for index in indexes:
                    print(
                        f"  {index}"
                    )

            else:

                print(
                    "  None"
                )

            print()

            count = db.execute(
                f"""
                SELECT COUNT(*)
                FROM "{table}"
                """
            ).fetchone()[0]

            print(
                f"ROW COUNT: {count}"
            )

            print()

    finally:

        db.close()


if __name__ == "__main__":
    main()