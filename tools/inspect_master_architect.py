import sqlite3

DB = "data/eso.db"

with sqlite3.connect(DB) as db:
    print("=" * 80)
    print("MASTER ARCHITECT")
    print("=" * 80)

    # Find the set
    rows = db.execute(
        """
        SELECT *
        FROM gear_set
        WHERE LOWER(name) LIKE '%master architect%'
        """
    ).fetchall()

    print(f"\ngear_set matches: {len(rows)}")

    for row in rows:
        print("\nGEAR SET:")
        print(row)

    # Show column names
    print("\nGEAR_SET COLUMNS:")
    for row in db.execute("PRAGMA table_info(gear_set)"):
        print(row)

    print("\n" + "=" * 80)
    print("GEAR SET BONUS COLUMNS")
    print("=" * 80)

    for row in db.execute("PRAGMA table_info(gear_set_bonus)"):
        print(row)
        
    print("\n" + "=" * 80)
    print("MASTER ARCHITECT BONUSES")
    print("=" * 80)

    bonuses = db.execute(
        """
        SELECT
            id,
            set_id,
            piece_count,
            description
        FROM gear_set_bonus
        WHERE set_id = 332
        ORDER BY piece_count
        """
    ).fetchall()

    for bonus in bonuses:
        print(bonus)        