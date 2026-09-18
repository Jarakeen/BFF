from __future__ import annotations

"""Inspect source evidence for canonical gear-set entities not normalized into gear_set.

This is diagnostic only. It does not mutate eso.db. The goal is to distinguish
"normalization debt with usable source payload" from "identity only, no source
payload", especially for arena-weapon entities.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class ExtremeEntityOnlyGearSourceRow:
    entity_id: str
    name: str
    source_count: int
    sources: tuple[str, ...]
    source_entity_types: tuple[str, ...]
    raw_json_count: int
    raw_json_keys: tuple[str, ...]

    @property
    def has_source_evidence(self) -> bool:
        return self.source_count > 0

    @property
    def has_raw_payload(self) -> bool:
        return self.raw_json_count > 0


@dataclass(frozen=True)
class ExtremeEntityOnlyGearSourceAudit:
    rows: tuple[ExtremeEntityOnlyGearSourceRow, ...]

    @property
    def entity_count(self) -> int:
        return len(self.rows)

    @property
    def with_source_count(self) -> int:
        return sum(row.has_source_evidence for row in self.rows)

    @property
    def with_raw_payload_count(self) -> int:
        return sum(row.has_raw_payload for row in self.rows)

    @property
    def without_source_count(self) -> int:
        return self.entity_count - self.with_source_count


class ExtremeEntityOnlyGearSourceAuditService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    @staticmethod
    def _json_keys(raw: str | None) -> tuple[str, ...]:
        if not raw:
            return ()
        try:
            payload = json.loads(raw)
        except Exception:
            return ()
        if isinstance(payload, dict):
            return tuple(sorted(str(key) for key in payload.keys()))
        return (f"<{type(payload).__name__}>",)

    def build(self) -> ExtremeEntityOnlyGearSourceAudit:
        with sqlite3.connect(self.database_path) as db:
            tables = {
                str(row[0])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if not {"entity", "gear_set"}.issubset(tables):
                return ExtremeEntityOnlyGearSourceAudit(())

            entities = db.execute(
                """
                SELECT e.id, e.name
                FROM entity e
                LEFT JOIN gear_set gs
                  ON LOWER(TRIM(gs.name)) = LOWER(TRIM(e.name))
                WHERE e.entity_type = 'gear_set'
                  AND e.name IS NOT NULL
                  AND TRIM(e.name) <> ''
                  AND gs.id IS NULL
                ORDER BY e.name COLLATE NOCASE, e.id
                """
            ).fetchall()

            has_source_table = "entity_source" in tables
            rows: list[ExtremeEntityOnlyGearSourceRow] = []
            for entity_id, name in entities:
                source_rows = ()
                if has_source_table:
                    source_rows = db.execute(
                        """
                        SELECT source, source_entity_type, raw_json
                        FROM entity_source
                        WHERE entity_id = ?
                        ORDER BY source, source_entity_type, source_id
                        """,
                        (str(entity_id),),
                    ).fetchall()

                sources = tuple(
                    dict.fromkeys(
                        str(source or "").strip()
                        for source, _source_type, _raw in source_rows
                        if str(source or "").strip()
                    )
                )
                source_types = tuple(
                    dict.fromkeys(
                        str(source_type or "").strip()
                        for _source, source_type, _raw in source_rows
                        if str(source_type or "").strip()
                    )
                )
                raw_payloads = tuple(
                    str(raw)
                    for _source, _source_type, raw in source_rows
                    if raw is not None and str(raw).strip()
                )
                keys: set[str] = set()
                for raw in raw_payloads:
                    keys.update(self._json_keys(raw))

                rows.append(
                    ExtremeEntityOnlyGearSourceRow(
                        entity_id=str(entity_id),
                        name=str(name),
                        source_count=len(source_rows),
                        sources=sources,
                        source_entity_types=source_types,
                        raw_json_count=len(raw_payloads),
                        raw_json_keys=tuple(sorted(keys)),
                    )
                )

        return ExtremeEntityOnlyGearSourceAudit(rows=tuple(rows))


__all__ = [
    "ExtremeEntityOnlyGearSourceRow",
    "ExtremeEntityOnlyGearSourceAudit",
    "ExtremeEntityOnlyGearSourceAuditService",
]
