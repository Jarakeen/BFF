from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsMagnitudeSequence:
    report_code: str
    fight_id: int
    source_id: int
    target_id: int
    cast_track_id: int
    hit_type: int | None
    amounts: tuple[float, ...]
    offsets_seconds: tuple[float, ...]

    @property
    def distinct_amount_count(self) -> int:
        return len({float(value) for value in self.amounts})

    @property
    def amount_is_constant(self) -> bool:
        return bool(self.amounts) and self.distinct_amount_count == 1


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsMagnitudeObservationReport:
    skill_entity_id: str
    periodic_ability_id: int
    cast_anchor_count: int
    sequences: tuple[RotationDDPeriodicEsoLogsMagnitudeSequence, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def constant_sequence_count(self) -> int:
        return sum(1 for item in self.sequences if item.amount_is_constant)

    @property
    def varying_sequence_count(self) -> int:
        return sum(1 for item in self.sequences if not item.amount_is_constant)


class RotationDDPeriodicEsoLogsMagnitudeObservationService:
    """Observe same-cast periodic damage amounts without inferring magnitude policy.

    Canonical lower-snake identity selects cast anchors. Numeric periodic ability IDs
    remain observational ESO Logs handles only. Sequences are separated by cast track,
    target, and hit type so obvious target/crit mixing does not masquerade as runtime
    magnitude behavior. Amount variation remains candidate evidence only: buffs,
    debuffs, mitigation, and other combat-state changes can still alter observed values.
    """

    _CAST_TYPES = ("cast", "completecast", "begincast")

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
        minimum_occurrences: int = 2,
    ) -> RotationDDPeriodicEsoLogsMagnitudeObservationReport:
        identity = ability_entity_id(skill_entity_id)
        unresolved: list[str] = []
        if not identity:
            return self._report(
                "",
                periodic_ability_id,
                unresolved=("canonical skill identity is required",),
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
        minimum = int(minimum_occurrences)
        if minimum < 2:
            return self._report(
                identity,
                periodic_ability_id,
                unresolved=("minimum_occurrences must be at least 2",),
            )

        resolution = self.coefficients.resolve_entity_id(identity)
        aliases: set[int] = set()
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
                kind
                for kind in self._CAST_TYPES
                if any(self._event_type(row) == kind for row in casts)
            )
            anchors = tuple(row for row in casts if self._event_type(row) == anchor_type)
            cast_times_by_key: dict[tuple[str, int, int, int], float] = {}
            groups: set[tuple[str, int, int]] = set()
            for row in anchors:
                track = self._track(row)
                if row["source_id"] is None or track is None:
                    continue
                report = str(row["report_code"])
                fight = int(row["fight_id"])
                source = int(row["source_id"])
                key = (report, fight, source, track)
                cast_times_by_key.setdefault(key, float(row["timestamp"]))
                groups.add((report, fight, source))

            grouped_rows: dict[
                tuple[str, int, int, int, int, int | None],
                list[sqlite3.Row],
            ] = {}
            for group_report, group_fight, group_source in groups:
                rows = self._periodic_rows(
                    db,
                    report_code=group_report,
                    fight_id=group_fight,
                    source_id=group_source,
                    periodic_ability_id=int(periodic_ability_id),
                )
                for row in rows:
                    track = self._track(row)
                    if track is None or row["target_id"] is None or row["amount"] is None:
                        continue
                    cast_key = (group_report, group_fight, group_source, track)
                    if cast_key not in cast_times_by_key:
                        continue
                    key = (
                        group_report,
                        group_fight,
                        group_source,
                        track,
                        int(row["target_id"]),
                        None if row["hit_type"] is None else int(row["hit_type"]),
                    )
                    grouped_rows.setdefault(key, []).append(row)

        sequences: list[RotationDDPeriodicEsoLogsMagnitudeSequence] = []
        for (group_report, group_fight, group_source, track, target, hit_type), rows in grouped_rows.items():
            ordered = sorted(
                rows,
                key=lambda row: (float(row["timestamp"]), int(row["event_index"])),
            )
            if len(ordered) < minimum:
                continue
            cast_time = cast_times_by_key[(group_report, group_fight, group_source, track)]
            sequences.append(
                RotationDDPeriodicEsoLogsMagnitudeSequence(
                    report_code=group_report,
                    fight_id=group_fight,
                    source_id=group_source,
                    target_id=target,
                    cast_track_id=track,
                    hit_type=hit_type,
                    amounts=tuple(float(row["amount"]) for row in ordered),
                    offsets_seconds=tuple(
                        (float(row["timestamp"]) - cast_time) / 1000.0
                        for row in ordered
                    ),
                )
            )

        if not sequences:
            unresolved.append(
                f"{identity}: no same-cast periodic amount sequences with at least {minimum} occurrences were observed"
            )
        return self._report(
            identity,
            periodic_ability_id,
            cast_anchor_count=len(cast_times_by_key),
            sequences=tuple(sequences),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _numeric_aliases(self, skill_id: int, morph: int, base_ability_id: int) -> tuple[int, ...]:
        uri = f"file:{self.canonical_database_path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only = ON")
            aliases = {int(base_ability_id)} if int(base_ability_id) > 0 else set()
            table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='skill_rank'"
            ).fetchone()
            if table is not None:
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
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='log_event'"
        ).fetchone()
        if row is None:
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
            "raw_json",
        }
        columns = {
            str(row[1])
            for row in db.execute("PRAGMA table_info(log_event)").fetchall()
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
                "AND ability_game_id=? AND amount IS NOT NULL "
                "ORDER BY timestamp,event_index",
                (report_code, int(fight_id), int(source_id), int(periodic_ability_id)),
            ).fetchall()
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
    def _track(row: sqlite3.Row) -> int | None:
        return int(row["cast_track_id"]) if row["cast_track_id"] is not None else None

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
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _report(
        skill_entity_id: str,
        periodic_ability_id: int,
        *,
        cast_anchor_count: int = 0,
        sequences: tuple[RotationDDPeriodicEsoLogsMagnitudeSequence, ...] = (),
        unresolved: tuple[str, ...] = (),
    ) -> RotationDDPeriodicEsoLogsMagnitudeObservationReport:
        return RotationDDPeriodicEsoLogsMagnitudeObservationReport(
            skill_entity_id=skill_entity_id,
            periodic_ability_id=int(periodic_ability_id),
            cast_anchor_count=int(cast_anchor_count),
            sequences=sequences,
            unresolved=unresolved,
        )


__all__ = [
    "RotationDDPeriodicEsoLogsMagnitudeObservationReport",
    "RotationDDPeriodicEsoLogsMagnitudeObservationService",
    "RotationDDPeriodicEsoLogsMagnitudeSequence",
]
