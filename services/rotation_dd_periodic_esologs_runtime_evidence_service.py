from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Iterable

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id
from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsObservedEvent:
    timestamp_ms: float
    event_type: str
    ability_game_id: int | None
    target_id: int | None
    amount: float | None
    tick: bool | None
    cast_track_id: int | None


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCastObservation:
    report_code: str
    fight_id: int
    source_id: int
    cast_timestamp_ms: float
    cast_event_type: str
    ability_game_id: int | None
    next_cast_timestamp_ms: float | None
    periodic_events: tuple[RotationDDPeriodicEsoLogsObservedEvent, ...]
    first_tick_offset_seconds: float | None
    tick_intervals_seconds: tuple[float, ...]
    exact_recast_boundary_event_count: int
    isolated_from_recast: bool
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsRuntimeEvidenceReport:
    skill_entity_id: str
    observed_ability_ids: tuple[int, ...]
    casts: tuple[RotationDDPeriodicEsoLogsCastObservation, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def complete_observational_timing(self) -> bool:
        return bool(self.casts) and not self.unresolved and all(
            not cast.unresolved and cast.first_tick_offset_seconds is not None
            for cast in self.casts
            if cast.isolated_from_recast
        )


class RotationDDPeriodicEsoLogsRuntimeEvidenceService:
    """Read imported ESO Logs events as non-executable DD periodic timing evidence.

    Canonical lower-snake-case ability identity is the request key. Translated raw
    ESO Logs ability names are preferred when available; numeric ability ids are
    only temporary crosswalk aliases for events whose raw name is absent.

    The service reports observed cast/tick timing. It never promotes refresh-boundary
    or magnitude-policy semantics automatically. Recast overlap, target switching,
    buffs, debuffs, crits, and bar state can all make raw combat-log magnitudes
    ambiguous, so those mechanics remain deliberate review work.
    """

    REQUIRED_COLUMNS = frozenset(
        {
            "report_code",
            "fight_id",
            "event_index",
            "timestamp",
            "event_type",
            "source_id",
            "target_id",
            "ability_game_id",
            "amount",
            "tick",
            "cast_track_id",
            "raw_json",
        }
    )
    _CAST_TYPES = ("cast", "completecast", "begincast")
    _BOUNDARY_TOLERANCE_MS = 50.0

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | None = None,
        review_service: RotationDDPeriodicRuntimeSemanticsReviewService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(
            self.database_path
        )
        self.review_service = review_service or RotationDDPeriodicRuntimeSemanticsReviewService()

    def inspect_skill(
        self,
        skill_entity_id: str,
        *,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsRuntimeEvidenceReport:
        identity = ability_entity_id(skill_entity_id)
        if not identity:
            return RotationDDPeriodicEsoLogsRuntimeEvidenceReport(
                skill_entity_id="",
                observed_ability_ids=(),
                casts=(),
                unresolved=("canonical skill identity is required",),
            )
        if not self.database_path.exists():
            raise FileNotFoundError(self.database_path)

        resolution = self.coefficients.resolve_entity_id(identity)
        numeric_aliases: set[int] = set()
        unresolved: list[str] = []
        if resolution.rank is not None:
            numeric_aliases.update(
                self._numeric_aliases_for_rank(
                    skill_id=resolution.rank.skill_id,
                    morph=resolution.rank.morph,
                    base_ability_id=resolution.rank.base_ability_id,
                )
            )
        elif resolution.unresolved:
            unresolved.extend(str(item).strip() for item in resolution.unresolved if str(item).strip())

        review = self.review_service.by_component()
        review_rows = tuple(
            row for (entity, _number), row in review.items() if entity == identity
        )
        durations = {
            float(row.duration_seconds)
            for row in review_rows
            if row.duration_seconds is not None
        }
        duration_seconds = next(iter(durations)) if len(durations) == 1 else None
        if len(durations) > 1:
            unresolved.append(
                f"{identity}: conflicting reviewed periodic durations prevent cast-window attribution"
            )

        uri = f"file:{self.database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            schema_unresolved = self._schema_unresolved(connection)
            if schema_unresolved:
                return RotationDDPeriodicEsoLogsRuntimeEvidenceReport(
                    skill_entity_id=identity,
                    observed_ability_ids=tuple(sorted(numeric_aliases)),
                    casts=(),
                    unresolved=tuple(dict.fromkeys((*unresolved, *schema_unresolved))),
                )

            rows = self._candidate_rows(
                connection,
                report_code=report_code,
                fight_id=fight_id,
                source_id=source_id,
            )

        matched = tuple(
            row
            for row in rows
            if self._matches_identity(row, identity=identity, numeric_aliases=numeric_aliases)
        )
        observed_ids = set(numeric_aliases)
        observed_ids.update(
            int(row["ability_game_id"])
            for row in matched
            if row["ability_game_id"] is not None
        )

        groups: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
        for row in matched:
            if row["source_id"] is None:
                continue
            key = (
                str(row["report_code"]),
                int(row["fight_id"]),
                int(row["source_id"]),
            )
            groups.setdefault(key, []).append(row)

        casts: list[RotationDDPeriodicEsoLogsCastObservation] = []
        for (group_report, group_fight, group_source), group_rows in sorted(groups.items()):
            casts.extend(
                self._cast_observations(
                    group_rows,
                    report_code=group_report,
                    fight_id=group_fight,
                    source_id=group_source,
                    duration_seconds=duration_seconds,
                )
            )

        if not casts:
            unresolved.append(f"{identity}: no matching ESO Logs cast observations found")

        return RotationDDPeriodicEsoLogsRuntimeEvidenceReport(
            skill_entity_id=identity,
            observed_ability_ids=tuple(sorted(observed_ids)),
            casts=tuple(casts),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases_for_rank(
        self,
        *,
        skill_id: int,
        morph: int,
        base_ability_id: int,
    ) -> tuple[int, ...]:
        uri = f"file:{self.database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            aliases = {int(base_ability_id)} if int(base_ability_id) > 0 else set()
            if "skill_rank" in tables:
                aliases.update(
                    int(row["ability_id"])
                    for row in connection.execute(
                        """
                        SELECT ability_id
                        FROM skill_rank
                        WHERE skill_id = ? AND COALESCE(morph, 0) = ?
                          AND ability_id IS NOT NULL
                        """,
                        (int(skill_id), int(morph)),
                    ).fetchall()
                )
            return tuple(sorted(alias for alias in aliases if alias > 0))

    @classmethod
    def _schema_unresolved(cls, connection: sqlite3.Connection) -> tuple[str, ...]:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "log_event" not in tables:
            return ("log_event table is unavailable",)
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(log_event)").fetchall()
        }
        missing = sorted(cls.REQUIRED_COLUMNS - columns)
        if missing:
            return ("log_event is missing required columns: " + ", ".join(missing),)
        return ()

    @staticmethod
    def _candidate_rows(
        connection: sqlite3.Connection,
        *,
        report_code: str | None,
        fight_id: int | None,
        source_id: int | None,
    ) -> tuple[sqlite3.Row, ...]:
        clauses = [
            "lower(event_type) IN ('cast', 'begincast', 'completecast', 'damage')"
        ]
        params: list[object] = []
        if report_code is not None:
            clauses.append("report_code = ?")
            params.append(str(report_code))
        if fight_id is not None:
            clauses.append("fight_id = ?")
            params.append(int(fight_id))
        if source_id is not None:
            clauses.append("source_id = ?")
            params.append(int(source_id))
        sql = (
            "SELECT report_code, fight_id, event_index, timestamp, event_type, "
            "source_id, target_id, ability_game_id, amount, tick, cast_track_id, raw_json "
            "FROM log_event WHERE "
            + " AND ".join(clauses)
            + " ORDER BY report_code, fight_id, source_id, timestamp, event_index"
        )
        return tuple(connection.execute(sql, tuple(params)).fetchall())

    @classmethod
    def _matches_identity(
        cls,
        row: sqlite3.Row,
        *,
        identity: str,
        numeric_aliases: set[int],
    ) -> bool:
        raw_name = cls._ability_name_from_raw(row["raw_json"])
        if raw_name:
            return ability_entity_id(raw_name) == identity
        ability_id = row["ability_game_id"]
        return ability_id is not None and int(ability_id) in numeric_aliases

    @classmethod
    def _cast_observations(
        cls,
        rows: Iterable[sqlite3.Row],
        *,
        report_code: str,
        fight_id: int,
        source_id: int,
        duration_seconds: float | None,
    ) -> tuple[RotationDDPeriodicEsoLogsCastObservation, ...]:
        rows = tuple(rows)
        cast_rows = tuple(
            row for row in rows if str(row["event_type"] or "").strip().lower() in cls._CAST_TYPES
        )
        if not cast_rows:
            return ()

        available_types = {
            str(row["event_type"] or "").strip().lower() for row in cast_rows
        }
        anchor_type = next(kind for kind in cls._CAST_TYPES if kind in available_types)
        anchors = tuple(
            row
            for row in cast_rows
            if str(row["event_type"] or "").strip().lower() == anchor_type
        )
        damage_rows = tuple(
            row for row in rows if str(row["event_type"] or "").strip().lower() == "damage"
        )

        observations: list[RotationDDPeriodicEsoLogsCastObservation] = []
        for index, cast in enumerate(anchors):
            cast_time = float(cast["timestamp"])
            next_cast_time = (
                float(anchors[index + 1]["timestamp"])
                if index + 1 < len(anchors)
                else None
            )
            natural_end = (
                cast_time + (duration_seconds * 1000.0)
                if duration_seconds is not None
                else None
            )
            if natural_end is not None:
                window_end = natural_end
            elif next_cast_time is not None:
                window_end = next_cast_time
            else:
                window_end = float("inf")

            relevant_damage = tuple(
                row
                for row in damage_rows
                if float(row["timestamp"]) >= cast_time
                and float(row["timestamp"]) <= window_end
                and bool(row["tick"])
            )
            unique_tick_times = tuple(
                dict.fromkeys(float(row["timestamp"]) for row in relevant_damage)
            )
            first_offset = (
                (unique_tick_times[0] - cast_time) / 1000.0
                if unique_tick_times
                else None
            )
            intervals = tuple(
                (later - earlier) / 1000.0
                for earlier, later in zip(unique_tick_times, unique_tick_times[1:])
            )
            boundary_count = 0
            if next_cast_time is not None:
                boundary_count = sum(
                    1
                    for tick_time in unique_tick_times
                    if abs(tick_time - next_cast_time) <= cls._BOUNDARY_TOLERANCE_MS
                )
            isolated = (
                next_cast_time is None
                or natural_end is None
                or next_cast_time > natural_end + cls._BOUNDARY_TOLERANCE_MS
            )
            cast_unresolved: list[str] = []
            if duration_seconds is None:
                cast_unresolved.append(
                    "reviewed periodic duration is unavailable; cast window may be truncated by recast"
                )
            if not relevant_damage:
                cast_unresolved.append("no matching tick-marked damage events observed in cast window")
            if not isolated:
                cast_unresolved.append(
                    "recast overlaps the reviewed active window; first-tick attribution may include multiple instances"
                )

            observations.append(
                RotationDDPeriodicEsoLogsCastObservation(
                    report_code=report_code,
                    fight_id=fight_id,
                    source_id=source_id,
                    cast_timestamp_ms=cast_time,
                    cast_event_type=anchor_type,
                    ability_game_id=(
                        int(cast["ability_game_id"])
                        if cast["ability_game_id"] is not None
                        else None
                    ),
                    next_cast_timestamp_ms=next_cast_time,
                    periodic_events=tuple(
                        RotationDDPeriodicEsoLogsObservedEvent(
                            timestamp_ms=float(row["timestamp"]),
                            event_type=str(row["event_type"] or "").strip().lower(),
                            ability_game_id=(
                                int(row["ability_game_id"])
                                if row["ability_game_id"] is not None
                                else None
                            ),
                            target_id=(int(row["target_id"]) if row["target_id"] is not None else None),
                            amount=(float(row["amount"]) if row["amount"] is not None else None),
                            tick=(None if row["tick"] is None else bool(row["tick"])),
                            cast_track_id=(
                                int(row["cast_track_id"])
                                if row["cast_track_id"] is not None
                                else None
                            ),
                        )
                        for row in relevant_damage
                    ),
                    first_tick_offset_seconds=first_offset,
                    tick_intervals_seconds=intervals,
                    exact_recast_boundary_event_count=boundary_count,
                    isolated_from_recast=isolated,
                    unresolved=tuple(dict.fromkeys(cast_unresolved)),
                )
            )
        return tuple(observations)

    @staticmethod
    def _ability_name_from_raw(raw_json: object) -> str | None:
        if raw_json is None:
            return None
        try:
            raw = json.loads(str(raw_json))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        ability = raw.get("ability")
        if isinstance(ability, dict):
            value = ability.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        value = raw.get("abilityName")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None


__all__ = [
    "RotationDDPeriodicEsoLogsCastObservation",
    "RotationDDPeriodicEsoLogsObservedEvent",
    "RotationDDPeriodicEsoLogsRuntimeEvidenceReport",
    "RotationDDPeriodicEsoLogsRuntimeEvidenceService",
]
