from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3


_OWNER_KEY_TOKENS = ("owner", "master", "pet", "parent", "summon")


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsActorProvenanceRow:
    actor_id: int
    event_count: int
    report_fight_groups: int
    name: str | None = None
    display_name: str | None = None
    actor_type: str | None = None
    role: str | None = None
    owner_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsActorProvenanceReport:
    ability_id: int
    event_count: int
    source_actor_count: int
    matched_actor_count: int
    rows: tuple[RotationDDPeriodicEsoLogsActorProvenanceRow, ...]
    unresolved: tuple[str, ...] = ()


class RotationDDPeriodicEsoLogsActorProvenanceService:
    """Summarize which imported ESO Logs actors emitted one observed ability ID.

    This service is evidence-only. Actor metadata and owner-like raw JSON fields are
    reported exactly as imported; no pet/summon ownership relationship is inferred
    when ESO Logs did not preserve one explicitly.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(self, ability_id: int) -> RotationDDPeriodicEsoLogsActorProvenanceReport:
        requested = int(ability_id)
        if requested <= 0:
            raise ValueError("ability_id must be positive")
        if not self.logs_database_path.is_file():
            return RotationDDPeriodicEsoLogsActorProvenanceReport(
                ability_id=requested,
                event_count=0,
                source_actor_count=0,
                matched_actor_count=0,
                rows=(),
                unresolved=(f"ESO Logs database not found: {self.logs_database_path}",),
            )

        with sqlite3.connect(self.logs_database_path) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            tables = {
                str(row[0])
                for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            missing = tuple(name for name in ("log_event", "log_actor") if name not in tables)
            if missing:
                return RotationDDPeriodicEsoLogsActorProvenanceReport(
                    ability_id=requested,
                    event_count=0,
                    source_actor_count=0,
                    matched_actor_count=0,
                    rows=(),
                    unresolved=("missing required tables: " + ", ".join(missing),),
                )

            totals = db.execute(
                """
                SELECT COUNT(*) AS event_count,
                       COUNT(DISTINCT source_id) AS source_actor_count
                FROM log_event
                WHERE ability_game_id = ?
                  AND source_id IS NOT NULL
                """,
                (requested,),
            ).fetchone()

            grouped = db.execute(
                """
                SELECT
                    e.source_id AS actor_id,
                    COUNT(*) AS event_count,
                    COUNT(DISTINCT e.report_code || ':' || e.fight_id) AS report_fight_groups,
                    MAX(a.name) AS name,
                    MAX(a.display_name) AS display_name,
                    MAX(a.actor_type) AS actor_type,
                    MAX(a.role) AS role,
                    MAX(a.raw_json) AS raw_json,
                    SUM(CASE WHEN a.actor_id IS NOT NULL THEN 1 ELSE 0 END) AS matched_rows
                FROM log_event e
                LEFT JOIN log_actor a
                  ON a.report_code = e.report_code
                 AND a.fight_id = e.fight_id
                 AND a.actor_id = e.source_id
                WHERE e.ability_game_id = ?
                  AND e.source_id IS NOT NULL
                GROUP BY e.source_id
                ORDER BY event_count DESC, actor_id
                """,
                (requested,),
            ).fetchall()

        rows = tuple(
            RotationDDPeriodicEsoLogsActorProvenanceRow(
                actor_id=int(row["actor_id"]),
                event_count=int(row["event_count"] or 0),
                report_fight_groups=int(row["report_fight_groups"] or 0),
                name=self._text(row["name"]),
                display_name=self._text(row["display_name"]),
                actor_type=self._text(row["actor_type"]),
                role=self._text(row["role"]),
                owner_hints=self._owner_hints(row["raw_json"]),
            )
            for row in grouped
        )
        matched_actor_count = sum(1 for row in grouped if int(row["matched_rows"] or 0) > 0)
        unresolved: list[str] = []
        if rows and matched_actor_count == 0:
            unresolved.append("ability sources exist but none matched imported log_actor metadata")
        if rows and not any(row.owner_hints for row in rows):
            unresolved.append(
                "imported actor metadata exposes no owner/pet/master/parent/summon linkage hints for observed sources"
            )
        return RotationDDPeriodicEsoLogsActorProvenanceReport(
            ability_id=requested,
            event_count=int(totals["event_count"] or 0) if totals is not None else 0,
            source_actor_count=int(totals["source_actor_count"] or 0) if totals is not None else 0,
            matched_actor_count=matched_actor_count,
            rows=rows,
            unresolved=tuple(unresolved),
        )

    @staticmethod
    def _text(value) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _owner_hints(raw_json) -> tuple[str, ...]:
        text = str(raw_json or "").strip()
        if not text:
            return ()
        try:
            payload = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return ()
        if not isinstance(payload, dict):
            return ()
        hints: list[str] = []
        for key, value in payload.items():
            normalized = str(key).casefold()
            if not any(token in normalized for token in _OWNER_KEY_TOKENS):
                continue
            rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
            hints.append(f"{key}={rendered}")
        return tuple(hints)


__all__ = [
    "RotationDDPeriodicEsoLogsActorProvenanceReport",
    "RotationDDPeriodicEsoLogsActorProvenanceRow",
    "RotationDDPeriodicEsoLogsActorProvenanceService",
]
