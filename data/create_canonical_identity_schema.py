import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "eso.db"
)


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Canonical Identity Schema")
    print("=" * 60)

    print()
    print(f"Database: {DB_PATH}")
    print()

    db = sqlite3.connect(DB_PATH)

    try:
        db.execute("PRAGMA foreign_keys = ON")

        print("Creating entity table...")

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS entity (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,

                UNIQUE (
                    entity_type,
                    slug
                )
            )
            """
        )

        print("Creating entity_source table...")

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_source (
                id INTEGER PRIMARY KEY,
                entity_id TEXT NOT NULL,
                source TEXT NOT NULL,
                source_entity_type TEXT,
                source_id TEXT,
                source_name TEXT,
                raw_json TEXT,

                FOREIGN KEY (
                    entity_id
                )
                REFERENCES entity(id)
                ON DELETE CASCADE,

                UNIQUE (
                    entity_id,
                    source,
                    source_entity_type,
                    source_id
                )
            )
            """
        )

        db.commit()

        print()
        print("=" * 60)
        print(" CANONICAL IDENTITY SCHEMA READY")
        print("=" * 60)

        print()
        print("Tables:")

        for table in (
            "entity",
            "entity_source",
        ):
            exists = db.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                """,
                (table,),
            ).fetchone()

            print(
                f"  {table:<20}"
                f"{'OK' if exists else 'MISSING'}"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
