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


# Reviewed H1 dispositions for ability-altering weapon sets whose composite
# two-piece text is intentionally broader than the generic static set resolver.
# These rows are source-reviewed from the normalized ESO-Hub corpus. "standing"
# means the set has an always-on H1-relevant stat contribution, "conditional"
# means the contribution belongs to runtime/event-state evaluation, and
# "standing_and_conditional" carries both. "irrelevant" means the mechanic does
# not alter the selected H1 heal-event magnitude for that objective.
_ARENA_H1_DISPOSITIONS: dict[tuple[str, str], str] = {
    ("caustic arrow", "spell_damage"): "irrelevant",
    ("caustic arrow", "weapon_damage"): "irrelevant",
    ("perfected caustic arrow", "spell_damage"): "standing",
    ("perfected caustic arrow", "weapon_damage"): "standing",
    ("chaotic whirlwind", "spell_damage"): "conditional",
    ("chaotic whirlwind", "weapon_damage"): "conditional",
    ("perfected chaotic whirlwind", "spell_damage"): "conditional",
    ("perfected chaotic whirlwind", "weapon_damage"): "conditional",
    ("cruel flurry", "spell_damage"): "irrelevant",
    ("cruel flurry", "weapon_damage"): "irrelevant",
    ("perfected cruel flurry", "spell_damage"): "standing",
    ("perfected cruel flurry", "weapon_damage"): "standing",
    ("destructive impact", "spell_damage"): "conditional",
    ("destructive impact", "weapon_damage"): "conditional",
    ("perfected destructive impact", "spell_damage"): "standing_and_conditional",
    ("perfected destructive impact", "weapon_damage"): "standing_and_conditional",
    ("perfected concentrated force", "spell_damage"): "standing",
    ("perfected concentrated force", "weapon_damage"): "standing",
    ("frenzied momentum", "spell_damage"): "conditional",
    ("frenzied momentum", "weapon_damage"): "conditional",
    ("perfected frenzied momentum", "spell_damage"): "conditional",
    ("perfected frenzied momentum", "weapon_damage"): "conditional",
    ("perfected frenzied momentum", "max_stamina"): "standing",
    ("perfected disciplined slash", "max_stamina"): "standing",
    ("perfected force overflow", "max_magicka"): "standing",
    ("perfected grand rejuvenation", "max_magicka"): "standing",
    ("perfected timeless blessing", "max_magicka"): "standing",
    ("perfected void bash", "max_health"): "standing",
    ("perfected point-blank snipe", "spell_damage"): "standing",
    ("perfected point-blank snipe", "weapon_damage"): "standing",
    ("puncturing remedy", "healing_done"): "irrelevant",
    ("perfected puncturing remedy", "healing_done"): "irrelevant",
}


