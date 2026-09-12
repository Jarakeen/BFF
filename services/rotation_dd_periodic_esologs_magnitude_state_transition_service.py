from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id
from services.esologs_event_interpreter import (
    BUFF_APPLY_EVENTS,
    BUFF_REFRESH_EVENTS,
    BUFF_REMOVE_EVENTS,
    DEBUFF_APPLY_EVENTS,
    DEBUFF_REFRESH_EVENTS,
    DEBUFF_REMOVE_EVENTS,
)


_STATE_APPLY_OR_REFRESH = (
    BUFF_APPLY_EVENTS
    | BUFF_REFRESH_EVENTS
    | DEBUFF_APPLY_EVENTS
    | DEBUFF_REFRESH_EVENTS
)
_STATE_REMOVE = BUFF_REMOVE_EVENTS | DEBUFF_REMOVE_EVENTS
_STATE_EVENT_TYPES = tuple(sorted(_STATE_APPLY_OR_REFRESH | _STATE_REMOVE))
_CAST_TYPES = ("cast", "completecast", "begincast")


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsStateEventEvidence:
    timestamp_ms: float
    event_index: int
    event_type: str
    source_id: int | None
    target_id: int | None
    ability_game_id: int | None
    ability_name: str | None


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsMagnitudeTransition:
    report_code: str
    fight_id: int
    source_id: int
    target_id: int
    cast_track_id: int
    hit_type: int | None
    from_timestamp_ms: float
    to_timestamp_ms: float
    from_amount: float
    to_amount: float
    state_events: tuple[RotationDDPeriodicEsoLogsStateEventEvidence, ...]

    @property
    def has_observed_state_change(self) -> bool:
        return bool(self.state_events)


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport:
    skill_entity_id: str
    periodic_ability_id: int
    transitions: tuple[RotationDDPeriodicEsoLogsMagnitudeTransition, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def transitions_with_state_change(self) -> int:
        return sum(1 for item in self.transitions if item.has_observed_state_change)

    @property
    def transitions_without_state_change(self) -> int:
        return sum(1 for item in self.transitions if not item.has_observed_state_change)


class RotationDDPeriodicEsoLogsMagnitudeStateTransitionService:
    """Compare periodic tick magnitude with net source/target state at tick boundaries.

    Canonical lower-snake identity selects cast anchors. Numeric periodic/effect IDs
    remain ESO Logs evidence handles only. State is replayed in exact timestamp/event
    order and compared at the two tick boundaries, so transient remove/apply churn that
    returns to the same state is not reported as a magnitude-state transition.
    Results remain observational and never promote snapshot-vs-dynamic policy.
    """

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
        periodic_ability_id: int,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport:
        identity = ability_entity_id(skill_entity_id)
        if not identity:
            return self._report(
                "", periodic_ability_id, unresolved=("canonical skill identity is required",)
            )
        if not self.canonical_database_path.is_file():
            raise FileNotFoundError(self.canonical_database_path)
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)
        if int(periodic_ability_id) <= 0:
            return self._report(
                identity,
                periodic_ability_id,
                unresolved=("positive observational periodic ability ID is required",),
            )

        resolution = self.coefficients.resolve_entity_id(identity)
        aliases: set[int] = set()
        unresolved: list[str] = []
        if resolution.rank is not None:
            aliases.update(
                self._numeric_aliases(
                    resolution.rank.skill_id,
                    resolution.rank.morph,
                    resolution.rank.base_ability_id,
                )
            )
        elif resolution.unresolved:
            unresolved.extend(
                str(item).strip() for item in resolution.unresolved if str(item).strip()
            )

        transitions: list[RotationDDPeriodicEsoLogsMagnitudeTransition] = []
        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return self._report(
                    identity,
                    periodic_ability_id,
                    unresolved=tuple(dict.fromkeys((*unresolved, schema_error))),
                )

            casts = tuple(
                row
                for row in self._cast_rows(
                    db,
                    report_code=report_code,
                    fight_id=fight_id,
                    source_id=source_id,
                )
                if self._matches_cast_identity(row, identity=identity, aliases=aliases)
            )
            if not casts:
                unresolved.append(f"{identity}: no matching cast observations found")
                return self._report(
                    identity,
                    periodic_ability_id,
                    unresolved=tuple(dict.fromkeys(unresolved)),
                )

            anchor_type = next(
                kind for kind in _CAST_TYPES if any(self._event_type(row) == kind for row in casts)
            )
            anchor_tracks: set[tuple[str, int, int, int]] = set()
            groups: set[tuple[str, int, int]] = set()
            for row in casts:
                if (
                    self._event_type(row) != anchor_type
                    or row["source_id"] is None
                    or row["cast_track_id"] is None
                ):
                    continue
                key = (
                    str(row["report_code"]),
                    int(row["fight_id"]),
                    int(row["source_id"]),
                    int(row["cast_track_id"]),
                )
                anchor_tracks.add(key)
                groups.add(key[:3])

            for group_report, group_fight, group_source in groups:
                periodic_rows = self._periodic_rows(
                    db,
                    report_code=group_report,
                    fight_id=group_fight,
                    source_id=group_source,
                    periodic_ability_id=int(periodic_ability_id),
                )
                grouped: dict[tuple[int, int, int | None], list[sqlite3.Row]] = {}
                for row in periodic_rows:
                    if (
                        row["cast_track_id"] is None
                        or row["target_id"] is None
                        or row["amount"] is None
                    ):
                        continue
                    track = int(row["cast_track_id"])
                    if (group_report, group_fight, group_source, track) not in anchor_tracks:
                        continue
                    key = (
                        track,
                        int(row["target_id"]),
                        None if row["hit_type"] is None else int(row["hit_type"]),
                    )
                    grouped.setdefault(key, []).append(row)

                if not grouped:
                    continue

                relevant_actors = {group_source}
                relevant_actors.update(target for _, target, _ in grouped)
                state_rows = self._state_rows_for_actors(
                    db,
                    report_code=group_report,
                    fight_id=group_fight,
                    actor_ids=tuple(sorted(relevant_actors)),
                )

                boundaries = {
                    (float(row["timestamp"]), int(row["event_index"]))
                    for rows in grouped.values()
                    for row in rows
                }
                snapshots = self._snapshots_at_boundaries(
                    state_rows,
                    boundaries=tuple(sorted(boundaries)),
                )

                for (track, target, hit_type), rows in grouped.items():
                    ordered = sorted(
                        rows,
                        key=lambda row: (float(row["timestamp"]), int(row["event_index"])),
                    )
                    actor_filter = {group_source, target}
                    for previous, current in zip(ordered, ordered[1:]):
                        from_amount = float(previous["amount"])
                        to_amount = float(current["amount"])
                        if from_amount == to_amount:
                            continue
                        previous_key = (
                            float(previous["timestamp"]),
                            int(previous["event_index"]),
                        )
                        current_key = (
                            float(current["timestamp"]),
                            int(current["event_index"]),
                        )
                        state_events = self._net_state_delta(
                            snapshots[previous_key],
                            snapshots[current_key],
                            relevant_actors=actor_filter,
                        )
                        transitions.append(
                            RotationDDPeriodicEsoLogsMagnitudeTransition(
                                report_code=group_report,
                                fight_id=group_fight,
                                source_id=group_source,
                                target_id=target,
                                cast_track_id=track,
                                hit_type=hit_type,
                                from_timestamp_ms=previous_key[0],
                                to_timestamp_ms=current_key[0],
                                from_amount=from_amount,
                                to_amount=to_amount,
                                state_events=state_events,
                            )
                        )

        if not transitions:
            unresolved.append(
                f"{identity}: no same-cast periodic amount-change transitions were observed"
            )
        return self._report(
            identity,
            periodic_ability_id,
            transitions=tuple(transitions),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def _snapshots_at_boundaries(
        cls,
        rows: tuple[sqlite3.Row, ...],
        *,
        boundaries: tuple[tuple[float, int], ...],
    ) -> dict[
        tuple[float, int],
        tuple[
            dict[tuple[int, int], int],
            dict[tuple[int, int], sqlite3.Row],
        ],
    ]:
        active: dict[tuple[int, int], int] = {}
        last_event: dict[tuple[int, int], sqlite3.Row] = {}
        snapshots = {}
        row_index = 0
        ordered_rows = tuple(
            sorted(rows, key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
        )
        for boundary in boundaries:
            while row_index < len(ordered_rows):
                row = ordered_rows[row_index]
                row_key = (float(row["timestamp"]), int(row["event_index"]))
                if row_key > boundary:
                    break
                cls._apply_state_row(active, last_event, row)
                row_index += 1
            snapshots[boundary] = (dict(active), dict(last_event))
        return snapshots

    @classmethod
    def _apply_state_row(
        cls,
        active: dict[tuple[int, int], int],
        last_event: dict[tuple[int, int], sqlite3.Row],
        row: sqlite3.Row,
    ) -> None:
        if row["target_id"] is None or row["ability_game_id"] is None:
            return
        key = (int(row["target_id"]), int(row["ability_game_id"]))
        event_type = cls._event_type(row)
        last_event[key] = row
        if event_type in _STATE_REMOVE:
            active.pop(key, None)
            return
        if event_type in _STATE_APPLY_OR_REFRESH:
            stack = row["stack"]
            active[key] = 1 if stack is None else int(stack)

    @classmethod
    def _net_state_delta(
        cls,
        before_snapshot: tuple[
            dict[tuple[int, int], int],
            dict[tuple[int, int], sqlite3.Row],
        ],
        after_snapshot: tuple[
            dict[tuple[int, int], int],
            dict[tuple[int, int], sqlite3.Row],
        ],
        *,
        relevant_actors: set[int],
    ) -> tuple[RotationDDPeriodicEsoLogsStateEventEvidence, ...]:
        before, _before_events = before_snapshot
        after, after_events = after_snapshot
        keys = {
            key
            for key in set(before) | set(after)
            if key[0] in relevant_actors
        }
        evidence: list[RotationDDPeriodicEsoLogsStateEventEvidence] = []
        for key in sorted(keys):
            before_value = before.get(key)
            after_value = after.get(key)
            if before_value == after_value:
                continue
            row = after_events.get(key)
            if row is None:
                continue
            if before_value is None:
                event_type = "state_gained"
            elif after_value is None:
                event_type = "state_lost"
            else:
                event_type = "state_changed"
            evidence.append(cls._state_evidence(row, event_type=event_type))
        return tuple(evidence)

    def _numeric_aliases(self, skill_id: int, morph: int, base_ability_id: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            aliases = {int(base_ability_id)} if int(base_ability_id) > 0 else set()
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='skill_rank'"
            ).fetchone() is not None:
                aliases.update(
                    int(row["ability_id"])
                    for row in db.execute(
                        "SELECT ability_id FROM skill_rank WHERE skill_id=? "
                        "AND COALESCE(morph,0)=? AND ability_id IS NOT NULL",
                        (int(skill_id), int(morph)),
                    ).fetchall()
                )
            return tuple(sorted(value for value in aliases if value > 0))

    def _open_logs(self) -> sqlite3.Connection:
        uri = f"file:{self.logs_database_path.resolve().as_posix()}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only = ON")
        return db

    @staticmethod
    def _schema_error(db: sqlite3.Connection) -> str | None:
        if db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='log_event'"
        ).fetchone() is None:
            return "log_event table is unavailable"
        required = {
            "report_code",
            "fight_id",
            "event_index",
            "timestamp",
            "event_type",
            "source_id",
            "target_id",
            "ability_game_id",
            "amount",
            "hit_type",
            "cast_track_id",
            "stack",
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
    def _cast_rows(
        db: sqlite3.Connection,
        *,
        report_code: str | None,
        fight_id: int | None,
        source_id: int | None,
    ) -> tuple[sqlite3.Row, ...]:
        clauses = ["lower(event_type) IN ('cast','begincast','completecast')"]
        params: list[object] = []
        if report_code is not None:
            clauses.append("report_code=?")
            params.append(str(report_code))
        if fight_id is not None:
            clauses.append("fight_id=?")
            params.append(int(fight_id))
        if source_id is not None:
            clauses.append("source_id=?")
            params.append(int(source_id))
        return tuple(
            db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event WHERE "
                + " AND ".join(clauses)
                + " ORDER BY report_code,fight_id,source_id,timestamp,event_index",
                tuple(params),
            ).fetchall()
        )

    @staticmethod
    def _periodic_rows(
        db: sqlite3.Connection,
        *,
        report_code: str,
        fight_id: int,
        source_id: int,
        periodic_ability_id: int,
    ) -> tuple[sqlite3.Row, ...]:
        return tuple(
            db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                "target_id,ability_game_id,amount,hit_type,cast_track_id,raw_json "
                "FROM log_event WHERE report_code=? AND fight_id=? AND source_id=? "
                "AND ability_game_id=? AND amount IS NOT NULL ORDER BY timestamp,event_index",
                (report_code, int(fight_id), int(source_id), int(periodic_ability_id)),
            ).fetchall()
        )

    @staticmethod
    def _state_rows_for_actors(
        db: sqlite3.Connection,
        *,
        report_code: str,
        fight_id: int,
        actor_ids: tuple[int, ...],
    ) -> tuple[sqlite3.Row, ...]:
        if not actor_ids:
            return ()
        type_placeholders = ",".join("?" for _ in _STATE_EVENT_TYPES)
        actor_placeholders = ",".join("?" for _ in actor_ids)
        return tuple(
            db.execute(
                f"SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                f"target_id,ability_game_id,stack,raw_json FROM log_event "
                f"WHERE report_code=? AND fight_id=? "
                f"AND lower(event_type) IN ({type_placeholders}) "
                f"AND target_id IN ({actor_placeholders}) ORDER BY timestamp,event_index",
                (report_code, int(fight_id), *_STATE_EVENT_TYPES, *actor_ids),
            ).fetchall()
        )

    @classmethod
    def _state_evidence(
        cls,
        row: sqlite3.Row,
        *,
        event_type: str | None = None,
    ) -> RotationDDPeriodicEsoLogsStateEventEvidence:
        return RotationDDPeriodicEsoLogsStateEventEvidence(
            timestamp_ms=float(row["timestamp"]),
            event_index=int(row["event_index"]),
            event_type=event_type or cls._event_type(row),
            source_id=None if row["source_id"] is None else int(row["source_id"]),
            target_id=None if row["target_id"] is None else int(row["target_id"]),
            ability_game_id=(
                None if row["ability_game_id"] is None else int(row["ability_game_id"])
            ),
            ability_name=cls._ability_name_from_raw(row["raw_json"]),
        )

    @classmethod
    def _matches_cast_identity(
        cls,
        row: sqlite3.Row,
        *,
        identity: str,
        aliases: set[int],
    ) -> bool:
        raw_name = cls._ability_name_from_raw(row["raw_json"])
        if raw_name:
            return ability_entity_id(raw_name) == identity
        value = row["ability_game_id"]
        return value is not None and int(value) in aliases

    @staticmethod
    def _event_type(row: sqlite3.Row) -> str:
        return str(row["event_type"] or "").strip().lower()

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
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _report(
        skill_entity_id: str,
        periodic_ability_id: int,
        *,
        transitions: tuple[RotationDDPeriodicEsoLogsMagnitudeTransition, ...] = (),
        unresolved: tuple[str, ...] = (),
    ) -> RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport:
        return RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport(
            skill_entity_id=skill_entity_id,
            periodic_ability_id=int(periodic_ability_id),
            transitions=transitions,
            unresolved=unresolved,
        )


__all__ = [
    "RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport",
    "RotationDDPeriodicEsoLogsMagnitudeStateTransitionService",
    "RotationDDPeriodicEsoLogsMagnitudeTransition",
    "RotationDDPeriodicEsoLogsStateEventEvidence",
]
