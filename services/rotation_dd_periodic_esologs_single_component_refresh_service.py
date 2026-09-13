from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from statistics import median

from minmax.skill_coefficient_repository import ability_entity_id
from services.rotation_dd_periodic_esologs_refresh_boundary_evidence_service import (
    RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceService,
)


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsSingleComponentRefreshObservation:
    report_code: str
    fight_id: int
    source_id: int
    old_cast_track_id: int
    new_cast_track_id: int
    new_boundary_timestamp_ms: float
    new_boundary_event_index: int
    old_periodic_before_boundary: int
    old_periodic_at_boundary: int
    old_periodic_after_boundary: int
    exact_boundary_old_tick_before_new: int
    exact_boundary_old_tick_after_new: int
    exact_boundary_old_tick_event_indices: tuple[int, ...]
    last_old_periodic_offset_seconds: float | None


@dataclass(frozen=True)
class RotationDDPeriodicEsoLogsSingleComponentRefreshReport:
    skill_entity_id: str
    periodic_ability_id: int
    boundary_tolerance_ms: float
    observations: tuple[RotationDDPeriodicEsoLogsSingleComponentRefreshObservation, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def old_tick_at_boundary_count(self) -> int:
        return sum(item.old_periodic_at_boundary for item in self.observations)

    @property
    def old_tick_after_boundary_count(self) -> int:
        return sum(item.old_periodic_after_boundary for item in self.observations)

    @property
    def exact_boundary_old_tick_before_new_count(self) -> int:
        return sum(item.exact_boundary_old_tick_before_new for item in self.observations)

    @property
    def exact_boundary_old_tick_after_new_count(self) -> int:
        return sum(item.exact_boundary_old_tick_after_new for item in self.observations)

    @property
    def median_last_old_periodic_offset_seconds(self) -> float | None:
        values = tuple(
            item.last_old_periodic_offset_seconds
            for item in self.observations
            if item.last_old_periodic_offset_seconds is not None
        )
        return float(median(values)) if values else None


class RotationDDPeriodicEsoLogsSingleComponentRefreshService(
    RotationDDPeriodicEsoLogsRefreshBoundaryEvidenceService
):
    """Observe refresh behavior when the periodic stream is the only logged component.

    The first periodic event on the new cast track is the observational boundary. This
    service never treats that boundary as a canonical activation anchor and never promotes
    refresh semantics automatically. The ESO Logs database is opened read-only by the
    shared evidence base class.
    """

    def inspect(
        self,
        skill_entity_id: str,
        *,
        periodic_ability_id: int,
        active_window_seconds: float,
        boundary_tolerance_ms: float = 50.0,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationDDPeriodicEsoLogsSingleComponentRefreshReport:
        identity = ability_entity_id(skill_entity_id)
        tolerance = float(boundary_tolerance_ms)
        unresolved: list[str] = []

        if not identity:
            return self._single_report(
                "", periodic_ability_id, tolerance,
                unresolved=("canonical skill identity is required",),
            )
        if not self.canonical_database_path.is_file():
            raise FileNotFoundError(self.canonical_database_path)
        if not self.logs_database_path.is_file():
            raise FileNotFoundError(self.logs_database_path)
        if int(periodic_ability_id) <= 0:
            return self._single_report(
                identity, periodic_ability_id, tolerance,
                unresolved=("positive observational periodic ability ID is required",),
            )
        if float(active_window_seconds) <= 0:
            return self._single_report(
                identity, periodic_ability_id, tolerance,
                unresolved=("active_window_seconds must be positive",),
            )
        if tolerance < 0:
            return self._single_report(
                identity, periodic_ability_id, tolerance,
                unresolved=("boundary_tolerance_ms must be non-negative",),
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
            unresolved.extend(str(item).strip() for item in resolution.unresolved if str(item).strip())

        observations: list[RotationDDPeriodicEsoLogsSingleComponentRefreshObservation] = []
        with self._open_logs() as db:
            schema_error = self._schema_error(db)
            if schema_error:
                return self._single_report(
                    identity,
                    periodic_ability_id,
                    tolerance,
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
                return self._single_report(
                    identity,
                    periodic_ability_id,
                    tolerance,
                    unresolved=tuple(dict.fromkeys(unresolved)),
                )

            anchor_type = next(
                kind for kind in self._CAST_TYPES if any(self._event_type(row) == kind for row in casts)
            )
            grouped: dict[tuple[str, int, int], list[sqlite3.Row]] = {}
            for row in casts:
                if self._event_type(row) != anchor_type or row["source_id"] is None:
                    continue
                key = (str(row["report_code"]), int(row["fight_id"]), int(row["source_id"]))
                grouped.setdefault(key, []).append(row)

            for (group_report, group_fight, group_source), group_casts in grouped.items():
                group_casts.sort(key=lambda row: (float(row["timestamp"]), int(row["event_index"])))
                periodic_rows = self._single_effect_rows(
                    db,
                    report_code=group_report,
                    fight_id=group_fight,
                    source_id=group_source,
                    periodic_ability_id=int(periodic_ability_id),
                )
                periodic_by_track = self._events_by_track(periodic_rows, int(periodic_ability_id))

                for old_cast, new_cast in zip(group_casts, group_casts[1:]):
                    old_track = self._track(old_cast)
                    new_track = self._track(new_cast)
                    if old_track is None or new_track is None:
                        continue
                    old_stream = periodic_by_track.get(old_track, ())
                    new_stream = periodic_by_track.get(new_track, ())
                    if not old_stream or not new_stream:
                        continue

                    first_old = old_stream[0]
                    first_new = new_stream[0]
                    first_old_time = float(first_old["timestamp"])
                    boundary_time = float(first_new["timestamp"])
                    boundary_index = int(first_new["event_index"])
                    if boundary_time <= first_old_time:
                        continue
                    if boundary_time - first_old_time > float(active_window_seconds) * 1000.0:
                        continue

                    relevant_old = tuple(
                        row
                        for row in old_stream
                        if first_old_time <= float(row["timestamp"]) <= boundary_time + max(tolerance, 250.0)
                    )
                    before = tuple(
                        row for row in relevant_old
                        if float(row["timestamp"]) < boundary_time - tolerance
                    )
                    at_boundary = tuple(
                        row for row in relevant_old
                        if abs(float(row["timestamp"]) - boundary_time) <= tolerance
                    )
                    after = tuple(
                        row for row in relevant_old
                        if float(row["timestamp"]) > boundary_time + tolerance
                    )
                    exact = tuple(
                        row for row in relevant_old if float(row["timestamp"]) == boundary_time
                    )
                    exact_before = tuple(
                        row for row in exact if int(row["event_index"]) < boundary_index
                    )
                    exact_after = tuple(
                        row for row in exact if int(row["event_index"]) > boundary_index
                    )
                    last_old = max(
                        (float(row["timestamp"]) for row in relevant_old),
                        default=None,
                    )
                    observations.append(
                        RotationDDPeriodicEsoLogsSingleComponentRefreshObservation(
                            report_code=group_report,
                            fight_id=group_fight,
                            source_id=group_source,
                            old_cast_track_id=old_track,
                            new_cast_track_id=new_track,
                            new_boundary_timestamp_ms=boundary_time,
                            new_boundary_event_index=boundary_index,
                            old_periodic_before_boundary=len(before),
                            old_periodic_at_boundary=len(at_boundary),
                            old_periodic_after_boundary=len(after),
                            exact_boundary_old_tick_before_new=len(exact_before),
                            exact_boundary_old_tick_after_new=len(exact_after),
                            exact_boundary_old_tick_event_indices=tuple(int(row["event_index"]) for row in exact),
                            last_old_periodic_offset_seconds=(
                                None if last_old is None else (last_old - boundary_time) / 1000.0
                            ),
                        )
                    )

        if not observations:
            unresolved.append(
                f"{identity}: no consecutive cast pairs with cast-track-linked periodic streams were observed"
            )
        return self._single_report(
            identity,
            periodic_ability_id,
            tolerance,
            observations=tuple(observations),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _single_effect_rows(
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
                "ability_game_id,cast_track_id,raw_json FROM log_event "
                "WHERE report_code=? AND fight_id=? AND source_id=? AND ability_game_id=? "
                "ORDER BY timestamp,event_index",
                (report_code, int(fight_id), int(source_id), int(periodic_ability_id)),
            ).fetchall()
        )

    @staticmethod
    def _single_report(
        skill_entity_id: str,
        periodic_ability_id: int,
        boundary_tolerance_ms: float,
        *,
        observations: tuple[RotationDDPeriodicEsoLogsSingleComponentRefreshObservation, ...] = (),
        unresolved: tuple[str, ...] = (),
    ) -> RotationDDPeriodicEsoLogsSingleComponentRefreshReport:
        return RotationDDPeriodicEsoLogsSingleComponentRefreshReport(
            skill_entity_id=skill_entity_id,
            periodic_ability_id=int(periodic_ability_id),
            boundary_tolerance_ms=float(boundary_tolerance_ms),
            observations=observations,
            unresolved=unresolved,
        )
