import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "eso.db"

TARGET_EFFECTS = [
    "Brutality",
    "Savagery",
    "Prophecy",
    "Sorcery",
    "Heroism",
]

def main():
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    print("=" * 72)
    print("Black Feather Foundry")
    print("Potion Variant Diagnostic")
    print("=" * 72)
    print(f"DATABASE: {DB}")
    print()
    print("READ ONLY. No database changes will be made.")
    print()

    for effect_name in TARGET_EFFECTS:
        print("=" * 72)
        print(f"EFFECT: {effect_name}")
        print("=" * 72)

        rows = db.execute(
            """
            SELECT
                e.id AS effect_id,
                e.name AS effect_name,
                ev.id AS variant_id,
                ev.type AS variant_type,
                ev.description AS variant_description,
                ev.icon AS variant_icon,
                es.id AS source_id,
                es.source_type,
                es.source_name,
                es.condition,
                es.raw_text
            FROM effect e
            JOIN effect_variant ev
              ON ev.effect_id = e.id
            LEFT JOIN effect_source es
              ON es.effect_variant_id = ev.id
             AND es.source_type = 'Potions'
            WHERE e.name = ?
            ORDER BY ev.id, es.id
            """,
            (effect_name,),
        ).fetchall()

        if not rows:
            print("NO ROWS FOUND")
            print()
            continue

        current_variant = None

        for row in rows:
            if row["variant_id"] != current_variant:
                current_variant = row["variant_id"]
                print()
                print(f"  VARIANT ID:   {row['variant_id']}")
                print(f"  TYPE:          {row['variant_type']!r}")
                print(f"  DESCRIPTION:   {row['variant_description']!r}")
                print(f"  ICON:          {row['variant_icon']!r}")
                print("  POTION SOURCES:")

            if row["source_id"] is None:
                print("    (none)")
            else:
                print(f"    source_id:   {row['source_id']}")
                print(f"    source_name: {row['source_name']!r}")
                print(f"    condition:   {row['condition']!r}")
                print(f"    raw_text:    {row['raw_text']!r}")

    db.close()

    print()
    print("=" * 72)
    print("END DIAGNOSTIC")
    print("=" * 72)

if __name__ == "__main__":
    main()
