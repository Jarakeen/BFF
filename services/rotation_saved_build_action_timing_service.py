from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from engine.config import get_data_dir
from minmax.rotation_action_cooldown import RotationActionCooldownRequirement
from minmax.rotation_action_occupancy import RotationActionOccupancyRequirement
from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild


DEFAULT_DATABASE = get_data_dir() / "eso.db"
_MILLISECONDS_PER_SECOND = 1000.0


@dataclass(frozen=True)
class RotationSavedBuildActionTimingEvidence:
    """Canonical action-timing requirements resolved from one saved build."""

    cooldown_requirements: tuple[RotationActionCooldownRequirement, ...] = ()
    occupancy_requirements: tuple[RotationActionOccupancyRequirement, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationSavedBuildActionTimingService:
    """Resolve cooldown and cast/channel occupancy for the build's slotted actions.

    The canonical skill importer stores ESO API timing values in milliseconds.
    Rotation schedules use seconds, so this bridge performs the unit conversion once
    at the data boundary. It does not invent a global cooldown, animation lock, or
    execution cadence. Zero/NULL timing means no requirement is emitted.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    def resolve(self, player_build: PlayerBuild) -> RotationSavedBuildActionTimingEvidence:
        slots = self._saved_slots(player_build)
        if not slots:
            return RotationSavedBuildActionTimingEvidence()

        if not self.database_path.exists():
            return RotationSavedBuildActionTimingEvidence(
                unresolved=(f"canonical skill timing database not found: {self.database_path}",)
            )

        cooldowns: dict[tuple[RotationActionKind, str], RotationActionCooldownRequirement] = {}
        occupancies: dict[tuple[RotationActionKind, str], RotationActionOccupancyRequirement] = {}
        unresolved: list[str] = []

        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            columns = {
                str(row[1])
                for row in db.execute("PRAGMA table_info(skill_rank)").fetchall()
            }
            required = {
                "skill_id",
                "ability_id",
                "rank",
                "raw_name",
                "cooldown",
                "cast_time",
                "channel_time",
            }
            if not required.issubset(columns):
                missing = ", ".join(sorted(required - columns))
                return RotationSavedBuildActionTimingEvidence(
                    unresolved=(f"canonical skill timing schema is missing: {missing}",)
                )

            for action_name, action_kind in slots:
                row = self._timing_row(db, action_name)
                if row is None:
                    unresolved.append(
                        f"canonical skill timing not found by exact saved name: {action_name}"
                    )
                    continue

                cooldown_seconds = self._seconds(row["cooldown"])
                occupancy_seconds = max(
                    self._seconds(row["cast_time"]),
                    self._seconds(row["channel_time"]),
                )
                key = (action_kind, action_name.casefold())

                if cooldown_seconds > 0:
                    cooldowns[key] = RotationActionCooldownRequirement(
                        action_name=action_name,
                        cooldown_seconds=cooldown_seconds,
                        action_kind=action_kind,
                    )
                if occupancy_seconds > 0:
                    occupancies[key] = RotationActionOccupancyRequirement(
                        action_name=action_name,
                        occupancy_seconds=occupancy_seconds,
                        action_kind=action_kind,
                    )

        return RotationSavedBuildActionTimingEvidence(
            cooldown_requirements=tuple(cooldowns.values()),
            occupancy_requirements=tuple(occupancies.values()),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _saved_slots(player_build: PlayerBuild) -> tuple[tuple[str, RotationActionKind], ...]:
        values: list[tuple[str, RotationActionKind]] = []
        front = tuple(getattr(player_build, "FrontBarSkills", ()) or ())
        back = tuple(getattr(player_build, "BackBarSkills", ()) or ())
        for names in (front, back):
            for index, raw_name in enumerate(names):
                name = str(raw_name or "").strip()
                if not name:
                    continue
                kind = (
                    RotationActionKind.ULTIMATE
                    if index == 5
                    else RotationActionKind.SKILL
                )
                values.append((name, kind))
        return tuple(values)

    @staticmethod
    def _timing_row(db: sqlite3.Connection, action_name: str) -> sqlite3.Row | None:
        return db.execute(
            """
            SELECT
                sr.cooldown,
                sr.cast_time,
                sr.channel_time
            FROM skill_rank sr
            JOIN skill s ON s.id = sr.skill_id
            LEFT JOIN ability a ON a.ability_id = sr.ability_id
            WHERE LOWER(TRIM(COALESCE(NULLIF(sr.raw_name, ''), NULLIF(a.name, ''), s.name)))
                = LOWER(TRIM(?))
            ORDER BY COALESCE(sr.rank, 0) DESC, sr.ability_id DESC
            LIMIT 1
            """,
            (action_name,),
        ).fetchone()

    @staticmethod
    def _seconds(value: object) -> float:
        if value is None:
            return 0.0
        amount = float(value)
        if amount <= 0:
            return 0.0
        return amount / _MILLISECONDS_PER_SECOND


__all__ = [
    "RotationSavedBuildActionTimingEvidence",
    "RotationSavedBuildActionTimingService",
]
