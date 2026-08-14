from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILE = (
    ROOT
    / "data"
    / "eso.db"
)


class SkillsRebuild:

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
        print(" Skills Canonical Rebuild")
        print("=========================================")
        print()

        print(
            f"Database: {self.database_path}"
        )

        db = sqlite3.connect(
            self.database_path
        )

        try:

            self._create_tables(db)

            self._clear_tables(db)

            skill_map = (
                self._build_skills(db)
            )

            rank_count = (
                self._build_skill_ranks(
                    db,
                    skill_map,
                )
            )

            db.commit()

            self._report(
                db,
                rank_count,
            )

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

    # ==================================================
    # TABLES
    # ==================================================

    def _create_tables(
        self,
        db: sqlite3.Connection,
    ):

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS skill (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                base_ability_id INTEGER NOT NULL UNIQUE,

                name TEXT,
                index_name TEXT,
                description TEXT,
                texture TEXT,

                class_type TEXT,
                skill_line TEXT,

                target TEXT,
                skill_type INTEGER,

                is_passive INTEGER
                    NOT NULL DEFAULT 0,

                is_player INTEGER
                    NOT NULL DEFAULT 0,

                is_crafted INTEGER
                    NOT NULL DEFAULT 0,

                crafted_id INTEGER
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS skill_rank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                skill_id INTEGER NOT NULL,

                ability_id INTEGER NOT NULL UNIQUE,
                display_id INTEGER,

                rank INTEGER,
                morph INTEGER,

                skill_index INTEGER,
                learned_level INTEGER,

                FOREIGN KEY (
                    skill_id
                )
                REFERENCES skill(id)
                ON DELETE CASCADE
            )
            """
        )

        db.commit()

    # ==================================================
    # CLEAR
    # ==================================================

    def _clear_tables(
        self,
        db: sqlite3.Connection,
    ):

        db.execute(
            "DELETE FROM skill_rank"
        )

        db.execute(
            "DELETE FROM skill"
        )

        db.commit()

    # ==================================================
    # BUILD SKILLS
    # ==================================================

    def _build_skills(
        self,
        db: sqlite3.Connection,
    ) -> dict[int, int]:

        rows = db.execute(
            """
            SELECT
                ability_id,
                name,
                index_name,
                description,
                texture,
                class_type,
                skill_line,
                target,
                skill_type,
                is_passive,
                is_player,
                is_crafted,
                crafted_id
            FROM ability
            WHERE base_ability_id != -1
              AND is_crafted = 0
            ORDER BY
                base_ability_id,
                rank,
                morph,
                ability_id
            """
        ).fetchall()

        skill_map = {}

        for row in rows:

            (
                ability_id,
                name,
                index_name,
                description,
                texture,
                class_type,
                skill_line,
                target,
                skill_type,
                is_passive,
                is_player,
                is_crafted,
                crafted_id,
            ) = row

            existing = db.execute(
                """
                SELECT id
                FROM skill
                WHERE base_ability_id = ?
                """,
                (
                    ability_id,
                ),
            ).fetchone()

            # --------------------------------------------------
            # We only create the canonical skill when this
            # ability is its own base ability.
            # --------------------------------------------------

            base_row = db.execute(
                """
                SELECT id
                FROM ability
                WHERE ability_id = ?
                  AND base_ability_id = ?
                """,
                (
                    ability_id,
                    ability_id,
                ),
            ).fetchone()

            if base_row is None:
                continue

            if existing:
                skill_id = existing[0]

            else:

                cursor = db.execute(
                    """
                    INSERT INTO skill (
                        base_ability_id,
                        name,
                        index_name,
                        description,
                        texture,
                        class_type,
                        skill_line,
                        target,
                        skill_type,
                        is_passive,
                        is_player,
                        is_crafted,
                        crafted_id
                    )
                    VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?
                    )
                    """,
                    (
                        ability_id,
                        name,
                        index_name,
                        description,
                        texture,
                        class_type,
                        skill_line,
                        target,
                        skill_type,
                        is_passive,
                        is_player,
                        is_crafted,
                        crafted_id,
                    ),
                )

                skill_id = cursor.lastrowid

            skill_map[
                ability_id
            ] = skill_id

        return skill_map

    # ==================================================
    # BUILD RANKS
    # ==================================================

    def _build_skill_ranks(
        self,
        db: sqlite3.Connection,
        skill_map: dict[int, int],
    ) -> int:

        rows = db.execute(
            """
            SELECT
                ability_id,
                base_ability_id,
                display_id,
                rank,
                morph,
                skill_index,
                learned_level
            FROM ability
            WHERE base_ability_id != -1
              AND is_crafted = 0
            ORDER BY
                base_ability_id,
                rank,
                morph,
                ability_id
            """
        ).fetchall()

        inserted = 0

        for row in rows:

            (
                ability_id,
                base_ability_id,
                display_id,
                rank,
                morph,
                skill_index,
                learned_level,
            ) = row

            skill_id = skill_map.get(
                base_ability_id
            )

            if skill_id is None:
                continue

            db.execute(
                """
                INSERT OR IGNORE INTO skill_rank (
                    skill_id,
                    ability_id,
                    display_id,
                    rank,
                    morph,
                    skill_index,
                    learned_level
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    skill_id,
                    ability_id,
                    display_id,
                    rank,
                    morph,
                    skill_index,
                    learned_level,
                ),
            )

            inserted += 1

        return inserted

    # ==================================================
    # REPORT
    # ==================================================

    def _report(
        self,
        db: sqlite3.Connection,
        rank_count: int,
    ):

        skills = db.execute(
            """
            SELECT COUNT(*)
            FROM skill
            """
        ).fetchone()[0]

        ranks = db.execute(
            """
            SELECT COUNT(*)
            FROM skill_rank
            """
        ).fetchone()[0]

        print()
        print("## Skills Rebuild Complete")
        print()
        print(
            f"Canonical skills:  {skills:,}"
        )
        print(
            f"Skill ranks:       {ranks:,}"
        )
        print()

        print(
            "Scribing abilities remain "
            "in the ability table."
        )

        print(
            "Standalone base=-1 abilities "
            "remain in the ability table."
        )

        print()


def main():

    rebuild = SkillsRebuild()

    rebuild.run()


if __name__ == "__main__":
    main()