# Reviewed dispositions for the remaining special-set mechanics that the generic
# static resolver intentionally leaves fail-closed. "package" means the mechanic
# is deterministic from the equipped package/topology rather than runtime event
# state, and therefore belongs to package-search proof rather than proc uptime.
_SPECIAL_H1_DISPOSITIONS: dict[tuple[str, str, str], str] = {
    # Monster sets: all six outstanding power effects are trigger/state owned.
    **{
        ("monster", name, objective): "conditional"
        for name in (
            "balorgh",
            "domihaus",
            "magma incarnate",
            "molag kena",
            "stone husk",
            "zoal the ever-wakeful",
        )
        for objective in ("spell_damage", "weapon_damage")
    },

    # Mythics.
    **{
        ("mythic", "death dealer's fete", objective): "conditional"
        for objective in ("max_health", "max_magicka", "max_stamina")
    },
    ("mythic", "markyn ring of majesty", "spell_damage"): "package",
    ("mythic", "markyn ring of majesty", "weapon_damage"): "package",

    ("mythic", "oakensoul ring", "healing_done"): "standing_and_package",
    ("mythic", "oakensoul ring", "critical_healing"): "package",
    ("mythic", "oakensoul ring", "spell_damage"): "standing_and_package",
    ("mythic", "oakensoul ring", "weapon_damage"): "standing_and_package",
    ("mythic", "oakensoul ring", "max_health"): "package",
    ("mythic", "oakensoul ring", "max_magicka"): "package",
    ("mythic", "oakensoul ring", "max_stamina"): "package",

    ("mythic", "prowler's talisman", "max_magicka"): "conditional",
    ("mythic", "prowler's talisman", "max_stamina"): "conditional",
    ("mythic", "sea-serpent's coil", "spell_damage"): "conditional",
    ("mythic", "sea-serpent's coil", "weapon_damage"): "conditional",
    **{
        ("mythic", "shapeshifter's chain", objective): "conditional"
        for objective in ("max_health", "max_magicka", "max_stamina")
    },

    # Aura of Pride benefits other group members; the wearer pays the recovery
    # cost and does not receive the 260 Weapon/Spell Damage self-H1 modifier.
    ("mythic", "spaulder of ruin", "spell_damage"): "irrelevant",
    ("mythic", "spaulder of ruin", "weapon_damage"): "irrelevant",

    ("mythic", "the saint and the seducer", "spell_damage"): "conditional",
    ("mythic", "the saint and the seducer", "weapon_damage"): "conditional",
    ("mythic", "thrassian stranglers", "spell_damage"): "conditional",
    ("mythic", "thrassian stranglers", "weapon_damage"): "conditional",
    ("mythic", "thrassian stranglers", "max_health"): "conditional",

    ("mythic", "torc of the last ayleid king", "healing_done"): "package",
    ("mythic", "torc of the last ayleid king", "critical_healing"): "package",
    ("mythic", "torc of the last ayleid king", "spell_damage"): "standing_and_package",
    ("mythic", "torc of the last ayleid king", "weapon_damage"): "standing_and_package",
    ("mythic", "torc of the last ayleid king", "max_health"): "package",
    ("mythic", "torc of the last ayleid king", "max_magicka"): "package",
    ("mythic", "torc of the last ayleid king", "max_stamina"): "package",
}


@dataclass(frozen=True)
class ExtremeActualHealSpecialGearDisposition:
    set_id: int
    set_name: str
    family: str
    relevant_objectives: tuple[str, ...]
    conditional_objectives: tuple[str, ...] = ()
    package_objectives: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved

    @property
    def h1_relevant(self) -> bool:
        return bool(
            self.relevant_objectives
            or self.conditional_objectives
            or self.package_objectives
        )


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

    @staticmethod
    def special_h1_disposition(
        family: str,
        set_name: str,
        objective: str,
    ) -> str | None:
        key = (
            str(family or "").strip().casefold(),
            " ".join(str(set_name or "").strip().casefold().split()),
            str(objective or "").strip().casefold(),
        )
        return _SPECIAL_H1_DISPOSITIONS.get(key)

    @staticmethod
    def arena_h1_disposition(set_name: str, objective: str) -> str | None:
        key = (
            " ".join(str(set_name or "").strip().casefold().split()),
            str(objective or "").strip().casefold(),
        )
        return _ARENA_H1_DISPOSITIONS.get(key)

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
                    conditional_objectives=(),
                    package_objectives=(),
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
            conditional: list[str] = []
            package: list[str] = []
            unresolved: list[str] = []
            for objective in H1_GEAR_OBJECTIVES:
                candidate = ExtremeGearSetObjectiveService.candidate_for_set(
                    self.repository,
                    gear_set.name,
                    objective,
                )

                disposition = None
                if family == "arena_weapon":
                    disposition = self.arena_h1_disposition(
                        gear_set.name,
                        objective,
                    )
                elif family in {"monster", "mythic"}:
                    disposition = self.special_h1_disposition(
                        family,
                        gear_set.name,
                        objective,
                    )

                if disposition == "irrelevant":
                    continue
                if disposition == "standing":
                    relevant.append(objective)
                    continue
                if disposition == "conditional":
                    conditional.append(objective)
                    continue
                if disposition == "package":
                    package.append(objective)
                    continue
                if disposition == "standing_and_conditional":
                    relevant.append(objective)
                    conditional.append(objective)
                    continue
                if disposition == "standing_and_package":
                    relevant.append(objective)
                    package.append(objective)
                    continue

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
                    conditional_objectives=tuple(dict.fromkeys(conditional)),
                    package_objectives=tuple(dict.fromkeys(package)),
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
