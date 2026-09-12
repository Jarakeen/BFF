from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsSourceWindowExclusivityReport:
    skill_entity_id: str
    candidate_ability_id: int
    active_window_seconds: float
    cast_count: int
    caster_source_groups: int
    active_exposure_seconds: float
    inactive_exposure_seconds: float
    candidate_events_inside_windows: int
    candidate_events_outside_windows: int
    noncaster_source_groups_with_candidate: int
    noncaster_candidate_events: int
    unresolved: tuple[str, ...] = ()

    @property
    def inside_rate_per_minute(self) -> float | None:
        if self.active_exposure_seconds <= 0:
            return None
        return self.candidate_events_inside_windows * 60.0 / self.active_exposure_seconds

    @property
    def outside_rate_per_minute(self) -> float | None:
        if self.inactive_exposure_seconds <= 0:
            return None
        return self.candidate_events_outside_windows * 60.0 / self.inactive_exposure_seconds

    @property
    def inside_outside_rate_ratio(self) -> float | None:
        inside = self.inside_rate_per_minute
        outside = self.outside_rate_per_minute
        if inside is None or outside is None or outside <= 0:
            return None
        return inside / outside


class RotationDDPeriodicEsoLogsSourceWindowExclusivityService:
    """Compare one observational candidate inside and outside reviewed skill windows.

    This is candidate-identification evidence only. Numeric ESO IDs remain observational
    aliases, and a high inside/outside rate ratio does not promote canonical identity or
    executable periodic semantics. Overlapping/recast active windows are merged before
    exposure is measured so heavily refreshed skills do not double-count active time.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")

    def __init__(
        self,
        *,
        canonical_database_path: str | Path,
        logs_database_path: str | Path,
    ) -> None:
        self.canonical_database_path = Path(canonical_database_path)
        self.logs_database_path = Path(logs_database_path)
        self.coefficients = SkillCoefficientRepository(self.canonical_database_path)

    def inspect(
        self,
        skill_entity_id: str,
        *,
        candidate_ability_id: int,
        active_window_seconds: float,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsSourceWindowExclusivityReport:
        identity = ability_entity_id(skill_entity_id)
        candidate_id = int(candidate_ability_id)
        window_seconds = float(active_window_seconds)
        unresolved: list[str] = []

        if not identity:
            return self._report("", candidate_id, window_seconds, unresolved=("canonical skill identity is required",))
        if candidate_id <= 0:
            return self._report(identity, candidate_id, window_seconds, unresolved=("positive candidate ability id is required",))
        if window_seconds <= 0:
            return self._report(identity, candidate_id, window_seconds, unresolved=("positive active window is required",))
        if not self.canonical_database_path.is_file():
            raise FileNotFoundError(self.canonical_database_path)
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)

        resolution = self.coefficients.resolve_entity_id(identity)
        aliases: set[int] = set()
        if resolution.rank is not None:
            aliases.add(int(resolution.rank.base_ability_id))
            aliases.update(self._numeric_aliases(resolution.rank.skill_id, resolution.rank.morph))
        elif resolution.unresolved:
            unresolved.extend(str(value).strip() for value in resolution.unresolved if str(value).strip())

        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
            required = {
                "report_code", "fight_id", "event_index", "timestamp", "event_type",
                "source_id", "ability_game_id", "raw_json",
            }
            missing = sorted(required - columns)
            if missing:
                return self._report(
                    identity,
                    candidate_id,
                    window_seconds,
                    unresolved=("log_event missing required columns: " + ", ".join(missing),),
                )

            where = ["source_id IS NOT NULL"]
            params: list[object] = []
            if report_code is not None:
                where.append("report_code = ?")
                params.append(report_code)
            if fight_id is not None:
                where.append("fight_id = ?")
                params.append(int(fight_id))
            if source_id is not None:
                where.append("source_id = ?")
                params.append(int(source_id))
            rows = db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,ability_game_id,raw_json "
                "FROM log_event WHERE " + " AND ".join(where) +
                " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                tuple(params),
            ).fetchall()

        groups: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            key = (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]))
            groups.setdefault(key, []).append(row)

        cast_groups: dict[tuple[str, int, int], list[float]] = {}
        cast_count = 0
        for key, group_rows in groups.items():
            matching_casts = [
                row
                for row in group_rows
                if self._event_type(row) in self._CAST_TYPES
                and self._matches_cast(row, identity=identity, aliases=aliases)
            ]
            if not matching_casts:
                continue
            anchor_type = next(
                kind for kind in self._CAST_TYPES
                if any(self._event_type(row) == kind for row in matching_casts)
            )
            times = [float(row["timestamp"]) for row in matching_casts if self._event_type(row) == anchor_type]
            if times:
                cast_groups[key] = sorted(times)
                cast_count += len(times)

        if not cast_groups:
            unresolved.append(f"{identity}: no matching cast observations found")
            return self._report(identity, candidate_id, window_seconds, unresolved=tuple(dict.fromkeys(unresolved)))

        active_exposure_ms = 0.0
        inactive_exposure_ms = 0.0
        inside_events = 0
        outside_events = 0

        for key, cast_times in cast_groups.items():
            group_rows = groups[key]
            group_start = min(float(row["timestamp"]) for row in group_rows)
            group_end = max(float(row["timestamp"]) for row in group_rows)
            if group_end <= group_start:
                continue

            windows = self._merge_windows(
                (
                    (cast_time, min(cast_time + window_seconds * 1000.0, group_end))
                    for cast_time in cast_times
                    if cast_time <= group_end
                ),
                clip_start=group_start,
                clip_end=group_end,
            )
            active_ms = sum(end - start for start, end in windows)
            total_ms = group_end - group_start
            active_exposure_ms += active_ms
            inactive_exposure_ms += max(0.0, total_ms - active_ms)

            candidate_times = [
                float(row["timestamp"])
                for row in group_rows
                if self._event_type(row) == "damage"
                and row["ability_game_id"] is not None
                and int(row["ability_game_id"]) == candidate_id
            ]
            for timestamp in candidate_times:
                if self._in_windows(timestamp, windows):
                    inside_events += 1
                else:
                    outside_events += 1

        noncaster_groups = 0
        noncaster_events = 0
        for key, group_rows in groups.items():
            if key in cast_groups:
                continue
            count = sum(
                1
                for row in group_rows
                if self._event_type(row) == "damage"
                and row["ability_game_id"] is not None
                and int(row["ability_game_id"]) == candidate_id
            )
            if count:
                noncaster_groups += 1
                noncaster_events += count

        if active_exposure_ms <= 0:
            unresolved.append(f"{identity}: no measurable active-window exposure")

        return self._report(
            identity,
            candidate_id,
            window_seconds,
            cast_count=cast_count,
            caster_source_groups=len(cast_groups),
            active_exposure_seconds=active_exposure_ms / 1000.0,
            inactive_exposure_seconds=inactive_exposure_ms / 1000.0,
            candidate_events_inside_windows=inside_events,
            candidate_events_outside_windows=outside_events,
            noncaster_source_groups_with_candidate=noncaster_groups,
            noncaster_candidate_events=noncaster_events,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            rows = db.execute(
                "SELECT ability_id FROM skill_rank "
                "WHERE skill_id=? AND COALESCE(morph,0)=? AND ability_id IS NOT NULL",
                (int(skill_id), int(morph)),
            ).fetchall()
        return tuple(int(row[0]) for row in rows)

    @staticmethod
    def _event_type(row: sqlite3.Row) -> str:
        return str(row["event_type"] or "").strip().casefold()

    @staticmethod
    def _ability_name(row: sqlite3.Row) -> str:
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            return ""
        ability = raw.get("ability") if isinstance(raw, dict) else None
        return str(ability.get("name") or "").strip() if isinstance(ability, dict) else ""

    def _matches_cast(self, row: sqlite3.Row, *, identity: str, aliases: set[int]) -> bool:
        name = self._ability_name(row)
        if name:
            return ability_entity_id(name) == identity
        return row["ability_game_id"] is not None and int(row["ability_game_id"]) in aliases

    @staticmethod
    def _merge_windows(
        windows,
        *,
        clip_start: float,
        clip_end: float,
    ) -> tuple[tuple[float, float], ...]:
        clipped = sorted(
            (max(float(start), clip_start), min(float(end), clip_end))
            for start, end in windows
            if min(float(end), clip_end) > max(float(start), clip_start)
        )
        if not clipped:
            return ()
        merged: list[list[float]] = [[clipped[0][0], clipped[0][1]]]
        for start, end in clipped[1:]:
            previous = merged[-1]
            if start <= previous[1]:
                previous[1] = max(previous[1], end)
            else:
                merged.append([start, end])
        return tuple((start, end) for start, end in merged)

    @staticmethod
    def _in_windows(timestamp: float, windows: tuple[tuple[float, float], ...]) -> bool:
        return any(start <= timestamp <= end for start, end in windows)

    @staticmethod
    def _report(
        skill_entity_id: str,
        candidate_ability_id: int,
        active_window_seconds: float,
        **kwargs,
    ) -> RotationDDPeriodicEsoLogsSourceWindowExclusivityReport:
        return RotationDDPeriodicEsoLogsSourceWindowExclusivityReport(
            skill_entity_id=skill_entity_id,
            candidate_ability_id=candidate_ability_id,
            active_window_seconds=active_window_seconds,
            cast_count=kwargs.get("cast_count", 0),
            caster_source_groups=kwargs.get("caster_source_groups", 0),
            active_exposure_seconds=kwargs.get("active_exposure_seconds", 0.0),
            inactive_exposure_seconds=kwargs.get("inactive_exposure_seconds", 0.0),
            candidate_events_inside_windows=kwargs.get("candidate_events_inside_windows", 0),
            candidate_events_outside_windows=kwargs.get("candidate_events_outside_windows", 0),
            noncaster_source_groups_with_candidate=kwargs.get("noncaster_source_groups_with_candidate", 0),
            noncaster_candidate_events=kwargs.get("noncaster_candidate_events", 0),
            unresolved=kwargs.get("unresolved", ()),
        )
