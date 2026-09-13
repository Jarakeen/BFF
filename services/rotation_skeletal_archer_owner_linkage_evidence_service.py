from __future__ import annotations

"""Research-only owner-linkage adequacy audit for Skeletal Archer pet evidence.

The pet-source discovery path can identify strong friendly non-player periodic candidates,
but executable ownership requires evidence that links the pet source actor to the player
who cast Skeletal Archer. This service inspects imported schema/metadata for such hints
without treating timing co-occurrence as ownership.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any


SKELETAL_ARCHER_PERIODIC_EVIDENCE_ID = 122774
_LINK_TOKENS = ("owner", "master", "parent", "summon", "pet", "companion")


@dataclass(frozen=True)
class RotationSkeletalArcherOwnerLinkageEvidenceReport:
    periodic_ability_id: int
    event_count: int
    source_actor_count: int
    log_actor_columns: tuple[str, ...]
    actor_linkage_columns: tuple[str, ...]
    raw_linkage_paths: tuple[str, ...]
    raw_linkage_sample_count: int
    unresolved: tuple[str, ...] = ()

    @property
    def has_imported_linkage_evidence(self) -> bool:
        return bool(self.actor_linkage_columns or self.raw_linkage_paths)


class RotationSkeletalArcherOwnerLinkageEvidenceService:
    """Inspect imported ESO Logs evidence for explicit pet-to-owner linkage hints.

    This is an adequacy audit, not an ownership resolver. A matching metadata key is only
    a hint that can justify deeper review; absence of such keys supports parking the
    current corpus for owner-linkage work.
    """

    def __init__(self, logs_database_path: str | Path) -> None:
        self.logs_database_path = Path(logs_database_path)

    def inspect(
        self,
        *,
        periodic_ability_id: int = SKELETAL_ARCHER_PERIODIC_EVIDENCE_ID,
    ) -> RotationSkeletalArcherOwnerLinkageEvidenceReport:
        with self._open_logs() as db:
            event_columns = self._columns(db, "log_event")
            actor_columns = self._columns(db, "log_actor")
            unresolved: list[str] = []
            if not event_columns:
                return self._report(periodic_ability_id, unresolved=("log_event table is unavailable",))
            required = {"ability_game_id", "source_id", "raw_json"}
            missing = sorted(required - set(event_columns))
            if missing:
                return self._report(
                    periodic_ability_id,
                    log_actor_columns=actor_columns,
                    unresolved=("log_event missing required columns: " + ", ".join(missing),),
                )

            rows = db.execute(
                """
                SELECT source_id, raw_json
                FROM log_event
                WHERE ability_game_id = ?
                  AND lower(COALESCE(event_type, '')) = 'damage'
                ORDER BY report_code, fight_id, timestamp, event_index
                """,
                (int(periodic_ability_id),),
            ).fetchall()
            source_ids = {int(row["source_id"]) for row in rows if row["source_id"] is not None}

            actor_linkage_columns = tuple(
                column for column in actor_columns if self._is_linkage_name(column)
            )
            raw_paths: set[str] = set()
            raw_samples = 0
            for row in rows:
                payload = self._json_object(row["raw_json"])
                if payload is None:
                    continue
                found = self._linkage_paths(payload)
                if found:
                    raw_samples += 1
                    raw_paths.update(found)

            if not rows:
                unresolved.append(
                    f"no damage events found for periodic evidence id {int(periodic_ability_id)}"
                )
            elif not actor_linkage_columns and not raw_paths:
                unresolved.append(
                    "imported log_actor/log_event metadata exposes no explicit owner/master/parent/summon/pet/companion linkage fields for the reviewed candidate"
                )

            return self._report(
                periodic_ability_id,
                event_count=len(rows),
                source_actor_count=len(source_ids),
                log_actor_columns=actor_columns,
                actor_linkage_columns=actor_linkage_columns,
                raw_linkage_paths=tuple(sorted(raw_paths)),
                raw_linkage_sample_count=raw_samples,
                unresolved=tuple(unresolved),
            )

    def _open_logs(self) -> sqlite3.Connection:
        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        return db

    @staticmethod
    def _columns(db: sqlite3.Connection, table: str) -> tuple[str, ...]:
        try:
            rows = db.execute(f"PRAGMA table_info({table})").fetchall()
        except sqlite3.Error:
            return ()
        return tuple(str(row["name"]) for row in rows)

    @classmethod
    def _is_linkage_name(cls, value: str) -> bool:
        lowered = str(value).casefold()
        return any(token in lowered for token in _LINK_TOKENS)

    @classmethod
    def _linkage_paths(cls, payload: Any, prefix: str = "") -> tuple[str, ...]:
        found: set[str] = set()
        if isinstance(payload, dict):
            for key, value in payload.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if cls._is_linkage_name(str(key)):
                    found.add(path)
                found.update(cls._linkage_paths(value, path))
        elif isinstance(payload, list):
            for index, value in enumerate(payload):
                found.update(cls._linkage_paths(value, f"{prefix}[{index}]"))
        return tuple(sorted(found))

    @staticmethod
    def _json_object(raw_json: object) -> object | None:
        if raw_json in (None, ""):
            return None
        try:
            return json.loads(str(raw_json))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _report(
        periodic_ability_id: int,
        *,
        event_count: int = 0,
        source_actor_count: int = 0,
        log_actor_columns: tuple[str, ...] = (),
        actor_linkage_columns: tuple[str, ...] = (),
        raw_linkage_paths: tuple[str, ...] = (),
        raw_linkage_sample_count: int = 0,
        unresolved: tuple[str, ...] = (),
    ) -> RotationSkeletalArcherOwnerLinkageEvidenceReport:
        return RotationSkeletalArcherOwnerLinkageEvidenceReport(
            periodic_ability_id=int(periodic_ability_id),
            event_count=int(event_count),
            source_actor_count=int(source_actor_count),
            log_actor_columns=tuple(log_actor_columns),
            actor_linkage_columns=tuple(actor_linkage_columns),
            raw_linkage_paths=tuple(raw_linkage_paths),
            raw_linkage_sample_count=int(raw_linkage_sample_count),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "SKELETAL_ARCHER_PERIODIC_EVIDENCE_ID",
    "RotationSkeletalArcherOwnerLinkageEvidenceReport",
    "RotationSkeletalArcherOwnerLinkageEvidenceService",
]
