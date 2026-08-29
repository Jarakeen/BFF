from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .effects import Effect, EffectOperation, EffectUnit
from .stat_ids import StatId


_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_VALUE = r"([0-9]+(?:\.[0-9]+)?)"


@dataclass(frozen=True)
class ChampionPointRecord:
    name: str
    skill_type: int
    max_points: int
    jump_points: tuple[int, ...]
    description: str


class ChampionPointStaticRepository:
    """Resolve only unconditional static CP effects from canonical DB tooltips."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _clean(text: str | None) -> str:
        return _COLOR.sub("", str(text or "")).strip()

    def get(self, name: str) -> ChampionPointRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT name, skill_type, max_points, jump_points,
                       COALESCE(min_description, max_description, description, '') AS description
                FROM champion_point
                WHERE name = ?
                """,
                (str(name).strip(),),
            ).fetchone()
        if row is None:
            return None
        jumps = tuple(
            int(value)
            for value in str(row["jump_points"] or "").split(",")
            if str(value).strip().isdigit()
        )
        return ChampionPointRecord(
            name=str(row["name"]),
            skill_type=int(row["skill_type"] or 0),
            max_points=int(row["max_points"] or 0),
            jump_points=jumps,
            description=self._clean(row["description"]),
        )

    @staticmethod
    def _stages(record: ChampionPointRecord, points: int) -> int:
        allocated = max(0, min(int(points), record.max_points or int(points)))
        thresholds = tuple(value for value in record.jump_points if value > 0)
        if thresholds:
            return sum(1 for value in thresholds if allocated >= value)
        return allocated

    @staticmethod
    def _effects_for_simple_stat(name: str, stat: StatId, amount: float, unit: EffectUnit) -> list[Effect]:
        return [
            Effect(
                source=f"Champion Point: {name}",
                stat=stat,
                operation=EffectOperation.ADD_PERCENT if unit is EffectUnit.PERCENT else EffectOperation.ADD,
                value=amount,
                unit=unit,
            )
        ]

    def resolve(self, name: str, points: int) -> tuple[list[Effect], list[str]]:
        record = self.get(name)
        if record is None:
            return [], [f"Champion Point not found: {name}"]
        stages = self._stages(record, points)
        if stages <= 0:
            return [], []

        first_line = record.description.splitlines()[0].strip()
        source = record.name

        patterns: tuple[tuple[str, tuple[StatId, ...], EffectUnit], ...] = (
            (rf"^(?:Grants|Increases(?: your)?) {_VALUE} Max Health per stage\.$", (StatId.MAX_HEALTH,), EffectUnit.FLAT),
            (rf"^(?:Grants|Increases(?: your)?) {_VALUE} Max Magicka per stage\.$", (StatId.MAX_MAGICKA,), EffectUnit.FLAT),
            (rf"^(?:Grants|Increases(?: your)?) {_VALUE} Max Stamina per stage\.$", (StatId.MAX_STAMINA,), EffectUnit.FLAT),
            (rf"^Grants {_VALUE} Armor per stage\.$", (StatId.PHYSICAL_RESISTANCE, StatId.SPELL_RESISTANCE), EffectUnit.FLAT),
            (rf"^Grants {_VALUE} Offensive Penetration per stage\.$", (StatId.PHYSICAL_PENETRATION, StatId.SPELL_PENETRATION), EffectUnit.FLAT),
            (rf"^Grants {_VALUE} Critical Chance per stage\.$", (StatId.CRITICAL_CHANCE,), EffectUnit.FLAT),
            (rf"^Grants {_VALUE} Critical Resistance per stage\.$", (StatId.CRITICAL_RESISTANCE,), EffectUnit.FLAT),
            (rf"^Increases your Healing Done by {_VALUE}% per stage\.$", (StatId.HEALING_DONE,), EffectUnit.PERCENT),
            (rf"^Increases your healing received by {_VALUE}% per stage\.$", (StatId.HEALING_TAKEN,), EffectUnit.PERCENT),
            (rf"^Increases your Weapon and Spell Damage by {_VALUE} per stage\.$", (StatId.WEAPON_DAMAGE, StatId.SPELL_DAMAGE), EffectUnit.FLAT),
            (rf"^Grants {_VALUE} Health, Magicka, and Stamina Recovery per stage\.$", (StatId.HEALTH_RECOVERY, StatId.MAGICKA_RECOVERY, StatId.STAMINA_RECOVERY), EffectUnit.FLAT),
        )

        for pattern, stats, unit in patterns:
            match = re.match(pattern, first_line, flags=re.IGNORECASE)
            if not match:
                continue
            per_stage = float(match.group(1))
            amount = per_stage * stages
            effects: list[Effect] = []
            for stat in stats:
                effects.extend(self._effects_for_simple_stat(source, stat, amount, unit))
            return effects, []

        finesse = re.match(
            rf"^Increases your Critical Damage and Critical Healing done by {_VALUE}% per stage\.$",
            first_line,
            flags=re.IGNORECASE,
        )
        if finesse:
            amount = float(finesse.group(1)) * stages
            return (
                self._effects_for_simple_stat(source, StatId.CRITICAL_DAMAGE, amount, EffectUnit.PERCENT),
                [f"Champion Point: {source} critical healing is outside the current character-sheet StatId layer"],
            )

        return [], [f"Champion Point is dynamic or not yet stat-mapped: {source}"]
