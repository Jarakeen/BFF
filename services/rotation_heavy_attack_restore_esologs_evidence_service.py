from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.esologs_event_interpreter import EsoLogsEventInterpreter, SemanticEventKind


@dataclass(frozen=True)
class RotationHeavyAttackRestoreObservation:
    report_code: str
    fight_id: int
    event_index: int
    timestamp: float
    source_id: int | None
    ability_game_id: int | None
    ability_name: str | None
    resource_change: float
    resource_change_type: int | None
    waste: float | None
    max_resource_amount: float | None


@dataclass(frozen=True)
class RotationHeavyAttackRestoreObservationReport:
    observations: tuple[RotationHeavyAttackRestoreObservation, ...]
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationHeavyAttackRestoreActorAlias:
    report_code: str
    fight_id: int
    actor_id: int
    name: str | None
    display_name: str | None


@dataclass(frozen=True)
class RotationHeavyAttackRestoreResourceAliasCandidate:
    source_id: int
    ability_game_id: int | None
    ability_name: str | None
    resource_change_type: int | None
    event_count: int
    minimum_restore: float
    maximum_restore: float


class RotationHeavyAttackRestoreEsoLogsEvidenceService:
    """Surface observed positive resource restores for reviewed heavy-attack aliases.

    This is observational evidence only. Caller-supplied names or numeric aliases
    select candidate heavy-attack resource-change events. Numeric log ids are not
    promoted to canonical skill identity, resource type enums are preserved raw,
    and observed restore amounts are never promoted to live game constants by this
    service.
    """

    _REQUIRED_COLUMNS = {
        "report_code", "fight_id", "event_index", "timestamp", "event_type",
        "source_id", "source_is_friendly", "target_id", "target_instance",
        "target_is_friendly", "ability_game_id", "extra_ability_game_id", "amount",
        "hit_type", "tick", "cast_track_id", "resource_change", "resource_change_type",
        "other_resource_change", "max_resource_amount", "waste", "overheal",
        "absorbed", "stack", "raw_json",
    }

    def discover(
        self,
        database_path: str | Path,
        *,
        report_code: str,
        fight_id: int,
        ability_names: tuple[str, ...] = (),
        ability_game_ids: tuple[int, ...] = (),
        source_id: int | None = None,
    ) -> RotationHeavyAttackRestoreObservationReport:
        names, ids = self._normalize_aliases(ability_names, ability_game_ids)
        report = str(report_code or "").strip()
        if not report:
            raise ValueError("report_code is required")
        fight = int(fight_id)
        if fight < 0:
            raise ValueError("fight_id cannot be negative")

        path = Path(database_path)
        with self._open_read_only(path) as db:
            unresolved = self._schema_unresolved(db)
            if unresolved:
                return RotationHeavyAttackRestoreObservationReport(observations=(), unresolved=unresolved)
            observations = self._discover_fight(
                db,
                report_code=report,
                fight_id=fight,
                names=names,
                ids=ids,
                source_id=source_id,
            )

        return self._report(observations)

    def discover_corpus(
        self,
        database_path: str | Path,
        *,
        ability_names: tuple[str, ...] = (),
        ability_game_ids: tuple[int, ...] = (),
        source_id: int | None = None,
        report_code: str | None = None,
    ) -> RotationHeavyAttackRestoreObservationReport:
        """Scan all matching fights without promoting any observation to canonical truth."""

        names, ids = self._normalize_aliases(ability_names, ability_game_ids)
        report = None if report_code is None else str(report_code or "").strip()
        if report_code is not None and not report:
            raise ValueError("report_code cannot be empty when supplied")

        path = Path(database_path)
        with self._open_read_only(path) as db:
            unresolved = self._schema_unresolved(db)
            if unresolved:
                return RotationHeavyAttackRestoreObservationReport(observations=(), unresolved=unresolved)

            query = "SELECT DISTINCT report_code, fight_id FROM log_event"
            params: tuple[object, ...] = ()
            if report is not None:
                query += " WHERE report_code = ?"
                params = (report,)
            query += " ORDER BY report_code ASC, fight_id ASC"

            observations: list[RotationHeavyAttackRestoreObservation] = []
            for row in db.execute(query, params):
                observations.extend(
                    self._discover_fight(
                        db,
                        report_code=str(row["report_code"]),
                        fight_id=int(row["fight_id"]),
                        names=names,
                        ids=ids,
                        source_id=source_id,
                    )
                )

        return self._report(tuple(observations))

    def discover_actor_aliases(
        self,
        database_path: str | Path,
        *,
        actor_names: tuple[str, ...],
        report_code: str | None = None,
    ) -> tuple[RotationHeavyAttackRestoreActorAlias, ...]:
        """Resolve reviewed character/account names to raw ESO Logs actor ids."""

        names = frozenset(
            str(value or "").strip().casefold()
            for value in actor_names
            if str(value or "").strip()
        )
        if not names:
            raise ValueError("actor alias discovery requires at least one reviewed actor name")
        report = None if report_code is None else str(report_code or "").strip()
        if report_code is not None and not report:
            raise ValueError("report_code cannot be empty when supplied")

        with self._open_read_only(Path(database_path)) as db:
            tables = {
                str(row[0])
                for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            if "log_actor" not in tables:
                return ()
            query = "SELECT report_code, fight_id, actor_id, name, display_name FROM log_actor"
            params: list[object] = []
            clauses: list[str] = []
            if report is not None:
                clauses.append("report_code = ?")
                params.append(report)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY report_code, fight_id, actor_id"
            rows = []
            for row in db.execute(query, tuple(params)):
                values = {
                    str(row["name"] or "").strip().casefold(),
                    str(row["display_name"] or "").strip().casefold(),
                }
                if not (names & values):
                    continue
                rows.append(
                    RotationHeavyAttackRestoreActorAlias(
                        report_code=str(row["report_code"]),
                        fight_id=int(row["fight_id"]),
                        actor_id=int(row["actor_id"]),
                        name=None if row["name"] is None else str(row["name"]),
                        display_name=(
                            None if row["display_name"] is None else str(row["display_name"])
                        ),
                    )
                )
            return tuple(rows)

    def discover_positive_resource_aliases(
        self,
        database_path: str | Path,
        *,
        source_ids: tuple[int, ...],
        report_code: str | None = None,
    ) -> tuple[RotationHeavyAttackRestoreResourceAliasCandidate, ...]:
        """List raw positive-resource ability aliases for reviewed source actors."""

        ids = tuple(sorted({int(value) for value in source_ids}))
        if not ids:
            raise ValueError("resource alias discovery requires at least one source id")
        report = None if report_code is None else str(report_code or "").strip()
        if report_code is not None and not report:
            raise ValueError("report_code cannot be empty when supplied")

        with self._open_read_only(Path(database_path)) as db:
            unresolved = self._schema_unresolved(db)
            if unresolved:
                return ()
            placeholders = ",".join("?" for _ in ids)
            query = f"""
                SELECT source_id, ability_game_id,
                       MIN(json_extract(raw_json, '$.ability.name')) AS raw_ability_name,
                       resource_change_type,
                       COUNT(*) AS event_count,
                       MIN(resource_change) AS minimum_restore,
                       MAX(resource_change) AS maximum_restore
                FROM log_event
                WHERE event_type = 'resourcechange'
                  AND resource_change > 0
                  AND source_id IN ({placeholders})
            """
            params: list[object] = list(ids)
            if report is not None:
                query += " AND report_code = ?"
                params.append(report)
            query += " GROUP BY source_id, ability_game_id, resource_change_type"
            query += " ORDER BY event_count DESC, source_id, ability_game_id"
            return tuple(
                RotationHeavyAttackRestoreResourceAliasCandidate(
                    source_id=int(row["source_id"]),
                    ability_game_id=(
                        None if row["ability_game_id"] is None else int(row["ability_game_id"])
                    ),
                    ability_name=(
                        None if row["raw_ability_name"] is None else str(row["raw_ability_name"])
                    ),
                    resource_change_type=(
                        None
                        if row["resource_change_type"] is None
                        else int(row["resource_change_type"])
                    ),
                    event_count=int(row["event_count"]),
                    minimum_restore=float(row["minimum_restore"]),
                    maximum_restore=float(row["maximum_restore"]),
                )
                for row in db.execute(query, tuple(params))
            )

    @staticmethod
    def _normalize_aliases(
        ability_names: tuple[str, ...],
        ability_game_ids: tuple[int, ...],
    ) -> tuple[frozenset[str], frozenset[int]]:
        names = frozenset(
            str(value or "").strip().casefold()
            for value in ability_names
            if str(value or "").strip()
        )
        ids = frozenset(int(value) for value in ability_game_ids)
        if not names and not ids:
            raise ValueError(
                "heavy restore observation discovery requires at least one reviewed ability alias"
            )
        return names, ids

    @staticmethod
    def _open_read_only(path: Path) -> sqlite3.Connection:
        if not path.exists():
            raise FileNotFoundError(path)
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        return db

    def _schema_unresolved(self, db: sqlite3.Connection) -> tuple[str, ...]:
        tables = {
            str(row[0])
            for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if "log_event" not in tables:
            return ("log_event table is unavailable",)
        columns = {
            str(row["name"])
            for row in db.execute("PRAGMA table_info(log_event)")
        }
        missing = tuple(sorted(self._REQUIRED_COLUMNS - columns))
        if missing:
            return (
                "log_event schema is missing required columns: " + ", ".join(missing),
            )
        return ()

    @staticmethod
    def _discover_fight(
        db: sqlite3.Connection,
        *,
        report_code: str,
        fight_id: int,
        names: frozenset[str],
        ids: frozenset[int],
        source_id: int | None,
    ) -> tuple[RotationHeavyAttackRestoreObservation, ...]:
        interpreter = EsoLogsEventInterpreter(db)
        events = interpreter.iter_fight(
            report_code,
            fight_id,
            event_kinds={SemanticEventKind.RESOURCE_CHANGE},
        )
        observations: list[RotationHeavyAttackRestoreObservation] = []
        for event in events:
            if source_id is not None and event.source_id != int(source_id):
                continue
            name_match = (
                event.ability_name is not None
                and event.ability_name.strip().casefold() in names
            )
            id_match = (
                event.ability_game_id is not None
                and event.ability_game_id in ids
            )
            if not (name_match or id_match):
                continue
            amount = event.resource_change
            if amount is None or float(amount) <= 0.0:
                continue
            observations.append(
                RotationHeavyAttackRestoreObservation(
                    report_code=event.report_code,
                    fight_id=event.fight_id,
                    event_index=event.event_index,
                    timestamp=event.timestamp,
                    source_id=event.source_id,
                    ability_game_id=event.ability_game_id,
                    ability_name=event.ability_name,
                    resource_change=float(amount),
                    resource_change_type=event.resource_change_type,
                    waste=event.waste,
                    max_resource_amount=event.max_resource_amount,
                )
            )
        return tuple(observations)

    @staticmethod
    def _report(
        observations: tuple[RotationHeavyAttackRestoreObservation, ...]
        | list[RotationHeavyAttackRestoreObservation],
    ) -> RotationHeavyAttackRestoreObservationReport:
        rows = tuple(observations)
        unresolved: tuple[str, ...] = ()
        if not rows:
            unresolved = (
                "no positive resource-change events matched the reviewed heavy-attack aliases",
            )
        return RotationHeavyAttackRestoreObservationReport(
            observations=rows,
            unresolved=unresolved,
        )


__all__ = [
    "RotationHeavyAttackRestoreActorAlias",
    "RotationHeavyAttackRestoreEsoLogsEvidenceService",
    "RotationHeavyAttackRestoreObservation",
    "RotationHeavyAttackRestoreObservationReport",
    "RotationHeavyAttackRestoreResourceAliasCandidate",
]
