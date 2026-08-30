# services/reference_data_service.py
#
# Lightweight read-only lookups against the existing
# eso.db (see EsoDatabase) for populating combo boxes on
# the Builds and Capabilities pages, and for suggesting
# buffs/debuffs to watch based on the sets a player has
# equipped.
#
# This intentionally does not touch ReferenceLibrary
# (services/reference_service.py) -- that class reads
# standalone JSON files that aren't present in this
# workspace. eso.db is the one reference dataset that's
# actually populated, so lookups go straight at it.

from __future__ import annotations

import re

from services.eso_database import EsoDatabase


# "Major Slayer", "Minor Force", ... -- the standard ESO
# buff/debuff naming convention. Used to pull suggested
# watches out of gear set bonus description text.
_BUFF_PATTERN = re.compile(
    r"\b(Major|Minor)\s+[A-Z][A-Za-z'’]+(?:\s+[A-Z][A-Za-z'’]+)?"
)


class ReferenceDataService:

    def __init__(self, database: EsoDatabase):

        self.database = database

        self._race_names: list[str] | None = None
        self._gear_set_names: list[str] | None = None
        self._skill_names: list[str] | None = None
        self._cp_names: list[str] | None = None
        self._skill_rows: list[dict] | None = None
        self._food_names: list[str] | None = None
        self._potion_names: list[str] | None = None
    # --------------------------------------------------
    # Combo box sources
    # --------------------------------------------------

    def list_race_names(self) -> list[str]:

        if self._race_names is None:

            try:

                rows = self.database.execute(
                    "SELECT name FROM race ORDER BY name"
                ).fetchall()

                self._race_names = [row["name"] for row in rows]

            except Exception:
                self._race_names = []

        return self._race_names

    def list_gear_set_names(self) -> list[str]:
        """Return every selectable gear-set name known to the database.

        Older imports populate ``gear_set`` directly, while newer canonical
        imports may first register a set in ``entity`` as ``entity_type='gear_set'``.
        The build editor should expose both sources so arena weapons and other
        canonical-only set entities are selectable before their bonus math is
        necessarily fully normalized into ``gear_set_bonus``.
        """

        if self._gear_set_names is None:

            try:
                if self.database.table_exists("entity"):
                    rows = self.database.execute(
                        """
                        SELECT name
                        FROM (
                            SELECT name
                            FROM gear_set
                            WHERE name IS NOT NULL AND TRIM(name) <> ''

                            UNION

                            SELECT name
                            FROM entity
                            WHERE entity_type = 'gear_set'
                              AND name IS NOT NULL
                              AND TRIM(name) <> ''
                        )
                        ORDER BY name COLLATE NOCASE
                        """
                    ).fetchall()
                else:
                    rows = self.database.execute(
                        """
                        SELECT name
                        FROM gear_set
                        WHERE name IS NOT NULL AND TRIM(name) <> ''
                        ORDER BY name COLLATE NOCASE
                        """
                    ).fetchall()

                self._gear_set_names = [row["name"] for row in rows]

            except Exception:
                self._gear_set_names = []

        return self._gear_set_names

    def list_skill_names(self) -> list[str]:

        if self._skill_names is None:

            try:

                rows = self.database.execute(
                    """
                    SELECT DISTINCT name
                    FROM skill
                    WHERE name IS NOT NULL AND name != ''
                    ORDER BY name
                    """
                ).fetchall()

                self._skill_names = [row["name"] for row in rows]

            except Exception:
                self._skill_names = []

        return self._skill_names

    def list_skills(self) -> list[dict]:
        """
        Return one display record for each base skill and morph.

        The canonical ``skill`` row owns the skill-line identity,
        while ``skill_rank`` links that identity to the concrete
        ability records. The concrete ability row is the source of
        truth for the displayed name and icon, so morphs retain their
        actual ESO names instead of inheriting the base skill name.

        One record per morph is returned using the highest available
        rank. The rank identity is retained in the returned mapping so
        later calculation work can resolve the selected ability without
        another name-based lookup.
        """

        if self._skill_rows is None:

            try:

                rows = self.database.execute(
                    """
                    WITH ranked AS (
                        SELECT
                            s.id,
                            s.base_ability_id,
                            s.name AS base_name,
                            s.index_name AS base_index_name,
                            s.description AS base_description,
                            s.texture AS base_texture,
                            s.class_type,
                            s.skill_line,
                            s.target AS base_target,
                            s.skill_type AS base_skill_type,
                            s.is_passive,
                            s.is_player,
                            s.is_crafted,
                            s.crafted_id,

                            sr.ability_id,
                            sr.display_id,
                            sr.rank,
                            sr.morph,
                            sr.skill_index,
                            sr.learned_level,

                            COALESCE(
                                NULLIF(ar.name, ''),
                                s.name
                            ) AS name,
                            COALESCE(
                                NULLIF(ar.index_name, ''),
                                s.index_name
                            ) AS index_name,
                            COALESCE(
                                NULLIF(ar.description, ''),
                                s.description
                            ) AS description,
                            COALESCE(
                                NULLIF(ar.texture, ''),
                                s.texture
                            ) AS texture,
                            COALESCE(
                                NULLIF(ar.target, ''),
                                s.target
                            ) AS target,
                            COALESCE(
                                ar.skill_type,
                                s.skill_type
                            ) AS skill_type,

                            a.base_mechanic,
                            a.cost,
                            a.buff_type,

                            ROW_NUMBER() OVER (
                                PARTITION BY s.id, sr.morph
                                ORDER BY sr.rank DESC, sr.ability_id DESC
                            ) AS rn

                        FROM skill s

                        JOIN skill_rank sr
                            ON sr.skill_id = s.id

                        JOIN ability ar
                            ON ar.ability_id = sr.ability_id

                        LEFT JOIN ability a
                            ON a.base_ability_id = s.base_ability_id

                        WHERE s.name IS NOT NULL
                        AND s.name != ''
                    )

                    SELECT
                        id,
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
                        crafted_id,
                        ability_id,
                        display_id,
                        rank,
                        morph,
                        skill_index,
                        learned_level,
                        base_mechanic,
                        cost,
                        buff_type
                    FROM ranked
                    WHERE rn = 1
                    ORDER BY name
                    """
                ).fetchall()

                self._skill_rows = [
                    dict(row)
                    for row in rows
                ]

            except Exception as exc:

                print(
                    "SKILLS QUERY ERROR:",
                    repr(exc),
                )

                self._skill_rows = []

        return self._skill_rows

    def list_champion_points(self) -> list[dict]:
        """Return Champion Point reference records with discipline metadata."""

        if getattr(self, "_cp_rows", None) is None:

            try:
                rows = self.database.execute(
                    """
                    SELECT
                        id,
                        name,
                        discipline_id,
                        description,
                        min_description,
                        max_description,
                        max_points,
                        jump_points,
                        skill_type
                    FROM champion_point
                    WHERE name IS NOT NULL AND TRIM(name) <> ''
                    ORDER BY name COLLATE NOCASE
                    """
                ).fetchall()

                self._cp_rows = [dict(row) for row in rows]

            except Exception:
                self._cp_rows = []

        return self._cp_rows

    def list_food_names(self) -> list[str]:
        if self._food_names is None:
            self._food_names = self._list_entity_names("food", "drink")
        return self._food_names

    def list_potion_names(self) -> list[str]:
        if self._potion_names is None:
            self._potion_names = self._list_entity_names("potion")
        return self._potion_names

    def _list_entity_names(self, *entity_types: str) -> list[str]:
        try:
            if not entity_types:
                return []
            placeholders = ",".join("?" for _ in entity_types)
            rows = self.database.execute(
                f"""
                SELECT DISTINCT name
                FROM entity
                WHERE entity_type IN ({placeholders})
                  AND name IS NOT NULL
                  AND TRIM(name) <> ''
                ORDER BY name COLLATE NOCASE
                """,
                tuple(entity_types),
            ).fetchall()
            return [row["name"] for row in rows]
        except Exception:
            return []

    # --------------------------------------------------
    # Buff/debuff extraction helpers
    # --------------------------------------------------

    def buffs_for_sets(self, set_names: list[str]) -> list[str]:
        names = [str(name or "").strip() for name in set_names if str(name or "").strip()]
        if not names:
            return []
        placeholders = ",".join("?" for _ in names)
        try:
            rows = self.database.execute(
                f"""
                SELECT description
                FROM gear_set_bonus
                WHERE set_id IN (
                    SELECT id FROM gear_set WHERE name IN ({placeholders})
                )
                """,
                tuple(names),
            ).fetchall()
        except Exception:
            return []
        found: set[str] = set()
        for row in rows:
            for match in _BUFF_PATTERN.finditer(str(row["description"] or "")):
                found.add(match.group(0))
        return sorted(found, key=str.casefold)

    def suggest_watches_for_sets(self, set_names: list[str]) -> list[str]:
        """Backward-compatible public API used by Optimization/Capabilities.

        This is the same set-bonus Major/Minor extraction as ``buffs_for_sets``.
        Keep the established method name because UI callers use it during app
        startup and coverage rendering.
        """

        return self.buffs_for_sets(set_names)
