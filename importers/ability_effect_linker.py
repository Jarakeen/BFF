from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILE = (
    ROOT
    / "data"
    / "eso.db"
)


class AbilityEffectLinker:

    def __init__(
        self,
        database_path: Path = DATABASE_FILE,
    ):
        self.database_path = Path(
            database_path
        )

    # ==================================================
    # RUN
    # ==================================================

    def run(self):

        print()
        print("=========================================")
        print(" Black Feather Foundry")
        print(" Ability → Effect Linker")
        print("=========================================")
        print()

        print(
            f"Database: {self.database_path}"
        )

        db = sqlite3.connect(
            self.database_path
        )

        try:

            self._create_table(db)

            self._clear_table(db)

            sources = self._load_sources(db)

            linked = 0
            matched_sources = 0
            unmatched_sources = []

            for source in sources:

                source_id = source[0]
                effect_variant_id = source[1]
                source_name = source[2]
                condition = source[3]

                matches = self._find_abilities(
                    db,
                    source_name,
                )

                if not matches:

                    unmatched_sources.append(
                        source
                    )

                    continue

                matched_sources += 1

                for ability_id in matches:

                    db.execute(
                        """
                        INSERT OR IGNORE INTO
                        ability_effect_link (
                            effect_source_id,
                            effect_variant_id,
                            ability_id,
                            condition,
                            match_method,
                            confidence
                        )
                        VALUES (
                            ?, ?, ?, ?, ?, ?
                        )
                        """,
                        (
                            source_id,
                            effect_variant_id,
                            ability_id,
                            condition,
                            "exact_name",
                            1.0,
                        ),
                    )

                    linked += 1

            db.commit()

            self._report(
                db,
                len(sources),
                matched_sources,
                linked,
                unmatched_sources,
            )

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

    # ==================================================
    # TABLE
    # ==================================================

    def _create_table(
        self,
        db: sqlite3.Connection,
    ):

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS
            ability_effect_link (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                effect_source_id INTEGER NOT NULL,

                effect_variant_id INTEGER NOT NULL,

                ability_id INTEGER NOT NULL,

                condition TEXT,

                match_method TEXT NOT NULL,

                confidence REAL NOT NULL
                    DEFAULT 1.0,

                UNIQUE (
                    effect_source_id,
                    ability_id
                ),

                FOREIGN KEY (
                    effect_source_id
                )
                REFERENCES effect_source(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    effect_variant_id
                )
                REFERENCES effect_variant(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    ability_id
                )
                REFERENCES ability(ability_id)
                ON DELETE CASCADE
            )
            """
        )

        db.commit()

    # ==================================================
    # CLEAR
    # ==================================================

    def _clear_table(
        self,
        db: sqlite3.Connection,
    ):

        db.execute(
            """
            DELETE FROM ability_effect_link
            """
        )

        db.commit()

    # ==================================================
    # LOAD SOURCES
    # ==================================================

    def _load_sources(
        self,
        db: sqlite3.Connection,
    ):

        return db.execute(
            """
            SELECT
                id,
                effect_variant_id,
                source_name,
                condition
            FROM effect_source
            WHERE source_type = 'Abilities'
            ORDER BY id
            """
        ).fetchall()

    # ==================================================
    # FIND ABILITIES
    # ==================================================

    def _find_abilities(
        self,
        db: sqlite3.Connection,
        source_name: str,
    ):

        return [
            row[0]
            for row in db.execute(
                """
                SELECT ability_id
                FROM ability
                WHERE LOWER(TRIM(name))
                    = LOWER(TRIM(?))
                ORDER BY ability_id
                """,
                (
                    source_name,
                ),
            ).fetchall()
        ]

    # ==================================================
    # REPORT
    # ==================================================

    def _report(
        self,
        db: sqlite3.Connection,
        total_sources: int,
        matched_sources: int,
        linked: int,
        unmatched_sources,
    ):

        rows = db.execute(
            """
            SELECT COUNT(*)
            FROM ability_effect_link
            """
        ).fetchone()[0]

        unique_abilities = db.execute(
            """
            SELECT COUNT(
                DISTINCT ability_id
            )
            FROM ability_effect_link
            """
        ).fetchone()[0]

        print()
        print("## Ability → Effect Linking Complete")
        print()

        print(
            f"Ability sources:       {total_sources:,}"
        )

        print(
            f"Matched sources:       {matched_sources:,}"
        )

        print(
            f"Unmatched sources:     "
            f"{len(unmatched_sources):,}"
        )

        print(
            f"Ability-effect links:  {linked:,}"
        )

        print(
            f"Unique abilities:      "
            f"{unique_abilities:,}"
        )

        print()

        if unmatched_sources:

            print(
                "UNMATCHED SOURCES"
            )

            print(
                "================="
            )

            for source in unmatched_sources:

                print(
                    f"{source[0]} | "
                    f"{source[2]} | "
                    f"condition={source[3]}"
                )

        print()


def main():

    linker = AbilityEffectLinker()

    linker.run()


if __name__ == "__main__":
    main()