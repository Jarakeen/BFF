from pathlib import Path
import sqlite3

DB_PATH = Path("data/eso.db")
SEARCH_ID = 47


def main():
    conn = sqlite3.connect(DB_PATH)

    try:
        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()

        print("=" * 80)
        print(f"SEARCHING FOR COLLECTIBLE ID: {SEARCH_ID}")
        print("=" * 80)

        matches = []

        for (table_name,) in tables:
            columns = conn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            for column in columns:
                column_name = column[1]
                column_type = (column[2] or "").upper()

                # Only search numeric-looking columns.
                if not any(
                    t in column_type
                    for t in ("INT", "REAL", "NUM", "DEC")
                ):
                    continue

                try:
                    count = conn.execute(
                        f'''
                        SELECT COUNT(*)
                        FROM "{table_name}"
                        WHERE "{column_name}" = ?
                        ''',
                        (SEARCH_ID,),
                    ).fetchone()[0]

                except sqlite3.Error:
                    continue

                if count:
                    matches.append(
                        (table_name, column_name, count)
                    )

        if not matches:
            print("No matches found.")
        else:
            print()
            print("MATCHES:")
            print()

            for table, column, count in matches:
                print(
                    f"{table}.{column}"
                    f" -> {count:,} row(s)"
                )

        print()
        print("=" * 80)
        print("DONE")
        print("=" * 80)

    finally:
        conn.close()


if __name__ == "__main__":
    main()