from __future__ import annotations

"""Canonical special-gear denominator for Extreme MOST Actual Heal.

Ordinary five-piece sets already have their own reconciled denominator. This
service inventories the remaining special package families that H1 can equip:
monster sets, mythics, and structurally proven arena-weapon sets. Every canonical
member receives one fail-closed disposition against the reviewed H1 stat
objectives. Runtime proc activation remains a separate scenario layer.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.character_build.gear_piece import GearPieceCategory
from minmax.gear_set_category_resolver import GearSetCategoryResolver
from minmax.gear_set_repository import GearSetRepository
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


H1_GEAR_OBJECTIVES = (
    "healing_done",
    "critical_healing",
    "spell_damage",
    "weapon_damage",
    "max_health",
    "max_magicka",
    "max_stamina",
)


@dataclass(frozen=True)
class ExtremeActualHealSpecialGearDisposition:
    set_id: int
    set_name: str
    family: str
    relevant_objectives: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved

    @property
    def h1_relevant(self) -> bool:
        return bool(self.relevant_objectives)


@dataclass(frozen=True)
class ExtremeActualHealSpecialGearDenominator:
    rows: tuple[ExtremeActualHealSpecialGearDisposition, ...]

    @property
    def monster_count(self) -> int:
        return sum(row.family == "monster" for row in self.rows)

    @property
    def mythic_count(self) -> int:
        return sum(row.family == "mythic" for row in self.rows)

    @property
    def arena_weapon_count(self) -> int:
        return sum(row.family == "arena_weapon" for row in self.rows)

    @property
    def entity_only_count(self) -> int:
        return sum(row.family == "entity_only" for row in self.rows)

    @property
    def unresolved_rows(self) -> tuple[ExtremeActualHealSpecialGearDisposition, ...]:
        return tuple(row for row in self.rows if row.unresolved)

    @property
    def relevant_rows(self) -> tuple[ExtremeActualHealSpecialGearDisposition, ...]:
        return tuple(row for row in self.rows if row.h1_relevant)

    @property
    def denominator_proven(self) -> bool:
        return bool(self.rows) and not self.unresolved_rows


class ExtremeActualHealSpecialGearDenominatorService:
    def __init__(
        self,
        database_path: str | Path,
        *,
        repository: GearSetRepository | None = None,
        categories: GearSetCategoryResolver | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.repository = repository or GearSetRepository(self.database_path)
        self.categories = categories or GearSetCategoryResolver(self.database_path)

    def _arena_weapon_ids(self) -> frozenset[int]:
        if not self.database_path.is_file():
            return frozenset()
        with sqlite3.connect(self.database_path) as db:
            tables = {
                str(row[0])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if not {"gear_set", "gear_set_piece"}.issubset(tables):
                return frozenset()
            set_rows = db.execute(
                """
                SELECT id
                FROM gear_set
                WHERE max_equip_count = 2
                ORDER BY id
                """
            ).fetchall()
            arena: set[int] = set()
            for (set_id,) in set_rows:
                rows = db.execute(
                    """
                    SELECT COALESCE(armor_type, 0), COALESCE(weapon_type, 0)
                    FROM gear_set_piece
                    WHERE set_id = ?
                    """,
                    (int(set_id),),
                ).fetchall()
                if rows and all(
                    int(armor_type or 0) == 0 and int(weapon_type or 0) > 0
                    for armor_type, weapon_type in rows
                ):
                    arena.add(int(set_id))
        return frozenset(arena)

    def _family(self, gear_set, arena_ids: frozenset[int]) -> str | None:
        category = self.categories.resolve(
            gear_set.id,
            raw_category=gear_set.category,
        )
        if category is GearPieceCategory.MONSTER_SET:
            return "monster"
        if category is GearPieceCategory.MYTHIC:
            return "mythic"
        if int(gear_set.id) in arena_ids:
            return "arena_weapon"
        return None

    def _entity_only_rows(self) -> tuple[ExtremeActualHealSpecialGearDisposition, ...]:
        """Expose canonical gear-set entities not yet normalized into gear_set.

        The build editor deliberately exposes the union of gear_set and canonical
        entity rows. Extreme must audit the same universe. Entity-only rows cannot
        be silently treated as absent, because arena weapons are known to arrive
        through this path before their set bonus/slot structure is normalized.
        """
        if not self.database_path.is_file():
            return ()
        with sqlite3.connect(self.database_path) as db:
            tables = {
                str(row[0])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "entity" not in tables or "gear_set" not in tables:
                return ()
            rows = db.execute(
                """
                SELECT e.id, e.name
                FROM entity e
                LEFT JOIN gear_set gs
                  ON LOWER(TRIM(gs.name)) = LOWER(TRIM(e.name))
                WHERE e.entity_type = 'gear_set'
                  AND e.name IS NOT NULL
                  AND TRIM(e.name) <> ''
                  AND gs.id IS NULL
                ORDER BY e.name COLLATE NOCASE, e.id
                """
            ).fetchall()

        result: list[ExtremeActualHealSpecialGearDisposition] = []
        for _raw_id, raw_name in rows:
            name = str(raw_name or "").strip()
            result.append(
                ExtremeActualHealSpecialGearDisposition(
                    set_id=-1,
                    set_name=name,
                    family="entity_only",
                    relevant_objectives=(),
                    unresolved=(
                        "canonical gear-set entity is selectable but lacks normalized "
                        "gear_set / gear_set_piece / gear_set_bonus evidence",
                    ),
                )
            )
        return tuple(result)

    def build(self) -> ExtremeActualHealSpecialGearDenominator:
        arena_ids = self._arena_weapon_ids()
        rows: list[ExtremeActualHealSpecialGearDisposition] = []

        for gear_set in self.repository.list_sets():
            family = self._family(gear_set, arena_ids)
            if family is None:
                continue

            relevant: list[str] = []
            unresolved: list[str] = []
            for objective in H1_GEAR_OBJECTIVES:
                candidate = ExtremeGearSetObjectiveService.candidate_for_set(
                    self.repository,
                    gear_set.name,
                    objective,
                )
                if candidate.unresolved:
                    unresolved.extend(
                        f"{objective}: {message}"
                        for message in candidate.unresolved
                    )
                elif float(candidate.reviewed_delta) > 0.0:
                    relevant.append(objective)

            rows.append(
                ExtremeActualHealSpecialGearDisposition(
                    set_id=int(gear_set.id),
                    set_name=str(gear_set.name),
                    family=family,
                    relevant_objectives=tuple(dict.fromkeys(relevant)),
                    unresolved=tuple(dict.fromkeys(unresolved)),
                )
            )

        rows.extend(self._entity_only_rows())

        return ExtremeActualHealSpecialGearDenominator(
            rows=tuple(
                sorted(
                    rows,
                    key=lambda row: (row.family, row.set_name.casefold(), row.set_id),
                )
            )
        )


__all__ = [
    "H1_GEAR_OBJECTIVES",
    "ExtremeActualHealSpecialGearDisposition",
    "ExtremeActualHealSpecialGearDenominator",
    "ExtremeActualHealSpecialGearDenominatorService",
]
