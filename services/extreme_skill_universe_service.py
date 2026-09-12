from __future__ import annotations

"""Canonical all-player-skill inventory for Extreme Builds.

This service deliberately inventories *every* player skill/passive in ``eso.db``
instead of assuming the Extreme engine only cares about class skill lines.  It
classifies skill-line families so combat-capable shared lines can participate in
Extreme candidate generation while crafting/utility lines remain visible as
known non-combat data rather than disappearing from coverage reports.

The service does not infer mechanical value from prose.  It exposes canonical
identity, max-rank descriptions, and bar-eligibility metadata; effect projection
belongs to separate reviewed services.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
import sqlite3

from minmax.character_build.character_class import CLASS_SKILL_LINES
from services.skill_bar_eligibility import (
    NON_COMBAT_SKILL_LINES,
    SHARED_COMBAT_SKILL_LINES,
    VAMPIRE_SKILL_LINE,
    WEREWOLF_SKILL_LINE,
    is_eligible,
    is_ultimate,
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _clean(value).casefold()


class ExtremeSkillDomain(str, Enum):
    CLASS = "class"
    WEAPON = "weapon"
    ARMOR = "armor"
    GUILD = "guild"
    ALLIANCE_WAR = "alliance_war"
    WORLD = "world"
    RACIAL = "racial"
    CRAFT = "craft"
    UTILITY = "utility"
    OTHER = "other"


WEAPON_LINES = frozenset(
    {
        "two handed",
        "one hand and shield",
        "dual wield",
        "bow",
        "destruction staff",
        "restoration staff",
    }
)
ARMOR_LINES = frozenset({"light armor", "medium armor", "heavy armor"})
GUILD_LINES = frozenset(
    {
        "fighters guild",
        "mages guild",
        "psijic order",
        "undaunted",
        "thieves guild",
        "dark brotherhood",
    }
)
ALLIANCE_LINES = frozenset({"assault", "support"})
WORLD_LINES = frozenset({"soul magic", VAMPIRE_SKILL_LINE, WEREWOLF_SKILL_LINE})
CRAFT_LINES = frozenset(
    {
        "alchemy",
        "blacksmithing",
        "clothing",
        "enchanting",
        "jewelry crafting",
        "provisioning",
        "woodworking",
        "scribing",
        "crafting",
    }
)
UTILITY_LINES = frozenset({"excavation", "legerdemain", "scrying"})

_CLASS_LINE_NAMES = frozenset(
    line.casefold()
    for lines in CLASS_SKILL_LINES.values()
    for line in lines
)
_RACE_LINE_RE = re.compile(r".+\s+skills$", re.IGNORECASE)


@dataclass(frozen=True)
class ExtremePlayerSkillRecord:
    skill_id: int
    name: str
    class_type: str
    skill_line: str
    skill_type: str
    is_passive: bool
    is_player: bool
    is_crafted: bool
    base_ability_id: int | None
    max_rank: int | None
    max_rank_ability_id: int | None
    description: str
    domain: ExtremeSkillDomain

    @property
    def line_key(self) -> str:
        return _key(self.skill_line)

    @property
    def combat_line(self) -> bool:
        line = self.line_key
        if self.domain is ExtremeSkillDomain.CLASS:
            return True
        return line in SHARED_COMBAT_SKILL_LINES or line in {
            VAMPIRE_SKILL_LINE,
            WEREWOLF_SKILL_LINE,
        }

    @property
    def known_noncombat_line(self) -> bool:
        return self.line_key in NON_COMBAT_SKILL_LINES or self.domain in {
            ExtremeSkillDomain.CRAFT,
            ExtremeSkillDomain.UTILITY,
            ExtremeSkillDomain.RACIAL,
        }


class ExtremeSkillUniverseService:
    """Enumerate every canonical player skill and passive from ``eso.db``."""

    # Exhaustive Extreme scoring constructs many service instances against the same
    # immutable canonical database. The full player-skill inventory is patch-scoped
    # evidence, not candidate state, so load it once per resolved database path for
    # the life of the audit process. A new audit process naturally gets a fresh view.
    _production_universe_cache: dict[str, tuple[ExtremePlayerSkillRecord, ...]] = {}

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def classify_domain(*, class_type: object, skill_line: object) -> ExtremeSkillDomain:
        owner = _key(class_type)
        line = _key(skill_line)
        if owner or line in _CLASS_LINE_NAMES:
            return ExtremeSkillDomain.CLASS
        if line in WEAPON_LINES:
            return ExtremeSkillDomain.WEAPON
        if line in ARMOR_LINES:
            return ExtremeSkillDomain.ARMOR
        if line in GUILD_LINES:
            return ExtremeSkillDomain.GUILD
        if line in ALLIANCE_LINES:
            return ExtremeSkillDomain.ALLIANCE_WAR
        if line in WORLD_LINES:
            return ExtremeSkillDomain.WORLD
        if line in CRAFT_LINES:
            return ExtremeSkillDomain.CRAFT
        if line in UTILITY_LINES:
            return ExtremeSkillDomain.UTILITY
        if line == "racial" or _RACE_LINE_RE.fullmatch(_clean(skill_line)):
            return ExtremeSkillDomain.RACIAL
        return ExtremeSkillDomain.OTHER

    @staticmethod
    def _columns(db: sqlite3.Connection, table: str) -> set[str]:
        return {
            str(row[1])
            for row in db.execute(f"PRAGMA table_info({table})").fetchall()
        }

    def all_player_skills(self) -> tuple[ExtremePlayerSkillRecord, ...]:
        if not self.database_path.is_file():
            return ()

        cache_key = str(self.database_path.resolve())
        cached = self._production_universe_cache.get(cache_key)
        if cached is not None:
            return cached

        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            skill_columns = self._columns(db, "skill")
            rank_columns = self._columns(db, "skill_rank")
            ability_columns = self._columns(db, "ability")
            required = {"id", "name", "is_passive"}
            if not required.issubset(skill_columns):
                result: tuple[ExtremePlayerSkillRecord, ...] = ()
                self._production_universe_cache[cache_key] = result
                return result

            def skill_expr(column: str, default: str) -> str:
                return f"s.{column}" if column in skill_columns else f"{default} AS {column}"

            has_ranks = {"skill_id", "rank", "ability_id"}.issubset(rank_columns)
            rank_join = ""
            rank_select = "NULL AS max_rank, NULL AS max_rank_ability_id"
            ability_join = ""
            concrete_description = "'' AS concrete_description"
            if has_ranks:
                rank_join = """
                    LEFT JOIN (
                        SELECT skill_id, MAX(rank) AS max_rank
                        FROM skill_rank
                        GROUP BY skill_id
                    ) r ON r.skill_id = s.id
                    LEFT JOIN skill_rank sr
                      ON sr.skill_id = s.id
                     AND sr.rank = r.max_rank
                """
                rank_select = "r.max_rank AS max_rank, MAX(sr.ability_id) AS max_rank_ability_id"
                if {"ability_id", "description"}.issubset(ability_columns):
                    ability_join = "LEFT JOIN ability a ON a.ability_id = sr.ability_id"
                    concrete_description = "MAX(COALESCE(NULLIF(a.description, ''), '')) AS concrete_description"

            query = f"""
                SELECT
                    s.id,
                    s.name,
                    {skill_expr('class_type', "''")},
                    {skill_expr('skill_line', "''")},
                    {skill_expr('skill_type', "''")},
                    s.is_passive,
                    {skill_expr('is_player', '1')},
                    {skill_expr('is_crafted', '0')},
                    {skill_expr('base_ability_id', 'NULL')},
                    {skill_expr('description', "''")},
                    {rank_select},
                    {concrete_description}
                FROM skill s
                {rank_join}
                {ability_join}
                WHERE COALESCE({skill_expr('is_player', '1').split(' AS ')[0]}, 1) != 0
                GROUP BY s.id
                ORDER BY
                    COALESCE({skill_expr('class_type', "''").split(' AS ')[0]}, '') COLLATE NOCASE,
                    COALESCE({skill_expr('skill_line', "''").split(' AS ')[0]}, '') COLLATE NOCASE,
                    s.name COLLATE NOCASE,
                    s.id
            """
            rows = db.execute(query).fetchall()

        records: list[ExtremePlayerSkillRecord] = []
        for row in rows:
            description = _clean(row["concrete_description"] or row["description"])
            class_type = _clean(row["class_type"])
            skill_line = _clean(row["skill_line"])
            records.append(
                ExtremePlayerSkillRecord(
                    skill_id=int(row["id"]),
                    name=_clean(row["name"]),
                    class_type=class_type,
                    skill_line=skill_line,
                    skill_type=_clean(row["skill_type"]),
                    is_passive=bool(row["is_passive"]),
                    is_player=bool(row["is_player"]),
                    is_crafted=bool(row["is_crafted"]),
                    base_ability_id=(
                        int(row["base_ability_id"])
                        if row["base_ability_id"] is not None
                        else None
                    ),
                    max_rank=(int(row["max_rank"]) if row["max_rank"] is not None else None),
                    max_rank_ability_id=(
                        int(row["max_rank_ability_id"])
                        if row["max_rank_ability_id"] is not None
                        else None
                    ),
                    description=description,
                    domain=self.classify_domain(
                        class_type=class_type,
                        skill_line=skill_line,
                    ),
                )
            )
        result = tuple(records)
        self._production_universe_cache[cache_key] = result
        return result

    def passives(self) -> tuple[ExtremePlayerSkillRecord, ...]:
        return tuple(row for row in self.all_player_skills() if row.is_passive)

    def actives(self) -> tuple[ExtremePlayerSkillRecord, ...]:
        return tuple(row for row in self.all_player_skills() if not row.is_passive)

    def by_domain(self, domain: ExtremeSkillDomain) -> tuple[ExtremePlayerSkillRecord, ...]:
        return tuple(row for row in self.all_player_skills() if row.domain is domain)

    @staticmethod
    def bar_eligible(
        row: ExtremePlayerSkillRecord,
        *,
        character_class: str | None,
        slot_index: int,
        vampire: bool = False,
        werewolf: bool = False,
        transformed_form: str | None = None,
    ) -> bool:
        if row.is_passive or row.max_rank_ability_id is None:
            return False
        synthetic = {
            "ability_id": row.max_rank_ability_id,
            "base_ability_id": row.base_ability_id or row.max_rank_ability_id,
            "name": row.name,
            "class_type": row.class_type,
            "skill_line": row.skill_line,
            "is_passive": 0,
            "is_player": 1,
            "is_crafted": int(row.is_crafted),
            "base_mechanic": 8 if "ultimate" in row.skill_type.casefold() else 0,
        }
        return is_eligible(
            synthetic,
            character_class=character_class,
            slot_index=slot_index,
            vampire=vampire,
            werewolf=werewolf,
            transformed_form=transformed_form,
        )
