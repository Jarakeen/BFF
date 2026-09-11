from __future__ import annotations

"""Read-only ESO Logs candidate evidence for Minor Lifesteal runtime behavior.

This service deliberately does not promote observed cadence, ownership, or numeric
ability ids into canonical mechanics. It preserves per-event evidence so a reviewer
can decide which U50 runtime facts are sufficiently supported.
"""

from dataclasses import dataclass
from pathlib import Path
import math
import sqlite3

from services.esologs_event_interpreter import (
    EsoLogsEventInterpreter,
    SemanticCombatEvent,
)


@dataclass(frozen=True)
class RotationHealerMinorLifestealHealObservation:
    report_code: str
    fight_id: int
    event_index: int
    timestamp_seconds: float
    ability_game_id: int | None
    ability_name: str | None
    source_id: int | None
    target_id: int | None
    amount: float | None
    overheal: float | None
    source_target_relation: str
    previous_same_source_damage_event_index: int | None
    previous_same_source_damage_target_id: int | None
    previous_same_source_damage_delta_seconds: float | None
    previous_recipient_damage_event_index: int | None
    previous_recipient_damage_target_id: int | None
    previous_recipient_damage_delta_seconds: float | None


@dataclass(frozen=True)
class RotationHealerMinorLifestealCadenceStream:
    report_code: str
    fight_id: int
    source_id: int | None
    target_id: int | None
    source_target_relation: str
    heal_event_count: int
    observed_intervals_seconds: tuple[float, ...]


@dataclass(frozen=True)
class RotationHealerMinorLifestealEsoLogsEvidenceReport:
    source_path: str
    timestamp_unit: str
    observations: tuple[RotationHealerMinorLifestealHealObservation, ...]
    cadence_streams: tuple[RotationHealerMinorLifestealCadenceStream, ...]
    observed_heal_ability_aliases: tuple[int, ...]
    unresolved: tuple[str, ...]
    evidence_status: str = "candidate"

    def __post_init__(self) -> None:
        if self.evidence_status != "candidate":
            raise ValueError("Minor Lifesteal ESO Logs evidence must remain candidate")

    def to_candidate_fixture_payload(self, *, game_version: str = "U50") -> dict:
        return {
            "schema_version": 1,
            "evidence_status": "candidate",
            "game_version": str(game_version),
            "effect_id": "minor_lifesteal",
            "source_path": self.source_path,
            "timestamp_unit": self.timestamp_unit,
            "observed_heal_ability_aliases": list(self.observed_heal_ability_aliases),
            "observations": [
                {
                    "report_code": item.report_code,
                    "fight_id": item.fight_id,
                    "event_index": item.event_index,
                    "timestamp_seconds": item.timestamp_seconds,
                    "ability_game_id": item.ability_game_id,
                    "ability_name": item.ability_name,
                    "source_id": item.source_id,
                    "target_id": item.target_id,
                    "amount": item.amount,
                    "overheal": item.overheal,
                    "source_target_relation": item.source_target_relation,
                    "previous_same_source_damage_event_index": (
                        item.previous_same_source_damage_event_index
                    ),
                    "previous_same_source_damage_target_id": (
                        item.previous_same_source_damage_target_id
                    ),
                    "previous_same_source_damage_delta_seconds": (
                        item.previous_same_source_damage_delta_seconds
                    ),
                    "previous_recipient_damage_event_index": (
                        item.previous_recipient_damage_event_index
                    ),
                    "previous_recipient_damage_target_id": (
                        item.previous_recipient_damage_target_id
                    ),
                    "previous_recipient_damage_delta_seconds": (
                        item.previous_recipient_damage_delta_seconds
                    ),
                }
                for item in self.observations
            ],
            "cadence_streams": [
                {
                    "report_code": item.report_code,
                    "fight_id": item.fight_id,
                    "source_id": item.source_id,
                    "target_id": item.target_id,
                    "source_target_relation": item.source_target_relation,
                    "heal_event_count": item.heal_event_count,
                    "observed_intervals_seconds": list(
                        item.observed_intervals_seconds
                    ),
                }
                for item in self.cadence_streams
            ],
            "unresolved": list(self.unresolved),
        }


