from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from engine.config import get_data_dir
from minmax.rotation_action_range import RotationActionRangeRequirement
from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild


DEFAULT_DATABASE = get_data_dir() / "eso.db"


@dataclass(frozen=True)
class RotationSavedBuildActionRangeEvidence:
    """Canonical action range requirements resolved from one saved build."""

    range_requirements: tuple[RotationActionRangeRequirement, ...] = ()
    unresolved: tuple[str, ...] = ()


class RotationSavedBuildActionRangeService:
    """Resolve min/max action range for the build's slotted skills and ultimates.

    The service preserves canonical range values exactly as imported. It does not
    infer encounter distance, target identity, radius behavior, or units. Callers
    evaluating range legality must supply target-distance evidence in the same unit.
    NULL/zero max-range evidence is not promoted into an invented hard limit.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    def resolve(self, player_build: PlayerBuild) -> RotationSavedBuildActionRangeEvidence:
        if not self.database_path.exists():
            return RotationSavedBuildActionRangeEvidence(
                unresolved=(f"canonical skill range database not found: {self.database_path}",)
            )

        slots = self._saved_slots(player_build)
        if not slots:
            return RotationSavedBuildActionRangeEvidence()

        requirements: dict[
            tuple[RotationActionKind, str], RotationActionRangeRequirement
        ] = {}
        unresolved: list[str] = []

        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            columns = {
                str(row[1])
                for row in db.execute("PRAGMA table_info(skill_rank)").fetchall()
            }
            required = {"skill_id", "ability_id", "rank", "min_range", "max_range"}
            if not required.issubset(columns):
                missing = ", ".join(sorted(required - columns))
                return RotationSavedBuildActionRangeEvidence(
                    unresolved=(f"canonical skill range schema is missing: {missing}",)
                )

            for action_name, action_kind in slots:
                row = self._range_row(db, action_name)
                if row is None:
                    unresolved.append(
                        f"canonical skill range not found by exact saved name: {action_name}"
                    )
                    continue

                minimum = self._nonnegative(row["min_range"])
                maximum = self._positive_or_none(row["max_range"])
                if minimum is None:
                    unresolved.append(
                        f"canonical skill minimum range is invalid: {action_name}"
                    )
                    continue
                if maximum is not None and maximum < minimum:
                    unresolved.append(
                        f"canonical skill range is inconsistent for {action_name}: "
                        f"minimum {minimum:g}, maximum {maximum:g}"
                    )
                    continue

                # No positive max and no positive min means the imported row does
                # not provide a useful hard range bound for Rotation Maker.
                if maximum is None and minimum <= 0:
                    continue

                key = (action_kind, action_name.casefold())
                requirements[key] = RotationActionRangeRequirement(
                    action_name=action_name,
                    minimum_range=minimum,
                    maximum_range=maximum,
                    action_kind=action_kind,
                )

        return RotationSavedBuildActionRangeEvidence(
            range_requirements=tuple(requirements.values()),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _saved_slots(player_build: PlayerBuild) -> tuple[tuple[str, RotationActionKind], ...]:
        front = tuple(getattr(player_build, "FrontBarSkills", ()) or ())
        back = tuple(getattr(player_build, "BackBarSkills", ()) or ())
        values: list[tuple[str, RotationActionKind]] = []
        for names in (front, back):
            for index, raw_name in enumerate(names):
                name = str(raw_name or "").strip()
                if not name:
                    continue
                kind = RotationActionKind.ULTIMATE if index == 5 else RotationActionKind.SKILL
                values.append((name, kind))
        return tuple(values)

    @staticmethod
    def _range_row(db: sqlite3.Connection, action_name: str) -> sqlite3.Row | None:
        return db.execute(
            """
            SELECT
                sr.min_range,
                sr.max_range
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
    def _nonnegative(value: object) -> float | None:
        if value is None:
            return 0.0
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return None
        if amount < 0:
            return None
        return amount

    @staticmethod
    def _positive_or_none(value: object) -> float | None:
        if value is None:
            return None
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return None
        if amount <= 0:
            return None
        return amount


__all__ = [
    "RotationSavedBuildActionRangeEvidence",
    "RotationSavedBuildActionRangeService",
]
