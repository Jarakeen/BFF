from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCandidateDrilldownReport:
    skill_entity_id: str
    candidate_ability_id: int
    cast_count: int
    linked_cast_count: int
    event_count: int
    linked_event_count: int
    ability_names: tuple[str, ...]
    event_types: tuple[tuple[str, int], ...]
    target_count: int | None
    first_offsets_seconds: tuple[float, ...]
    last_offsets_seconds: tuple[float, ...]
    within_cast_intervals_seconds: tuple[float, ...]
    near_active_end_count: int
    active_window_seconds: float
    unresolved: tuple[str, ...] = ()

    @property
    def median_first_offset_seconds(self) -> float | None:
        return float(median(self.first_offsets_seconds)) if self.first_offsets_seconds else None

    @property
    def median_last_offset_seconds(self) -> float | None:
        return float(median(self.last_offsets_seconds)) if self.last_offsets_seconds else None


class RotationDDPeriodicEsoLogsCandidateDrilldownService:
    """Inspect one observational secondary-effect candidate without promoting it.

    The service keeps canonical skill identity separate from the numeric candidate id,
    requires exact same-cast-track linkage for its strongest observations, and reports
    whether the candidate clusters near the reviewed active-window end. It never
    converts those observations into executable cadence, anchor, refresh, or magnitude
    semantics.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")
    _END_TOLERANCE_MS = 250.0

    def __init__(self, *, canonical_database_path: str | Path, logs_database_path: str | Path) -> None:
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
    ) -> RotationDDPeriodicEsoLogsCandidateDrilldownReport:
        identity = ability_entity_id(skill_entity_id)
        candidate_id = int(candidate_ability_id)
        window = float(active_window_seconds)
        unresolved: list[str] = []
        if not identity:
            return self._report("", candidate_id, window, unresolved=("canonical skill identity is required",))
        if candidate_id <= 0:
            return self._report(identity, candidate_id, window, unresolved=("positive candidate ability id is required",))
        if window <= 0:
            return self._report(identity, candidate_id, window, unresolved=("positive active window is required",))
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
            unresolved.extend(str(v) for v in resolution.unresolved if str(v).strip())

        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(log_event)")}
            required = {"report_code", "fight_id", "event_index", "timestamp", "event_type", "source_id", "ability_game_id", "cast_track_id", "raw_json"}
            missing = sorted(required - columns)
            if missing:
                return self._report(identity, candidate_id, window, unresolved=("log_event missing required columns: " + ", ".join(missing),))

            where = ["1=1"]
            params: list[object] = []
            if report_code is not None:
                where.append("report_code=?"); params.append(report_code)
            if fight_id is not None:
                where.append("fight_id=?"); params.append(int(fight_id))
            if source_id is not None:
                where.append("source_id=?"); params.append(int(source_id))
            select_target = ", target_id" if "target_id" in columns else ""
            rows = db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,ability_game_id,cast_track_id,raw_json" + select_target + " FROM log_event WHERE " + " AND ".join(where) + " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                tuple(params),
            ).fetchall()

        casts = [row for row in rows if self._event_type(row) in self._CAST_TYPES and self._matches_cast(row, identity, aliases)]
        if not casts:
            unresolved.append(f"{identity}: no matching cast observations found")
            return self._report(identity, candidate_id, window, unresolved=tuple(unresolved))
        anchor_type = next(kind for kind in self._CAST_TYPES if any(self._event_type(row) == kind for row in casts))
        casts = [row for row in casts if self._event_type(row) == anchor_type]
        candidate_rows = [row for row in rows if row["ability_game_id"] is not None and int(row["ability_game_id"]) == candidate_id]

        names: set[str] = set()
        event_type_counts: dict[str, int] = {}
        targets: set[int] = set()
        first_offsets: list[float] = []
        last_offsets: list[float] = []
        intervals: list[float] = []
        linked_event_count = 0
        linked_cast_count = 0
        near_end_count = 0

        grouped_candidates: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in candidate_rows:
            if row["source_id"] is None or row["cast_track_id"] is None:
                continue
            key = (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]), int(row["cast_track_id"]))
            grouped_candidates.setdefault(key, []).append(row)
            name = self._ability_name(row)
            if name:
                names.add(name)
            kind = self._event_type(row)
            event_type_counts[kind] = event_type_counts.get(kind, 0) + 1
            if "target_id" in row.keys() and row["target_id"] is not None:
                targets.add(int(row["target_id"]))

        for cast in casts:
            if cast["source_id"] is None or cast["cast_track_id"] is None:
                continue
            key = (str(cast["report_code"]), int(cast["fight_id"]), int(cast["source_id"]), int(cast["cast_track_id"]))
            linked = sorted(grouped_candidates.get(key, ()), key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
            if not linked:
                continue
            cast_time = float(cast["timestamp"])
            linked = [row for row in linked if cast_time <= float(row["timestamp"]) <= cast_time + window * 1000.0 + self._END_TOLERANCE_MS]
            if not linked:
                continue
            linked_cast_count += 1
            linked_event_count += len(linked)
            times = [float(row["timestamp"]) for row in linked]
            first_offsets.append((times[0] - cast_time) / 1000.0)
            last_offsets.append((times[-1] - cast_time) / 1000.0)
            intervals.extend((b - a) / 1000.0 for a, b in zip(times, times[1:]))
            near_end_count += sum(1 for t in times if abs((t - cast_time) - window * 1000.0) <= self._END_TOLERANCE_MS)

        if not linked_cast_count:
            unresolved.append(f"{identity}: candidate {candidate_id} has no exact same-cast-track observations")

        return self._report(
            identity, candidate_id, window,
            cast_count=len(casts), linked_cast_count=linked_cast_count,
            event_count=len(candidate_rows), linked_event_count=linked_event_count,
            ability_names=tuple(sorted(names, key=str.casefold)),
            event_types=tuple(sorted(event_type_counts.items())),
            target_count=(len(targets) if "target_id" in rows[0].keys() else None) if rows else None,
            first_offsets_seconds=tuple(first_offsets), last_offsets_seconds=tuple(last_offsets),
            within_cast_intervals_seconds=tuple(intervals), near_active_end_count=near_end_count,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            rows = db.execute("SELECT ability_id FROM skill_rank WHERE skill_id=? AND COALESCE(morph,0)=? AND ability_id IS NOT NULL", (int(skill_id), int(morph))).fetchall()
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

    def _matches_cast(self, row: sqlite3.Row, identity: str, aliases: set[int]) -> bool:
        name = self._ability_name(row)
        if name:
            return ability_entity_id(name) == identity
        return row["ability_game_id"] is not None and int(row["ability_game_id"]) in aliases

    @staticmethod
    def _report(skill: str, candidate: int, window: float, **kwargs) -> RotationDDPeriodicEsoLogsCandidateDrilldownReport:
        return RotationDDPeriodicEsoLogsCandidateDrilldownReport(
            skill_entity_id=skill, candidate_ability_id=candidate,
            cast_count=kwargs.get("cast_count", 0), linked_cast_count=kwargs.get("linked_cast_count", 0),
            event_count=kwargs.get("event_count", 0), linked_event_count=kwargs.get("linked_event_count", 0),
            ability_names=kwargs.get("ability_names", ()), event_types=kwargs.get("event_types", ()),
            target_count=kwargs.get("target_count"), first_offsets_seconds=kwargs.get("first_offsets_seconds", ()),
            last_offsets_seconds=kwargs.get("last_offsets_seconds", ()), within_cast_intervals_seconds=kwargs.get("within_cast_intervals_seconds", ()),
            near_active_end_count=kwargs.get("near_active_end_count", 0), active_window_seconds=window,
            unresolved=kwargs.get("unresolved", ()),
        )