class RotationHealerMinorLifestealEsoLogsEvidenceService:
    """Inspect observed Minor Lifesteal heals without inferring runtime rules."""

    _REQUIRED_LOG_EVENT_COLUMNS = {
        "report_code", "fight_id", "event_index", "timestamp", "event_type",
        "source_id", "source_is_friendly", "target_id", "target_instance",
        "target_is_friendly", "ability_game_id", "extra_ability_game_id",
        "amount", "hit_type", "tick", "cast_track_id", "resource_change",
        "resource_change_type", "other_resource_change", "max_resource_amount",
        "waste", "overheal", "absorbed", "stack", "raw_json",
    }

    _TIMESTAMP_SCALES = {
        "milliseconds": 0.001,
        "seconds": 1.0,
    }

    _EVENT_COLUMNS = """
        report_code, fight_id, event_index, timestamp, event_type,
        source_id, source_is_friendly, target_id, target_instance,
        target_is_friendly, ability_game_id, extra_ability_game_id,
        amount, hit_type, tick, cast_track_id, resource_change,
        resource_change_type, other_resource_change, max_resource_amount,
        waste, overheal, absorbed, stack, raw_json
    """

    def inspect(
        self,
        database_path: str | Path,
        *,
        report_code: str | None = None,
        fight_id: int | None = None,
        timestamp_unit: str = "milliseconds",
        observed_heal_ability_ids: tuple[int, ...] = (),
    ) -> RotationHealerMinorLifestealEsoLogsEvidenceReport:
        path = Path(database_path)
        if not path.exists():
            raise FileNotFoundError(path)

        unit = str(timestamp_unit or "").strip().casefold()
        if unit not in self._TIMESTAMP_SCALES:
            raise ValueError("timestamp_unit must be milliseconds or seconds")
        scale = self._TIMESTAMP_SCALES[unit]

        aliases = {int(value) for value in observed_heal_ability_ids}
        observations: list[RotationHealerMinorLifestealHealObservation] = []
        unresolved: list[str] = []

        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if "log_event" not in tables:
                return RotationHealerMinorLifestealEsoLogsEvidenceReport(
                    source_path=str(path),
                    timestamp_unit=unit,
                    observations=(),
                    cadence_streams=(),
                    observed_heal_ability_aliases=tuple(sorted(aliases)),
                    unresolved=("log_event table is unavailable",),
                )

            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(log_event)")
            }
            missing_columns = tuple(
                sorted(self._REQUIRED_LOG_EVENT_COLUMNS - columns)
            )
            if missing_columns:
                return RotationHealerMinorLifestealEsoLogsEvidenceReport(
                    source_path=str(path),
                    timestamp_unit=unit,
                    observations=(),
                    cadence_streams=(),
                    observed_heal_ability_aliases=tuple(sorted(aliases)),
                    unresolved=(
                        "log_event schema is missing required columns: "
                        + ", ".join(missing_columns),
                    ),
                )

            interpreter = EsoLogsEventInterpreter(connection)
            events = self._candidate_heal_events(
                connection,
                interpreter=interpreter,
                aliases=aliases,
                report_code=report_code,
                fight_id=fight_id,
            )
            for event in events:
                if not self._is_minor_lifesteal_heal(event, aliases=aliases):
                    continue

                previous_damage = self._previous_damage_by_actor(
                    connection,
                    interpreter=interpreter,
                    event=event,
                    actor_id=event.source_id,
                )
                previous_recipient_damage = self._previous_damage_by_actor(
                    connection,
                    interpreter=interpreter,
                    event=event,
                    actor_id=event.target_id,
                )
                delta = self._event_delta_seconds(
                    event,
                    previous_damage,
                    scale=scale,
                )
                recipient_delta = self._event_delta_seconds(
                    event,
                    previous_recipient_damage,
                    scale=scale,
                )

                relation = self._source_target_relation(
                    event.source_id,
                    event.target_id,
                )
                observations.append(
                    RotationHealerMinorLifestealHealObservation(
                        report_code=event.report_code,
                        fight_id=event.fight_id,
                        event_index=int(event.event_index),
                        timestamp_seconds=round(float(event.timestamp) * scale, 6),
                        ability_game_id=event.ability_game_id,
                        ability_name=event.ability_name,
                        source_id=event.source_id,
                        target_id=event.target_id,
                        amount=event.amount,
                        overheal=event.overheal,
                        source_target_relation=relation,
                        previous_same_source_damage_event_index=(
                            int(previous_damage.event_index)
                            if previous_damage is not None
                            else None
                        ),
                        previous_same_source_damage_target_id=(
                            previous_damage.target_id
                            if previous_damage is not None
                            else None
                        ),
                        previous_same_source_damage_delta_seconds=delta,
                        previous_recipient_damage_event_index=(
                            int(previous_recipient_damage.event_index)
                            if previous_recipient_damage is not None
                            else None
                        ),
                        previous_recipient_damage_target_id=(
                            previous_recipient_damage.target_id
                            if previous_recipient_damage is not None
                            else None
                        ),
                        previous_recipient_damage_delta_seconds=recipient_delta,
                    )
                )

        if not observations:
            unresolved.append(
                "no Minor Lifesteal heal events matched readable ability names or caller-supplied observational aliases"
            )
        for item in observations:
            if item.source_id is None or item.target_id is None:
                unresolved.append(
                    f"{item.report_code} fight {item.fight_id} event {item.event_index}: "
                    "source/target ownership is unavailable"
                )
            if (
                item.previous_same_source_damage_event_index is None
                and item.previous_recipient_damage_event_index is None
            ):
                unresolved.append(
                    f"{item.report_code} fight {item.fight_id} event {item.event_index}: "
                    "no preceding damage event was observed for either the logged "
                    "heal source or the heal recipient"
                )

        observed_aliases = aliases | {
            int(item.ability_game_id)
            for item in observations
            if item.ability_game_id is not None
        }
        return RotationHealerMinorLifestealEsoLogsEvidenceReport(
            source_path=str(path),
            timestamp_unit=unit,
            observations=tuple(observations),
            cadence_streams=self._cadence_streams(observations),
            observed_heal_ability_aliases=tuple(sorted(observed_aliases)),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def _candidate_heal_events(
        cls,
        connection: sqlite3.Connection,
        *,
        interpreter: EsoLogsEventInterpreter,
        aliases: set[int],
        report_code: str | None,
        fight_id: int | None,
    ) -> tuple[SemanticCombatEvent, ...]:
        query = (
            f"SELECT {cls._EVENT_COLUMNS} FROM log_event "
            "WHERE lower(event_type) IN ('heal', 'hot')"
        )
        params: list[object] = []
        if report_code is not None:
            query += " AND report_code = ?"
            params.append(str(report_code))
        if fight_id is not None:
            query += " AND fight_id = ?"
            params.append(int(fight_id))
        if aliases:
            placeholders = ",".join("?" for _ in aliases)
            query += f" AND ability_game_id IN ({placeholders})"
            params.extend(sorted(aliases))
        query += " ORDER BY report_code, fight_id, timestamp, event_index"
        return tuple(
            interpreter.interpret_row(row)
            for row in connection.execute(query, params)
        )

    @classmethod
    def _previous_damage_by_actor(
        cls,
        connection: sqlite3.Connection,
        *,
        interpreter: EsoLogsEventInterpreter,
        event: SemanticCombatEvent,
        actor_id: int | None,
    ) -> SemanticCombatEvent | None:
        if actor_id is None:
            return None
        row = connection.execute(
            f"""
            SELECT {cls._EVENT_COLUMNS}
            FROM log_event
            WHERE report_code = ?
              AND fight_id = ?
              AND source_id = ?
              AND lower(event_type) = 'damage'
              AND (
                    timestamp < ?
                    OR (timestamp = ? AND event_index < ?)
              )
            ORDER BY timestamp DESC, event_index DESC
            LIMIT 1
            """,
            (
                event.report_code,
                int(event.fight_id),
                int(actor_id),
                float(event.timestamp),
                float(event.timestamp),
                int(event.event_index),
            ),
        ).fetchone()
        return interpreter.interpret_row(row) if row is not None else None

    @staticmethod
    def _event_delta_seconds(
        event: SemanticCombatEvent,
        previous_damage: SemanticCombatEvent | None,
        *,
        scale: float,
    ) -> float | None:
        if previous_damage is None:
            return None
        delta = round(
            (float(event.timestamp) - float(previous_damage.timestamp)) * scale,
            6,
        )
        if delta < 0 or not math.isfinite(delta):
            return None
        return delta

    @staticmethod
    def _fight_keys(
        connection: sqlite3.Connection,
        *,
        report_code: str | None,
        fight_id: int | None,
    ) -> tuple[tuple[str, int], ...]:
        query = "SELECT DISTINCT report_code, fight_id FROM log_event WHERE 1 = 1"
        params: list[object] = []
        if report_code is not None:
            query += " AND report_code = ?"
            params.append(str(report_code))
        if fight_id is not None:
            query += " AND fight_id = ?"
            params.append(int(fight_id))
        query += " ORDER BY report_code, fight_id"
        return tuple(
            (str(row["report_code"]), int(row["fight_id"]))
            for row in connection.execute(query, params)
        )

    @staticmethod
    def _is_minor_lifesteal_heal(event, *, aliases: set[int]) -> bool:
        if event.ability_game_id is not None and int(event.ability_game_id) in aliases:
            return True
        normalized = (
            str(event.ability_name or "")
            .strip()
            .casefold()
            .replace("_", " ")
            .replace("-", " ")
        )
        return " ".join(normalized.split()) == "minor lifesteal"

    @staticmethod
    def _source_target_relation(
        source_id: int | None,
        target_id: int | None,
    ) -> str:
        if source_id is None or target_id is None:
            return "unresolved"
        return "self" if int(source_id) == int(target_id) else "other"

    @staticmethod
    def _cadence_streams(
        observations: list[RotationHealerMinorLifestealHealObservation],
    ) -> tuple[RotationHealerMinorLifestealCadenceStream, ...]:
        grouped: dict[
            tuple[str, int, int | None, int | None, str],
            list[float],
        ] = {}
        for item in observations:
            key = (
                item.report_code,
                item.fight_id,
                item.source_id,
                item.target_id,
                item.source_target_relation,
            )
            grouped.setdefault(key, []).append(item.timestamp_seconds)

        streams: list[RotationHealerMinorLifestealCadenceStream] = []
        for key, timestamps in grouped.items():
            ordered = sorted(float(value) for value in timestamps)
            intervals = tuple(
                round(current - previous, 6)
                for previous, current in zip(ordered, ordered[1:])
            )
            streams.append(
                RotationHealerMinorLifestealCadenceStream(
                    report_code=key[0],
                    fight_id=key[1],
                    source_id=key[2],
                    target_id=key[3],
                    source_target_relation=key[4],
                    heal_event_count=len(ordered),
                    observed_intervals_seconds=intervals,
                )
            )
        streams.sort(
            key=lambda item: (
                item.report_code,
                item.fight_id,
                item.source_id if item.source_id is not None else -1,
                item.target_id if item.target_id is not None else -1,
            )
        )
        return tuple(streams)


__all__ = [
    "RotationHealerMinorLifestealCadenceStream",
    "RotationHealerMinorLifestealEsoLogsEvidenceReport",
    "RotationHealerMinorLifestealEsoLogsEvidenceService",
    "RotationHealerMinorLifestealHealObservation",
]
