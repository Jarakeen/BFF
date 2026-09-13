from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidatePersistenceSummary:
    candidate_ability_id: int
    linked_cast_count: int
    minimum_last_offset_seconds: float | None
    median_last_offset_seconds: float | None
    maximum_last_offset_seconds: float | None
    observed_at_or_after_2s: int
    observed_at_or_after_5s: int
    observed_at_or_after_10s: int
    observed_at_or_after_15s: int
    observed_at_or_after_19s: int


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidatePersistenceReport:
    skill_entity_id: str
    candidate_ability_ids: tuple[int, ...]
    active_window_seconds: float
    cast_count: int
    summaries: tuple[RotationDDPeriodicEsoLogsCandidatePersistenceSummary, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsCandidatePersistenceService:
    """Measure last-observed same-track candidate persistence per censored cast.

    Candidate numeric IDs remain observational evidence handles only. Each canonical
    skill cast owns same-source, same-cast-track candidate events from cast time until
    the next same-source cast or the reviewed active-window end, whichever comes first.
    A threshold count means only that at least one candidate event was observed at or
    after that offset. It does not prove uninterrupted effect uptime between observations.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")
    _THRESHOLDS = (2.0, 5.0, 10.0, 15.0, 19.0)

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
        candidate_ability_ids: tuple[int, ...],
        active_window_seconds: float,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsCandidatePersistenceReport:
        identity = ability_entity_id(skill_entity_id)
        candidates = tuple(dict.fromkeys(int(value) for value in candidate_ability_ids))
        window = float(active_window_seconds)
        if not identity:
            return self._report("", candidates, window, unresolved=("canonical skill identity is required",))
        if not candidates or any(value <= 0 for value in candidates):
            return self._report(identity, candidates, window, unresolved=("positive candidate ability ids are required",))
        if window <= 0:
            return self._report(identity, candidates, window, unresolved=("active_window_seconds must be positive",))
        if not self.canonical_database_path.is_file():
            raise FileNotFoundError(self.canonical_database_path)
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)

        resolution = self.coefficients.resolve_entity_id(identity)
        aliases: set[int] = set()
        unresolved: list[str] = []
        if resolution.rank is not None:
            aliases.add(int(resolution.rank.base_ability_id))
            aliases.update(self._numeric_aliases(resolution.rank.skill_id, resolution.rank.morph))
        elif resolution.unresolved:
            unresolved.extend(str(value) for value in resolution.unresolved if str(value).strip())

        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
            required = {
                "report_code", "fight_id", "event_index", "timestamp", "event_type",
                "source_id", "ability_game_id", "cast_track_id", "raw_json",
            }
            missing = sorted(required - columns)
            if missing:
                return self._report(
                    identity,
                    candidates,
                    window,
                    unresolved=("log_event missing required columns: " + ", ".join(missing),),
                )
            clauses = ["1=1"]
            params: list[object] = []
            if report_code is not None:
                clauses.append("report_code=?")
                params.append(str(report_code))
            if fight_id is not None:
                clauses.append("fight_id=?")
                params.append(int(fight_id))
            rows = tuple(
                db.execute(
                    "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                    "ability_game_id,cast_track_id,raw_json FROM log_event WHERE "
                    + " AND ".join(clauses)
                    + " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                    tuple(params),
                ).fetchall()
            )

        casts = [
            row
            for row in rows
            if self._event_type(row) in self._CAST_TYPES
            and self._matches_cast(row, identity, aliases)
            and (source_id is None or self._int_or_none(row["source_id"]) == int(source_id))
        ]
        if not casts:
            unresolved.append(f"{identity}: no matching cast observations found")
            return self._report(identity, candidates, window, unresolved=tuple(dict.fromkeys(unresolved)))
        anchor_type = next(
            kind for kind in self._CAST_TYPES if any(self._event_type(row) == kind for row in casts)
        )
        casts = [row for row in casts if self._event_type(row) == anchor_type]
        next_cast_times = self._next_same_source_cast_times(casts)

        candidate_set = set(candidates)
        by_scope_source_track: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            ability = row["ability_game_id"]
            source = self._int_or_none(row["source_id"])
            track = self._int_or_none(row["cast_track_id"])
            if ability is None or int(ability) not in candidate_set or source is None or track is None:
                continue
            key = (str(row["report_code"]), int(row["fight_id"]), source, track)
            by_scope_source_track.setdefault(key, []).append(row)

        last_offsets_by_candidate: dict[int, list[float]] = {candidate: [] for candidate in candidates}
        for cast in casts:
            cast_source = self._int_or_none(cast["source_id"])
            cast_track = self._int_or_none(cast["cast_track_id"])
            if cast_source is None or cast_track is None:
                continue
            cast_time = float(cast["timestamp"])
            cast_key = (str(cast["report_code"]), int(cast["fight_id"]), int(cast["event_index"]))
            next_cast_time = next_cast_times.get(cast_key)
            window_end = cast_time + window * 1000.0
            censored_end = min(window_end, next_cast_time) if next_cast_time is not None else window_end
            scope_key = (str(cast["report_code"]), int(cast["fight_id"]), cast_source, cast_track)
            matching = by_scope_source_track.get(scope_key, ())
            by_candidate: dict[int, list[float]] = {}
            for row in matching:
                timestamp = float(row["timestamp"])
                if timestamp < cast_time:
                    continue
                if next_cast_time is not None:
                    if timestamp >= censored_end:
                        continue
                elif timestamp > censored_end:
                    continue
                candidate_id = int(row["ability_game_id"])
                by_candidate.setdefault(candidate_id, []).append((timestamp - cast_time) / 1000.0)
            for candidate_id, offsets in by_candidate.items():
                if offsets:
                    last_offsets_by_candidate[candidate_id].append(max(offsets))

        summaries: list[RotationDDPeriodicEsoLogsCandidatePersistenceSummary] = []
        for candidate_id in candidates:
            offsets = tuple(sorted(last_offsets_by_candidate[candidate_id]))
            counts = {threshold: sum(1 for value in offsets if value >= threshold) for threshold in self._THRESHOLDS}
            summaries.append(
                RotationDDPeriodicEsoLogsCandidatePersistenceSummary(
                    candidate_ability_id=candidate_id,
                    linked_cast_count=len(offsets),
                    minimum_last_offset_seconds=min(offsets) if offsets else None,
                    median_last_offset_seconds=float(median(offsets)) if offsets else None,
                    maximum_last_offset_seconds=max(offsets) if offsets else None,
                    observed_at_or_after_2s=counts[2.0],
                    observed_at_or_after_5s=counts[5.0],
                    observed_at_or_after_10s=counts[10.0],
                    observed_at_or_after_15s=counts[15.0],
                    observed_at_or_after_19s=counts[19.0],
                )
            )
        if not any(item.linked_cast_count for item in summaries):
            unresolved.append(f"{identity}: no censored same-source same-track candidate observations found")
        return self._report(
            identity,
            candidates,
            window,
            cast_count=len(casts),
            summaries=tuple(summaries),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.execute("PRAGMA query_only = ON")
            rows = db.execute(
                "SELECT ability_id FROM skill_rank WHERE skill_id=? AND COALESCE(morph,0)=? "
                "AND ability_id IS NOT NULL",
                (int(skill_id), int(morph)),
            ).fetchall()
        return tuple(int(row[0]) for row in rows)

    @staticmethod
    def _next_same_source_cast_times(casts: list[sqlite3.Row]) -> dict[tuple[str, int, int], float]:
        grouped: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
        for cast in casts:
            source = cast["source_id"]
            if source is None:
                continue
            key = (str(cast["report_code"]), int(cast["fight_id"]), int(source))
            grouped.setdefault(key, []).append(cast)
        result: dict[tuple[str, int, int], float] = {}
        for values in grouped.values():
            ordered = sorted(values, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
            for current, following in zip(ordered, ordered[1:]):
                key = (str(current["report_code"]), int(current["fight_id"]), int(current["event_index"]))
                result[key] = float(following["timestamp"])
        return result

    @classmethod
    def _matches_cast(cls, row: sqlite3.Row, identity: str, aliases: set[int]) -> bool:
        name = cls._ability_name(row)
        if name:
            return ability_entity_id(name) == identity
        value = row["ability_game_id"]
        return value is not None and int(value) in aliases

    @staticmethod
    def _ability_name(row: sqlite3.Row) -> str:
        try:
            payload = json.loads(row["raw_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            return ""
        ability = payload.get("ability") if isinstance(payload, dict) else None
        return str(ability.get("name") or "").strip() if isinstance(ability, dict) else ""

    @staticmethod
    def _event_type(row: sqlite3.Row) -> str:
        return str(row["event_type"] or "").strip().casefold()

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        return None if value is None else int(value)

    @staticmethod
    def _report(
        skill: str,
        candidates: tuple[int, ...],
        window: float,
        **kwargs,
    ) -> RotationDDPeriodicEsoLogsCandidatePersistenceReport:
        return RotationDDPeriodicEsoLogsCandidatePersistenceReport(
            skill_entity_id=skill,
            candidate_ability_ids=candidates,
            active_window_seconds=window,
            cast_count=kwargs.get("cast_count", 0),
            summaries=kwargs.get("summaries", ()),
            unresolved=kwargs.get("unresolved", ()),
        )


__all__ = [
    "RotationDDPeriodicEsoLogsCandidatePersistenceReport",
    "RotationDDPeriodicEsoLogsCandidatePersistenceService",
    "RotationDDPeriodicEsoLogsCandidatePersistenceSummary",
]
