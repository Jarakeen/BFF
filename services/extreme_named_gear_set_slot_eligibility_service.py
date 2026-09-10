from __future__ import annotations

"""Canonical named-set physical slot eligibility for Extreme gear search.

This layer turns ``gear_set_piece`` rows into a reusable legality contract.  It
answers which armor slots, jewelry slots, and weapon types a *specific named set*
can occupy.  Exact source rows are authoritative for special sets.  Standard
reconstructable five-piece sets may use the same reviewed missing-weapon
completion rule already used by Stickerbook; no other missing slot is invented.

The result is intentionally separate from set-count topology and physical-shape
realization.  Those layers answer different denominator questions and should not
be collapsed merely because 5+5+2 looks familiar.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.stickerbook_service import (
    EQUIP_TYPES,
    WEAPON_TYPES,
    StickerbookService,
    _STANDARD_WEAPON_EQUIP,
)


_ARMOR_EQUIP_TYPES = frozenset({1, 3, 4, 8, 9, 10, 13})
_JEWELRY_EQUIP_TYPES = frozenset({2, 12})


@dataclass(frozen=True)
class ExtremeNamedGearSetSlotEligibility:
    set_id: int
    name: str
    category: str
    max_equip_count: int
    armor_slots: tuple[str, ...] = ()
    jewelry_slots: tuple[str, ...] = ()
    weapon_types: tuple[str, ...] = ()
    synthetic_weapon_types: tuple[str, ...] = ()
    other_equip_types: tuple[int, ...] = ()

    @property
    def has_physical_slot_evidence(self) -> bool:
        return bool(
            self.armor_slots
            or self.jewelry_slots
            or self.weapon_types
            or self.other_equip_types
        )


@dataclass(frozen=True)
class ExtremeNamedGearSetSlotEligibilityCatalog:
    sets: tuple[ExtremeNamedGearSetSlotEligibility, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def named_set_slot_eligibility_proven(self) -> bool:
        return bool(self.sets) and all(
            item.has_physical_slot_evidence for item in self.sets
        ) and not self.unresolved

    def by_set_id(self, set_id: int) -> ExtremeNamedGearSetSlotEligibility | None:
        target = int(set_id)
        return next((item for item in self.sets if item.set_id == target), None)


class ExtremeNamedGearSetSlotEligibilityService:
    """Read named-set slot legality from canonical gear-set piece evidence."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _tables(connection: sqlite3.Connection) -> set[str]:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    @staticmethod
    def _source_by_set(connection: sqlite3.Connection) -> dict[int, tuple[str, str]]:
        tables = ExtremeNamedGearSetSlotEligibilityService._tables(connection)
        if not {"content", "content_sets"}.issubset(tables):
            return {}
        rows = connection.execute(
            """
            SELECT cs.set_id, COALESCE(c.content_type, ''), COALESCE(c.name, '')
            FROM content_sets cs
            JOIN content c ON c.id = cs.content_id
            ORDER BY c.name COLLATE NOCASE, c.id
            """
        ).fetchall()
        output: dict[int, tuple[str, str]] = {}
        for set_id, content_type, source in rows:
            output.setdefault(
                int(set_id),
                (str(content_type or "").strip(), str(source or "").strip()),
            )
        return output

    def build(self) -> ExtremeNamedGearSetSlotEligibilityCatalog:
        unresolved: list[str] = []
        rows_out: list[ExtremeNamedGearSetSlotEligibility] = []

        try:
            connection = sqlite3.connect(f"file:{self.database_path.resolve()}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            return ExtremeNamedGearSetSlotEligibilityCatalog(
                (), (f"Gear slot eligibility database unreadable: {exc}",)
            )

        with connection:
            tables = self._tables(connection)
            required = {"gear_set", "gear_set_piece"}
            if not required.issubset(tables):
                missing = ", ".join(sorted(required - tables))
                return ExtremeNamedGearSetSlotEligibilityCatalog(
                    (), (f"Gear slot eligibility database missing table(s): {missing}",)
                )

            source_map = self._source_by_set(connection)
            set_rows = connection.execute(
                """
                SELECT id, name, COALESCE(category, ''), max_equip_count
                FROM gear_set
                WHERE TRIM(COALESCE(name, '')) <> ''
                ORDER BY name COLLATE NOCASE, id
                """
            ).fetchall()

            for set_id_raw, name_raw, category_raw, max_count_raw in set_rows:
                set_id = int(set_id_raw)
                name = str(name_raw or "").strip()
                category = str(category_raw or "").strip()
                try:
                    max_count = int(max_count_raw or 0)
                except (TypeError, ValueError):
                    max_count = 0
                if max_count <= 0:
                    unresolved.append(
                        f"Gear set {name} has no positive canonical max_equip_count"
                    )

                piece_rows = connection.execute(
                    """
                    SELECT equip_type, armor_type, weapon_type
                    FROM gear_set_piece
                    WHERE set_id = ?
                    ORDER BY equip_type, armor_type, weapon_type
                    """,
                    (set_id,),
                ).fetchall()
                if not piece_rows:
                    unresolved.append(
                        f"Gear set {name} has no canonical gear_set_piece slot evidence"
                    )

                armor_slots: set[str] = set()
                jewelry_slots: set[str] = set()
                weapon_types: set[str] = set()
                other_equip_types: set[int] = set()
                existing_weapon_ids: set[int] = set()

                for equip_raw, _armor_raw, weapon_raw in piece_rows:
                    equip_id = int(equip_raw or 0)
                    weapon_id = int(weapon_raw or 0)
                    if weapon_id > 0:
                        label = WEAPON_TYPES.get(weapon_id)
                        if label is None:
                            unresolved.append(
                                f"Gear set {name} uses unknown canonical weapon_type {weapon_id}"
                            )
                        else:
                            weapon_types.add(label)
                            existing_weapon_ids.add(weapon_id)
                        continue
                    if equip_id in _ARMOR_EQUIP_TYPES:
                        armor_slots.add(EQUIP_TYPES[equip_id])
                    elif equip_id in _JEWELRY_EQUIP_TYPES:
                        jewelry_slots.add(EQUIP_TYPES[equip_id])
                    elif equip_id > 0:
                        other_equip_types.add(equip_id)
                        if equip_id not in EQUIP_TYPES:
                            unresolved.append(
                                f"Gear set {name} uses unknown canonical equip_type {equip_id}"
                            )

                content_type, source = source_map.get(set_id, ("", ""))
                bucket = StickerbookService._bucket(category, content_type, source)
                reconstructable_standard = StickerbookService._is_stickerbook_set(
                    category, content_type, source
                )
                missing_weapon_ids: tuple[int, ...] = ()
                if reconstructable_standard:
                    missing_weapon_ids = StickerbookService._missing_standard_weapon_types(
                        bucket=bucket,
                        max_equip_count=max_count,
                        existing_weapon_types=existing_weapon_ids,
                    )
                synthetic_weapon_types = tuple(
                    WEAPON_TYPES[weapon_id] for weapon_id in missing_weapon_ids
                )
                weapon_types.update(synthetic_weapon_types)

                rows_out.append(
                    ExtremeNamedGearSetSlotEligibility(
                        set_id=set_id,
                        name=name,
                        category=category,
                        max_equip_count=max_count,
                        armor_slots=tuple(sorted(armor_slots)),
                        jewelry_slots=tuple(sorted(jewelry_slots)),
                        weapon_types=tuple(sorted(weapon_types)),
                        synthetic_weapon_types=tuple(sorted(synthetic_weapon_types)),
                        other_equip_types=tuple(sorted(other_equip_types)),
                    )
                )

        return ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=tuple(rows_out),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
