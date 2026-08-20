import sqlite3

db = sqlite3.connect("data/eso.db")

tables = [
    row[0]
    for row in db.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' ORDER BY name"
    )
    if any(
        term in row[0].lower()
        for term in ("race", "racial", "passive")
    )
]

for table in tables:
    print(f"\n--- {table} ---")

    print("COLUMNS:")
    for row in db.execute(f"PRAGMA table_info({table})"):
        print(row)

    print("SAMPLE:")
    for row in db.execute(f"SELECT * FROM {table} LIMIT 5"):
        print(row)

db.close()
