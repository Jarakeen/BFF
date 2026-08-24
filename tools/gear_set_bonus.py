import sqlite3

with sqlite3.connect("data/eso.db") as db:
    print("EFFECT VARIANT 37")
    print("=" * 80)

    print(
        db.execute(
            """
            SELECT *
            FROM effect_variant
            WHERE id = 37
            """
        ).fetchone()
    )

    print("\nEFFECT SOURCES")
    print("=" * 80)

    for row in db.execute(
        """
        SELECT *
        FROM effect_source
        WHERE effect_variant_id = 37
        """
    ):
        print(row)

    print("\nENTITY SOURCES FOR MASTER ARCHITECT")
    print("=" * 80)

    for row in db.execute(
        """
        SELECT *
        FROM entity_source
        WHERE source_name = 'Master Architect'
        """
    ):
        print(row)