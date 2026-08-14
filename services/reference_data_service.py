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

        if self._gear_set_names is None:

            try:

                rows = self.database.execute(
                    "SELECT name FROM gear_set ORDER BY name"
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
        Return structured skill records for the Build Editor.

        These records retain the metadata needed for:
        - class filtering
        - combat filtering
        - passive filtering
        - ultimate filtering
        - ESO skill icons
        """

        if self._skill_rows is None:

            try:

                rows = self.database.execute(
                    """
                    SELECT
                        s.id,
                        s.base_ability_id,
                        s.name,
                        s.index_name,
                        s.description,
                        s.texture,
                        s.class_type,
                        s.skill_line,
                        s.target,
                        s.skill_type,
                        s.is_passive,
                        s.is_player,
                        s.is_crafted,
                        s.crafted_id,

                        a.base_mechanic,
                        a.cost,
                        a.buff_type

                    FROM skill s

                    LEFT JOIN ability a
                        ON a.base_ability_id = s.base_ability_id

                    WHERE s.name IS NOT NULL
                    AND s.name != ''

                    ORDER BY s.name
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
                        jump_point_delta,
                        num_jump_points,
                        is_root,
                        is_cluster_root,
                        parent_skill_id,
                        skill_index,
                        discipline_index
                    FROM champion_point
                    WHERE name IS NOT NULL
                    AND name != ''
                    ORDER BY discipline_id, name
                    """
                ).fetchall()

                self._cp_rows = [dict(row) for row in rows]

            except Exception:
                self._cp_rows = []

        return self._cp_rows

    def champion_point_discipline(self, discipline_id: int) -> str:
        """Return the ESO Champion Point discipline name."""

        return {
            1: "Warfare",
            2: "Fitness",
            3: "Craft",
        }.get(discipline_id, "Unknown")

    def champion_point_discipline_color(self, discipline_id: int) -> str:
        """Return the display color associated with an ESO CP discipline."""

        return {
            1: "blue",
            2: "red",
            3: "green",
        }.get(discipline_id, "")
    # --------------------------------------------------
    # Suggestions
    # --------------------------------------------------

    def suggest_watches_for_sets(
        self,
        set_names: list[str],
    ) -> list[str]:
        """
        Given a list of equipped gear set names, return the
        Major/Minor buffs and debuffs their set bonus text
        mentions -- a starting point for "what should I
        watch" on the Capabilities page, not a guarantee the
        set was slotted for that buff specifically.
        """

        names = [n for n in set_names if n]

        if not names:
            return []

        found: list[str] = []

        seen: set[str] = set()

        try:

            placeholders = ",".join("?" for _ in names)

            rows = self.database.execute(
                f"""
                SELECT gsb.description
                FROM gear_set_bonus gsb
                JOIN gear_set gs ON gs.id = gsb.set_id
                WHERE gs.name IN ({placeholders})
                """,
                tuple(names),
            ).fetchall()

            for row in rows:

                description = row["description"] or ""

                for match in _BUFF_PATTERN.finditer(description):

                    buff = match.group(0).strip()

                    key = buff.casefold()

                    if key not in seen:

                        seen.add(key)

                        found.append(buff)

        except Exception:
            return []

        return sorted(found)

    def list_food_names(self) -> list[str]:
        if self._food_names is None:
            try:
                rows = self.database.execute(
                    """
                    SELECT DISTINCT name
                    FROM food
                    WHERE name IS NOT NULL
                    AND name != ''
                    ORDER BY name
                    """
                ).fetchall()

                self._food_names = [
                    row["name"]
                    for row in rows
                ]

            except Exception as exc:
                print("FOOD QUERY ERROR:", repr(exc))
                self._food_names = []

        return self._food_names


    def list_potion_names(self) -> list[str]:
        if self._potion_names is None:
            try:
                rows = self.database.execute(
                    """
                    SELECT name
                    FROM entity
                    WHERE entity_type = 'potion'
                    ORDER BY name
                    """
                ).fetchall()

                self._potion_names = [
                    row["name"]
                    for row in rows
                ]

            except Exception as exc:
                print("POTION QUERY ERROR:", repr(exc))
                self._potion_names = []

        return self._potion_names

    def list_food_names(self) -> list[str]:

        if self._food_names is None:
            try:
                rows = self.database.execute(
                    """
                    SELECT name
                    FROM entity
                    WHERE entity_type = 'food'
                    AND name IS NOT NULL
                    AND name != ''
                    ORDER BY name
                    """
                ).fetchall()

                self._food_names = [
                    row["name"]
                    for row in rows
                ]

            except Exception as exc:
                print(
                    "FOOD QUERY ERROR:",
                    repr(exc),
                )
                self._food_names = []

        return self._food_names
