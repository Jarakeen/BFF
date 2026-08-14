import sqlite3

for path in ["data/eso_main.db", "data/eso.db"]:
    print()
    print("=" * 60)
    print(path)
    print("=" * 60)

    with sqlite3.connect(path) as db:
        rows = db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()

        for row in rows:
            print(row[0])