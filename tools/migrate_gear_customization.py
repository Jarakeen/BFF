from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]

PROD = ROOT / "data" / "eso.db"
TEST = ROOT / "data" / "eso_gear_customization_test.db"
BACKUP = ROOT / "data" / "eso.db.pre_gear_customization"

TABLES = [
    "gear_trait_material",
    "armor_glyph",
    "armor_glyph_effect",
    "jewelry_trait",
    "jewelry_trait_effect",
    "jewelry_glyph",
    "jewelry_glyph_effect",
    "weapon_enchantment",
    "weapon_enchantment_effect",
    "weapon_trait_effect",
]


def main():

    if not PROD.exists():
        raise FileNotFoundError(PROD)

    if not TEST.exists():
        raise FileNotFoundError(TEST)

    if not BACKUP.exists():
        raise RuntimeError(
            f"Backup missing: {BACKUP}"
        )

    prod = sqlite3.connect(PROD)

    try:
        prod.execute("PRAGMA foreign_keys = ON")

        print("Opening production database...")
        print("Attaching validated test database...")

        prod.execute(
            "ATTACH DATABASE ? AS source",
            (str(TEST),),
        )

        try:

            # Production must not already contain these tables.
            for table in TABLES:
                exists = prod.execute(
                    """
                    SELECT COUNT(*)
                    FROM main.sqlite_master
                    WHERE type = 'table'
                    AND name = ?
                    """,
                    (table,),
                ).fetchone()[0]

                if exists:
                    raise RuntimeError(
                        f"Production already contains table: {table}"
                    )

            print("\nCreating tables...")

            for table in TABLES:

                schema = prod.execute(
                    """
                    SELECT sql
                    FROM source.sqlite_master
                    WHERE type = 'table'
                    AND name = ?
                    """,
                    (table,),
                ).fetchone()

                if not schema or not schema[0]:
                    raise RuntimeError(
                        f"No schema found for {table}"
                    )

                sql = schema[0]

                # The source schema contains CREATE TABLE table_name.
                sql = sql.replace(
                    f"CREATE TABLE {table}",
                    f"CREATE TABLE main.{table}",
                    1,
                )

                prod.execute(sql)

                prod.execute(
                    f"""
                    INSERT INTO main.{table}
                    SELECT *
                    FROM source.{table}
                    """
                )

                count = prod.execute(
                    f"SELECT COUNT(*) FROM main.{table}"
                ).fetchone()[0]

                expected = prod.execute(
                    f"SELECT COUNT(*) FROM source.{table}"
                ).fetchone()[0]

                if count != expected:
                    raise RuntimeError(
                        f"Row count mismatch for {table}: "
                        f"{count} != {expected}"
                    )

                print(
                    f"  {table}: {count} rows"
                )

            print("\nCreating gear indexes...")

            # Only copy indexes whose table belongs to our migration.
            for table in TABLES:

                indexes = prod.execute(
                    """
                    SELECT name, sql
                    FROM source.sqlite_master
                    WHERE type = 'index'
                    AND tbl_name = ?
                    AND sql IS NOT NULL
                    """,
                    (table,),
                ).fetchall()

                for name, sql in indexes:

                    # Recreate the index in main.
                    sql = sql.replace(
                        "CREATE INDEX ",
                        "CREATE INDEX main.",
                        1,
                    )

                    prod.execute(sql)

                    print(
                        f"  {name}"
                    )

            print("\nValidating migrated row counts...")

            for table in TABLES:

                actual = prod.execute(
                    f"SELECT COUNT(*) FROM main.{table}"
                ).fetchone()[0]

                expected = prod.execute(
                    f"SELECT COUNT(*) FROM source.{table}"
                ).fetchone()[0]

                if actual != expected:
                    raise RuntimeError(
                        f"Validation failed for {table}: "
                        f"{actual} != {expected}"
                    )

                print(
                    f"  {table}: OK ({actual})"
                )

            prod.commit()

            print("\nMigration complete.")

        except Exception:
            print(
                "\nERROR: migration failed."
            )
            print(
                "Rolling back production transaction..."
            )
            prod.rollback()
            raise

        finally:
            prod.execute(
                "DETACH DATABASE source"
            )

    finally:
        prod.close()


if __name__ == "__main__":
    main()
