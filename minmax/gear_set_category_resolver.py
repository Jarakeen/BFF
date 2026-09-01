from __future__ import annotations

import sqlite3
from pathlib import Path

from .character_build.gear_piece import GearPieceCategory


class GearSetCategoryResolver:
    """Resolve canonical gear-piece category from imported set structure.

    The raw gear_set.category field is preserved as source evidence, but older
    imports only distinguish a few categories reliably. Structural fallback is
    therefore used for categories the canonical build model must know:

    - one-piece, one-slot, non-weapon sets -> mythic
    - two-piece head+shoulders-only non-weapon sets -> monster set

    Unknown or incomplete structures remain ordinary set pieces rather than
    being guessed into a special category.
    """

    # UESP/ESO mined-item equipType values observed in the imported set data.
    # Magma Incarnate verifies the head+shoulders pair as 1 and 4.
    HEAD_EQUIP_TYPE = 1
    SHOULDERS_EQUIP_TYPE = 4

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

    def resolve(
        self,
        set_id: int,
        *,
        raw_category: str | None = None,
    ) -> GearPieceCategory:
        category = str(raw_category or "").strip().casefold()
        if "mythic" in category:
            return GearPieceCategory.MYTHIC
        if "monster" in category:
            return GearPieceCategory.MONSTER_SET

        structure = self._structure(set_id)
        if structure is None:
            return GearPieceCategory.SET_PIECE

        max_equip_count, equip_types, has_weapon_piece, source_item_count = structure

        if (
            max_equip_count == 1
            and len(equip_types) == 1
            and not has_weapon_piece
            and source_item_count == 1
        ):
            return GearPieceCategory.MYTHIC

        if (
            max_equip_count == 2
            and equip_types == {self.HEAD_EQUIP_TYPE, self.SHOULDERS_EQUIP_TYPE}
            and not has_weapon_piece
        ):
            return GearPieceCategory.MONSTER_SET

        return GearPieceCategory.SET_PIECE

    def _structure(
        self,
        set_id: int,
    ) -> tuple[int | None, set[int], bool, int] | None:
        with sqlite3.connect(self.database_path) as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            required = {"gear_set", "gear_set_piece"}
            if not required.issubset(tables):
                return None

            row = connection.execute(
                "SELECT max_equip_count FROM gear_set WHERE id = ?",
                (set_id,),
            ).fetchone()
            if row is None:
                return None

            piece_rows = connection.execute(
                """
                SELECT equip_type, weapon_type
                FROM gear_set_piece
                WHERE set_id = ?
                """,
                (set_id,),
            ).fetchall()
            if not piece_rows:
                return None

            equip_types = {
                int(equip_type)
                for equip_type, _weapon_type in piece_rows
                if equip_type is not None
            }
            has_weapon_piece = any(
                weapon_type is not None and int(weapon_type) > 0
                for _equip_type, weapon_type in piece_rows
            )

            source_item_count = 0
            if "gear_set_item" in tables:
                source_item_count = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM gear_set_item WHERE set_id = ?",
                        (set_id,),
                    ).fetchone()[0]
                )

        max_equip_count = int(row[0]) if row[0] is not None else None
        return max_equip_count, equip_types, has_weapon_piece, source_item_count
