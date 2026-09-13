from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3


_DEFAULT_NAMES = ("Meteor", "Ice Comet", "Shooting Star")
_CAST_TYPES = {"cast", "completecast", "begincast"}


@dataclass(frozen=True)
class RotationMeteorEsoLogsRawIdentityRow:
    ability_name: str
    ability_game_id: int | None
    event_type: str
    event_count: int
    source_actor_count: int
    cast_track_linked_event_count: int


@dataclass(frozen=True)
class RotationMeteorEsoLogsRawIdentityReport:
    rows: tuple[RotationMeteorEsoLogsRawIdentityRow, ...]
    matching_event_count: int
    matching_cast_event_count: int
    unresolved: tuple[str, ...] = ()


class RotationMeteorEsoLogsRawIdentityService:
    """Inventory raw ESO Logs identities for the Meteor skill family.

    This service is discovery-only. It deliberately does not consult the canonical
    skill crosswalk and never promotes numeric ESO Logs ids into runtime semantics.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(
        self,
        *,
        names: tuple[str, ...] = _DEFAULT_NAMES,
    ) -> RotationMeteorEsoLogsRawIdentityReport:
        if not self.logs_database_path.is_file():
            return RotationMeteorEsoLogsRawIdentityReport(
                rows=(),
                matching_event_count=0,
                matching_cast_event_count=0,
                unresolved=(f"ESO Logs database not found: {self.logs_database_path}",),
            )

        wanted = {name.casefold() for name in names if name.strip()}
        if not wanted:
            return RotationMeteorEsoLogsRawIdentityReport(
                rows=(),
                matching_event_count=0,
                matching_cast_event_count=0,
                unresolved=("at least one Meteor-family ability name is required",),
            )

        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return RotationMeteorEsoLogsRawIdentityReport(
                    rows=(),
                    matching_event_count=0,
                    matching_cast_event_count=0,
                    unresolved=(schema_error,),
                )
            rows = db.execute(
                "SELECT event_type, source_id, ability_game_id, cast_track_id, raw_json "
                "FROM log_event ORDER BY report_code, fight_id, timestamp, event_index"
            ).fetchall()

        buckets: dict[tuple[str, int | None, str], dict[str, object]] = {}
        matching = 0
        matching_casts = 0
        for row in rows:
            ability_name = self._ability_name(row["raw_json"])
            if ability_name is None or ability_name.casefold() not in wanted:
                continue
            matching += 1
            event_type = str(row["event_type"] or "").strip().casefold()
            if event_type in _CAST_TYPES:
                matching_casts += 1
            ability_id = int(row["ability_game_id"]) if row["ability_game_id"] is not None else None
            key = (ability_name, ability_id, event_type)
            bucket = buckets.setdefault(
                key,
                {"events": 0, "sources": set(), "linked": 0},
            )
            bucket["events"] = int(bucket["events"]) + 1
            if row["source_id"] is not None:
                bucket["sources"].add(int(row["source_id"]))
            if row["cast_track_id"] is not None:
                bucket["linked"] = int(bucket["linked"]) + 1

        report_rows = tuple(
            RotationMeteorEsoLogsRawIdentityRow(
                ability_name=name,
                ability_game_id=ability_id,
                event_type=event_type,
                event_count=int(data["events"]),
                source_actor_count=len(data["sources"]),
                cast_track_linked_event_count=int(data["linked"]),
            )
            for (name, ability_id, event_type), data in sorted(
                buckets.items(),
                key=lambda item: (
                    item[0][0].casefold(),
                    item[0][2],
                    -int(item[1]["events"]),
                    item[0][1] if item[0][1] is not None else -1,
                ),
            )
        )
        unresolved: list[str] = []
        if not report_rows:
            unresolved.append("no raw ESO Logs events matched Meteor, Ice Comet, or Shooting Star")
        elif matching_casts == 0:
            unresolved.append("Meteor-family raw events were found, but none were cast-like events")

        return RotationMeteorEsoLogsRawIdentityReport(
            rows=report_rows,
            matching_event_count=matching,
            matching_cast_event_count=matching_casts,
            unresolved=tuple(unresolved),
        )

    def _open_logs(self) -> sqlite3.Connection:
        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        return db

    @staticmethod
    def _schema_error(db: sqlite3.Connection) -> str | None:
        table = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='log_event'"
        ).fetchone()
        if table is None:
            return "log_event table is unavailable"
        required = {
            "report_code",
            "fight_id",
            "event_index",
            "timestamp",
            "event_type",
            "source_id",
            "ability_game_id",
            "cast_track_id",
            "raw_json",
        }
        columns = {
            str(row[1]) for row in db.execute("PRAGMA table_info(log_event)").fetchall()
        }
        missing = sorted(required - columns)
        return (
            "log_event is missing required columns: " + ", ".join(missing)
            if missing
            else None
        )

    @staticmethod
    def _ability_name(raw_json: object) -> str | None:
        if not raw_json:
            return None
        try:
            payload = json.loads(str(raw_json))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        ability = payload.get("ability") if isinstance(payload, dict) else None
        if not isinstance(ability, dict):
            return None
        name = ability.get("name")
        text = str(name).strip() if name is not None else ""
        return text or None
