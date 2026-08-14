from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


# ============================================================
# Project Root
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# Database
# ============================================================

from services.eso_database import EsoDatabase


DATABASE_FILE = ROOT / "data" / "eso.db"


# ============================================================
# Source Files
# ============================================================

BUFF_FILE = (
    ROOT
    / "data"
    / "raw"
    / "buff.txt"
)

DEBUFF_FILE = (
    ROOT
    / "data"
    / "raw"
    / "debuff.txt"
)


# ============================================================
# Canonical Entity Helpers
# ============================================================


def slugify(value: str) -> str:
    """
    Convert an entity name into a stable canonical slug.
    """

    value = value.strip().casefold()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    value = value.strip("_")

    return value


def canonical_id(
    entity_type: str,
    name: str,
) -> str:
    """
    Build Foundry's canonical entity ID.
    """

    return (
        f"{entity_type}:"
        f"{slugify(name)}"
    )


# ============================================================
# Effects Importer
# ============================================================


class EffectsImporter:

    def __init__(
        self,
        database: EsoDatabase,
        buff_file: Path = BUFF_FILE,
        debuff_file: Path = DEBUFF_FILE,
    ):

        self.database = database

        self.buff_file = Path(
            buff_file
        )

        self.debuff_file = Path(
            debuff_file
        )

        self.effect_entity_ids: dict[
            str,
            str,
        ] = {}

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        print()
        print("=" * 60)
        print(" Black Feather Foundry")
        print(" ESO Effects Importer")
        print("=" * 60)
        print()

        print(
            f"Buff data:    {self.buff_file}"
        )

        print(
            f"Debuff data:  {self.debuff_file}"
        )

        print(
            f"Database:     {self.database.database}"
        )

        print()

        # ----------------------------------------------------
        # Load files
        # ----------------------------------------------------

        buff_lines = self._load_lines(
            self.buff_file
        )

        debuff_lines = self._load_lines(
            self.debuff_file
        )

        print(
            f"Buff lines:   {len(buff_lines):,}"
        )

        print(
            f"Debuff lines: {len(debuff_lines):,}"
        )

        print()

        # ----------------------------------------------------
        # Ensure schema
        # ----------------------------------------------------

        self._create_tables()

        # ----------------------------------------------------
        # Parse
        # ----------------------------------------------------

        buff_count = self._parse_file(
            buff_lines,
            "buff",
        )

        debuff_count = self._parse_file(
            debuff_lines,
            "debuff",
        )

        self.database.commit()

        # ----------------------------------------------------
        # Final counts
        # ----------------------------------------------------

        effect_count = self._count(
            "effect"
        )

        variant_count = self._count(
            "effect_variant"
        )

        source_count = self._count(
            "effect_source"
        )

        entity_count = self._count(
            "entity"
        )

        entity_source_count = self._count(
            "entity_source"
        )

        print()
        print("=" * 60)
        print(" Effects Import Complete")
        print("=" * 60)
        print()

        print(
            f"Buff effects:          {buff_count:,}"
        )

        print(
            f"Debuff effects:        {debuff_count:,}"
        )

        print(
            f"Effect rows:           {effect_count:,}"
        )

        print(
            f"Effect variants:       {variant_count:,}"
        )

        print(
            f"Effect sources:        {source_count:,}"
        )

        print(
            f"Canonical entities:    {entity_count:,}"
        )

        print(
            f"Source mappings:       {entity_source_count:,}"
        )

        print()

    # ========================================================
    # LOAD
    # ========================================================

    def _load_lines(
        self,
        path: Path,
    ) -> list[str]:

        if not path.exists():

            raise FileNotFoundError(
                f"Raw effect file not found:\n"
                f"{path}"
            )

        with path.open(
            "r",
            encoding="utf-8-sig",
        ) as file:

            return [
                line.rstrip("\n\r")
                for line in file
            ]

    # ========================================================
    # CREATE TABLES
    # ========================================================

    def _create_tables(self):
        """
        Ensure the existing effect tables exist.

        IMPORTANT:
        We intentionally DO NOT drop or rebuild them.
        """

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                icon TEXT,
                raw_section TEXT,
                raw_json TEXT
            )
            """
        )

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS effect_variant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                effect_id INTEGER NOT NULL,
                type TEXT,
                description TEXT,
                icon TEXT,
                raw_json TEXT,

                FOREIGN KEY (
                    effect_id
                )
                REFERENCES effect(id)
                ON DELETE CASCADE,

                UNIQUE (
                    effect_id,
                    type
                )
            )
            """
        )

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS effect_source (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                effect_variant_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                condition TEXT,
                raw_text TEXT,

                FOREIGN KEY (
                    effect_variant_id
                )
                REFERENCES effect_variant(id)
                ON DELETE CASCADE
            )
            """
        )

        self.database.execute(
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

        self.database.execute(
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

        self.database.commit()

    # ========================================================
    # PARSE FILE
    # ========================================================

    def _parse_file(
        self,
        lines: list[str],
        category: str,
    ) -> int:

        current_effect: dict[
            str,
            Any,
        ] | None = None

        current_variant: dict[
            str,
            Any,
        ] | None = None

        effect_count = 0

        section = category

        for raw_line in lines:

            line = raw_line.strip()

            if not line:
                continue

            # ------------------------------------------------
            # Headers
            # ------------------------------------------------

            if line in (
                "Buffs",
                "Debuffs",
                "Miscellaneous Buffs",
                "Quest-Related",
            ):

                section = line

                current_effect = None
                current_variant = None

                continue

            if line.startswith(
                "Buff Name"
            ):
                continue

            if line.startswith(
                "Debuff Name"
            ):
                continue

            # ------------------------------------------------
            # Tabbed data
            # ------------------------------------------------

            parsed = self._parse_tabbed_line(
                raw_line
            )

            if parsed:

                if self._looks_like_effect_name(
                    parsed
                ):

                    current_effect = {
                        "name": parsed[0].strip(),
                        "category": self._section_category(
                            section,
                            category,
                        ),
                        "section": section,
                        "icon": None,
                    }

                    effect_id = (
                        self._insert_effect(
                            current_effect
                        )
                    )

                    current_effect["id"] = (
                        effect_id
                    )

                    current_variant = None

                    effect_count += 1

                    continue

                if current_effect is None:
                    continue

                self._consume_data_row(
                    current_effect,
                    current_variant,
                    parsed,
                    raw_line,
                )

                current_variant = (
                    self._get_last_variant(
                        current_effect["id"]
                    )
                )

                continue

            # ------------------------------------------------
            # Non-tabbed effect name
            # ------------------------------------------------

            if self._looks_like_plain_effect(
                line
            ):

                current_effect = {
                    "name": line,
                    "category": self._section_category(
                        section,
                        category,
                    ),
                    "section": section,
                    "icon": None,
                }

                effect_id = (
                    self._insert_effect(
                        current_effect
                    )
                )

                current_effect["id"] = (
                    effect_id
                )

                current_variant = None

                effect_count += 1

        return effect_count

    # ========================================================
    # PARSE TABBED LINE
    # ========================================================

    def _parse_tabbed_line(
        self,
        raw_line: str,
    ) -> list[str] | None:

        if "\t" not in raw_line:
            return None

        parts = [
            part.strip()
            for part in raw_line.split("\t")
        ]

        parts = [
            part
            for part in parts
            if part != ""
        ]

        if not parts:
            return None

        return parts

    # ========================================================
    # EFFECT NAME DETECTION
    # ========================================================

    def _looks_like_effect_name(
        self,
        parts: list[str],
    ) -> bool:

        if len(parts) != 1:
            return False

        value = parts[0].strip()

        if not value:
            return False

        known_types = {
            "Minor",
            "Major",
            "Champion",
            "-",
            "Sets",
            "Abilities",
            "Scribing",
            "Potions",
            "Verses",
            "Verse",
        }

        if value in known_types:
            return False

        if value.startswith(
            "ON-icon-"
        ):
            return False

        return True

    # ========================================================
    # PLAIN EFFECT NAME
    # ========================================================

    def _looks_like_plain_effect(
        self,
        line: str,
    ) -> bool:

        if not line:
            return False

        if line.startswith(
            "ON-icon-"
        ):
            return False

        if line in {
            "Buffs",
            "Debuffs",
            "Miscellaneous Buffs",
            "Quest-Related",
        }:
            return False

        return True

    # ========================================================
    # SECTION CATEGORY
    # ========================================================

    def _section_category(
        self,
        section: str,
        default: str,
    ) -> str:

        section_lower = section.lower()

        if "debuff" in section_lower:
            return "debuff"

        if "quest" in section_lower:
            return "quest"

        if "miscellaneous" in section_lower:
            return "miscellaneous"

        return default

    # ========================================================
    # CONSUME DATA ROW
    # ========================================================

    def _consume_data_row(
        self,
        effect: dict[str, Any],
        current_variant: dict[str, Any] | None,
        parts: list[str],
        raw_line: str,
    ):

        if len(parts) == 0:
            return

        first = parts[0].strip()

        # ----------------------------------------------------
        # Variant row
        # ----------------------------------------------------

        variant_types = {
            "Minor",
            "Major",
            "Champion",
            "-",
        }

        if first in variant_types:

            variant_type = first

            description = (
                parts[1]
                if len(parts) > 1
                else None
            )

            source_type = (
                parts[2]
                if len(parts) > 2
                else None
            )

            source_text = (
                parts[3]
                if len(parts) > 3
                else None
            )

            icon = (
                parts[4]
                if len(parts) > 4
                else None
            )

            variant_id = (
                self._insert_variant(
                    effect_id=effect["id"],
                    variant_type=variant_type,
                    description=description,
                    icon=icon,
                    raw_line=raw_line,
                )
            )

            if source_type and source_text:

                self._insert_sources(
                    variant_id,
                    source_type,
                    source_text,
                    raw_line,
                    effect,
                )

            return

        # ----------------------------------------------------
        # Continuation source row
        # ----------------------------------------------------

        source_types = {
            "Abilities",
            "Sets",
            "Scribing",
            "Potions",
            "Verses",
            "Verse",
        }

        if first in source_types:

            if current_variant is None:

                variant_id = (
                    self._insert_variant(
                        effect_id=effect["id"],
                        variant_type=None,
                        description=None,
                        icon=None,
                        raw_line=raw_line,
                    )
                )

            else:

                variant_id = (
                    current_variant["id"]
                )

            source_text = (
                parts[1]
                if len(parts) > 1
                else ""
            )

            self._insert_sources(
                variant_id,
                first,
                source_text,
                raw_line,
                effect,
            )

    # ========================================================
    # INSERT EFFECT
    # ========================================================

    def _insert_effect(
        self,
        effect: dict[str, Any],
    ) -> int:

        name = effect["name"].strip()

        category = effect[
            "category"
        ]

        # ----------------------------------------------------
        # Reuse existing effect
        # ----------------------------------------------------

        row = self.database.execute(
            """
            SELECT id
            FROM effect
            WHERE name = ?
            """,
            (name,),
        ).fetchone()

        if row is not None:

            effect_id = int(
                row[0]
            )

        else:

            cursor = self.database.execute(
                """
                INSERT INTO effect (
                    name,
                    category,
                    icon,
                    raw_section,
                    raw_json
                )
                VALUES (
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    name,
                    category,
                    effect.get("icon"),
                    effect.get("section"),
                    json.dumps(
                        effect,
                        ensure_ascii=False,
                    ),
                ),
            )

            effect_id = int(
                cursor.lastrowid
            )

        # ----------------------------------------------------
        # Canonical entity
        # ----------------------------------------------------

        entity_type = (
            "debuff"
            if category == "debuff"
            else "buff"
        )

        entity_id = (
            canonical_id(
                entity_type,
                name,
            )
        )

        self.database.execute(
            """
            INSERT INTO entity (
                id,
                entity_type,
                name,
                slug
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(id)
            DO UPDATE SET
                name = excluded.name,
                slug = excluded.slug
            """,
            (
                entity_id,
                entity_type,
                name,
                slugify(name),
            ),
        )

        self.effect_entity_ids[
            name.casefold()
        ] = entity_id

        # ----------------------------------------------------
        # Preserve relationship between canonical effect
        # and existing effect table.
        #
        # The existing effect ID is recorded as a source
        # identity rather than replacing it.
        # ----------------------------------------------------

        self._insert_entity_source(
            entity_id=entity_id,
            source="BFF",
            source_entity_type="effect",
            source_id=str(effect_id),
            source_name=name,
            raw_json=effect,
        )

        return effect_id

    # ========================================================
    # INSERT VARIANT
    # ========================================================

    def _insert_variant(
        self,
        effect_id: int,
        variant_type: str | None,
        description: str | None,
        icon: str | None,
        raw_line: str,
    ) -> int:

        row = self.database.execute(
            """
            SELECT id
            FROM effect_variant
            WHERE effect_id = ?
              AND (
                    type = ?
                    OR (
                        type IS NULL
                        AND ? IS NULL
                    )
              )
            ORDER BY id
            LIMIT 1
            """,
            (
                effect_id,
                variant_type,
                variant_type,
            ),
        ).fetchone()

        if row is not None:

            variant_id = int(
                row[0]
            )

            self.database.execute(
                """
                UPDATE effect_variant
                SET
                    description = COALESCE(
                        ?,
                        description
                    ),
                    icon = COALESCE(
                        ?,
                        icon
                    )
                WHERE id = ?
                """,
                (
                    description,
                    icon,
                    variant_id,
                ),
            )

            return variant_id

        cursor = self.database.execute(
            """
            INSERT INTO effect_variant (
                effect_id,
                type,
                description,
                icon,
                raw_json
            )
            VALUES (
                ?, ?, ?, ?, ?
            )
            """,
            (
                effect_id,
                variant_type,
                description,
                icon,
                json.dumps(
                    {
                        "raw_line": raw_line,
                    },
                    ensure_ascii=False,
                ),
            ),
        )

        return int(
            cursor.lastrowid
        )

    # ========================================================
    # INSERT SOURCES
    # ========================================================

    def _insert_sources(
        self,
        variant_id: int,
        source_type: str,
        source_text: str,
        raw_line: str,
        effect: dict[str, Any],
    ):

        if not source_text:
            return

        source_names = [
            part.strip()
            for part in source_text.split(",")
            if part.strip()
        ]

        for source_name in source_names:

            condition = (
                self._extract_condition(
                    source_name
                )
            )

            # ------------------------------------------------
            # Prevent duplicate effect_source rows
            # ------------------------------------------------

            row = self.database.execute(
                """
                SELECT id
                FROM effect_source
                WHERE effect_variant_id = ?
                  AND source_type = ?
                  AND source_name = ?
                  AND (
                        condition = ?
                        OR (
                            condition IS NULL
                            AND ? IS NULL
                        )
                  )
                LIMIT 1
                """,
                (
                    variant_id,
                    source_type,
                    source_name,
                    condition,
                    condition,
                ),
            ).fetchone()

            if row is None:

                self.database.execute(
                    """
                    INSERT INTO effect_source (
                        effect_variant_id,
                        source_type,
                        source_name,
                        condition,
                        raw_text
                    )
                    VALUES (
                        ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        variant_id,
                        source_type,
                        source_name,
                        condition,
                        raw_line,
                    ),
                )

            # ------------------------------------------------
            # Canonical source mapping
            # ------------------------------------------------

            entity_type = (
                self._source_entity_type(
                    source_type
                )
            )

            entity_id = (
                self._effect_entity_id(
                    effect
                )
            )

            # ------------------------------------------------
            # IMPORTANT:
            #
            # source_id is deliberately TEXT.
            #
            # We preserve the source type together with
            # the source name so that:
            #
            # Abilities / Foo
            #
            # cannot collide with:
            #
            # Sets / Foo
            #
            # Potions / Foo
            # ------------------------------------------------

            source_id = (
                f"{source_type}:"
                f"{source_name}"
            )

            self._insert_entity_source(
                entity_id=entity_id,
                source="buff_debuff_data",
                source_entity_type=entity_type,
                source_id=source_id,
                source_name=source_name,
                raw_json={
                    "source_type": source_type,
                    "source_name": source_name,
                    "condition": condition,
                    "raw_line": raw_line,
                },
            )

    # ========================================================
    # SOURCE ENTITY TYPE
    # ========================================================

    def _source_entity_type(
        self,
        source_type: str,
    ) -> str:

        mapping = {
            "Abilities": "skill",
            "Sets": "gear_set",
            "Scribing": "skill",
            "Potions": "potion",
            "Verses": "verse",
            "Verse": "verse",
        }

        return mapping.get(
            source_type,
            "source",
        )

    # ========================================================
    # EFFECT ENTITY ID
    # ========================================================

    def _effect_entity_id(
        self,
        effect: dict[str, Any],
    ) -> str:

        name = effect[
            "name"
        ].strip()

        category = effect[
            "category"
        ]

        entity_type = (
            "debuff"
            if category == "debuff"
            else "buff"
        )

        return canonical_id(
            entity_type,
            name,
        )

    # ========================================================
    # ENTITY SOURCE
    # ========================================================

    def _insert_entity_source(
        self,
        entity_id: str,
        source: str,
        source_entity_type: str | None,
        source_id: str | None,
        source_name: str | None,
        raw_json: Any = None,
    ):

        if source_id is None:
            return

        source_id = str(
            source_id
        ).strip()

        if not source_id:
            return

        raw_value = None

        if raw_json is not None:

            raw_value = json.dumps(
                raw_json,
                ensure_ascii=False,
                sort_keys=True,
            )

        self.database.execute(
            """
            INSERT INTO entity_source (
                entity_id,
                source,
                source_entity_type,
                source_id,
                source_name,
                raw_json
            )
            VALUES (
                ?, ?, ?, ?, ?, ?
            )

            ON CONFLICT(
                entity_id,
                source,
                source_entity_type,
                source_id
            )
            DO UPDATE SET
                source_name = excluded.source_name,
                raw_json = excluded.raw_json
            """,
            (
                entity_id,
                source,
                source_entity_type,
                source_id,
                source_name,
                raw_value,
            ),
        )

    # ========================================================
    # LAST VARIANT
    # ========================================================

    def _get_last_variant(
        self,
        effect_id: int,
    ) -> dict[str, Any] | None:

        row = self.database.execute(
            """
            SELECT
                id,
                type
            FROM effect_variant
            WHERE effect_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (effect_id,),
        ).fetchone()

        if row is None:
            return None

        return {
            "id": int(
                row[0]
            ),
            "type": row[1],
        }

    # ========================================================
    # CONDITION EXTRACTION
    # ========================================================

    def _extract_condition(
        self,
        source_name: str,
    ) -> str | None:

        match = re.search(
            r"\(([^()]*)\)",
            source_name,
        )

        if match:

            return match.group(
                1
            ).strip()

        lower = source_name.lower()

        conditional_markers = (
            " against ",
            " with ",
            " while ",
            " during ",
            " when ",
            " applies ",
        )

        for marker in conditional_markers:

            index = lower.find(
                marker
            )

            if index >= 0:

                return source_name[
                    index:
                ].strip()

        return None

    # ========================================================
    # COUNT
    # ========================================================

    def _count(
        self,
        table: str,
    ) -> int:

        row = self.database.execute(
            f"""
            SELECT COUNT(*)
            FROM {table}
            """
        ).fetchone()

        return int(
            row[0]
        )


# ============================================================
# MAIN
# ============================================================


def main():

    database = EsoDatabase(
        DATABASE_FILE
    )

    importer = EffectsImporter(
        database
    )

    try:

        importer.run()

    except Exception:

        database.rollback()

        raise

    finally:

        database.close()


if __name__ == "__main__":
    main()