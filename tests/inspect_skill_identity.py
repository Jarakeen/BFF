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
        print(" SKILL / ABILITY IDENTITY INSPECTION")
        print("=" * 60)
        print()

        for table in (
            "ability",
            "skill",
            "skill_rank",
        ):

            print("=" * 60)
            print(f"TABLE: {table}")
            print("=" * 60)
            print()

            print("COLUMNS:")

            columns = db.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()

            for column in columns:
                print(
                    f"  {column}"
                )

            print()
            print("FOREIGN KEYS:")

            foreign_keys = db.execute(
                f'PRAGMA foreign_key_list("{table}")'
            ).fetchall()

            if foreign_keys:

                for fk in foreign_keys:
                    print(
                        f"  {fk}"
                    )

            else:

                print("  None")

            print()
            print("ROW COUNT:")

            count = db.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            print(
                f"  {count}"
            )

            print()

        # ----------------------------------------------------
        # Specific Wall of Elements chain
        # ----------------------------------------------------

        print("=" * 60)
        print("WALL OF ELEMENTS")
        print("=" * 60)
        print()

        skills = db.execute(
            """
            SELECT
                id,
                base_ability_id,
                name,
                skill_line,
                skill_type
            FROM skill
            WHERE name = 'Wall of Elements'
            """
        ).fetchall()

        print("SKILL:")

        for row in skills:
            print(
                f"  {row}"
            )

        print()

        for skill_id, ability_id, name, _, _ in skills:

            print(
                f"ABILITY ID FROM SKILL: "
                f"{ability_id}"
            )

            abilities = db.execute(
                """
                SELECT *
                FROM ability
                WHERE ability_id = ?
                """,
                (ability_id,),
            ).fetchall()

            print(
                "ABILITY:"
            )

            for row in abilities:
                print(
                    f"  {row}"
                )

            print()

            ranks = db.execute(
                """
                SELECT *
                FROM skill_rank
                WHERE skill_id = ?
                ORDER BY rank
                """,
                (skill_id,),
            ).fetchall()

            print(
                "SKILL RANKS:"
            )

            for row in ranks:
                print(
                    f"  {row}"
                )

            print()

            links = db.execute(
                """
                SELECT
                    ael.id,
                    ael.effect_source_id,
                    ael.effect_variant_id,
                    ael.ability_id,
                    ael.condition,
                    ael.match_method,
                    ael.confidence
                FROM ability_effect_link ael
                WHERE ael.ability_id = ?
                """,
                (ability_id,),
            ).fetchall()

            print(
                "ABILITY EFFECT LINKS:"
            )

            for row in links:
                print(
                    f"  {row}"
                )

            if not links:
                print(
                    "  None"
                )

            print()

    finally:

        db.close()


if __name__ == "__main__":
    main()
    