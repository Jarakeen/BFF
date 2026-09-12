from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCastTrackComponent:
    ability_game_id: int | None
    ability_name: str
    event_type: str
    cast_track_count: int
    event_count: int
    first_offsets_seconds: tuple[float, ...]

    @property
    def median_first_offset_seconds(self) -> float | None:
        return float(median(self.first_offsets_seconds)) if self.first_offsets_seconds else None


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsCastTrackTopologyReport:
    skill_entity_id: str
    cast_count: int
    active_window_seconds: float
    components: tuple[RotationDDPeriodicEsoLogsCastTrackComponent, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsCastTrackTopologyService:
    """Describe every exact same-cast-track event after a canonical DD skill cast.

    This is observational topology only. It is intended to reveal whether a repeated damage
    component is preceded by a distinct placement, impact, application, or other event on the
    same cast track. Numeric ESO IDs remain evidence handles and are never promoted here.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")

    def __init__(self, *, canonical_database_path: str | Path, logs_database_path: str | Path) -> None:
        self.canonical_database_path = Path(canonical_database_path)
        self.logs_database_path = Path(logs_database_path)
        self.coefficients = SkillCoefficientRepository(self.canonical_database_path)

    def inspect(
        self,
        skill_entity_id: str,
        *,
        active_window_seconds: float,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsCastTrackTopologyReport:
        identity = ability_entity_id(skill_entity_id)
        window = float(active_window_seconds)
        unresolved: list[str] = []
        if not identity:
            return self._report("", window, unresolved=("canonical skill identity is required",))
        if window <= 0:
            return self._report(identity, window, unresolved=("positive active window is required",))
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
                    window,
                    unresolved=("log_event missing required columns: " + ", ".join(missing),),
                )

            where = ["1=1"]
            params: list[object] = []
            if report_code is not None:
                where.append("report_code=?")
                params.append(report_code)
            if fight_id is not None:
                where.append("fight_id=?")
                params.append(int(fight_id))
            if source_id is not None:
                where.append("source_id=?")
                params.append(int(source_id))
            rows = db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event WHERE "
                + " AND ".join(where)
                + " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                tuple(params),
            ).fetchall()

        casts = [
            row for row in rows
            if self._event_type(row) in self._CAST_TYPES and self._matches_cast(row, identity, aliases)
        ]
        if not casts:
            unresolved.append(f"{identity}: no matching cast observations found")
            return self._report(identity, window, unresolved=tuple(unresolved))

        anchor_type = next(kind for kind in self._CAST_TYPES if any(self._event_type(row) == kind for row in casts))
        casts = [row for row in casts if self._event_type(row) == anchor_type]

        track_rows: dict[tuple[str, int, int, int], list[sqlite3.Row]] = {}
        for row in rows:
            if row["source_id"] is None or row["cast_track_id"] is None:
                continue
            key = (
                str(row["report_code"]), int(row["fight_id"]),
                int(row["source_id"]), int(row["cast_track_id"]),
            )
            track_rows.setdefault(key, []).append(row)

        aggregates: dict[tuple[int | None, str, str], dict[str, object]] = {}
        for cast in casts:
            if cast["source_id"] is None or cast["cast_track_id"] is None:
                continue
            key = (
                str(cast["report_code"]), int(cast["fight_id"]),
                int(cast["source_id"]), int(cast["cast_track_id"]),
            )
            cast_time = float(cast["timestamp"])
            end_time = cast_time + window * 1000.0
            seen_components: set[tuple[int | None, str, str]] = set()
            first_for_component: dict[tuple[int | None, str, str], float] = {}
            for row in track_rows.get(key, ()):
                timestamp = float(row["timestamp"])
                if timestamp < cast_time or timestamp > end_time:
                    continue
                if int(row["event_index"]) == int(cast["event_index"]):
                    continue
                component_key = (
                    int(row["ability_game_id"]) if row["ability_game_id"] is not None else None,
                    self._ability_name(row),
                    self._event_type(row),
                )
                data = aggregates.setdefault(component_key, {"tracks": 0, "events": 0, "first": []})
                data["events"] = int(data["events"]) + 1
                offset = (timestamp - cast_time) / 1000.0
                previous = first_for_component.get(component_key)
                if previous is None or offset < previous:
                    first_for_component[component_key] = offset
                seen_components.add(component_key)
            for component_key in seen_components:
                data = aggregates[component_key]
                data["tracks"] = int(data["tracks"]) + 1
                cast_offsets = data["first"]
                assert isinstance(cast_offsets, list)
                cast_offsets.append(first_for_component[component_key])

        components = tuple(
            sorted(
                (
                    RotationDDPeriodicEsoLogsCastTrackComponent(
                        ability_game_id=key[0],
                        ability_name=key[1],
                        event_type=key[2],
                        cast_track_count=int(data["tracks"]),
                        event_count=int(data["events"]),
                        first_offsets_seconds=tuple(float(value) for value in data["first"]),
                    )
                    for key, data in aggregates.items()
                ),
                key=lambda item: (
                    -item.cast_track_count,
                    item.median_first_offset_seconds if item.median_first_offset_seconds is not None else float("inf"),
                    -item.event_count,
                    item.ability_game_id if item.ability_game_id is not None else -1,
                    item.event_type,
                ),
            )
        )
        if not components:
            unresolved.append(f"{identity}: no exact same-cast-track component events found")
        return self._report(
            identity,
            window,
            cast_count=len(casts),
            components=components,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases(self, skill_id: int, morph: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            rows = db.execute(
                "SELECT ability_id FROM skill_rank WHERE skill_id=? AND COALESCE(morph,0)=? "
                "AND ability_id IS NOT NULL",
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

    def _matches_cast(self, row: sqlite3.Row, identity: str, aliases: set[int]) -> bool:
        name = self._ability_name(row)
        if name:
            return ability_entity_id(name) == identity
        return row["ability_game_id"] is not None and int(row["ability_game_id"]) in aliases

    @staticmethod
    def _report(skill: str, window: float, **kwargs) -> RotationDDPeriodicEsoLogsCastTrackTopologyReport:
        return RotationDDPeriodicEsoLogsCastTrackTopologyReport(
            skill_entity_id=skill,
            cast_count=kwargs.get("cast_count", 0),
            active_window_seconds=window,
            components=kwargs.get("components", ()),
            unresolved=kwargs.get("unresolved", ()),
        )
