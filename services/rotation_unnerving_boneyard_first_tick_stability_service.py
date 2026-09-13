from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from statistics import median

from services.rotation_unnerving_boneyard_refresh_boundary_evidence_service import (
    RotationUnnervingBoneyardRefreshBoundaryEvidenceService,
)


@dataclass(frozen=True)
class RotationUnnervingBoneyardFirstTickGroupSummary:
    report_code: str
    source_id: int
    sample_count: int
    median_offset_seconds: float
    minimum_offset_seconds: float
    maximum_offset_seconds: float


@dataclass(frozen=True)
class RotationUnnervingBoneyardFirstTickStabilityReport:
    sample_count: int
    median_offset_seconds: float | None
    p10_offset_seconds: float | None
    p90_offset_seconds: float | None
    minimum_offset_seconds: float | None
    maximum_offset_seconds: float | None
    groups: tuple[RotationUnnervingBoneyardFirstTickGroupSummary, ...]
    unresolved: tuple[str, ...] = ()


class RotationUnnervingBoneyardFirstTickStabilityService(
    RotationUnnervingBoneyardRefreshBoundaryEvidenceService
):
    """Measure cast-to-first-117809 stability without promoting runtime timing.

    Research-only. Exact first-tick semantics remain unresolved unless the observed
    offset proves stable enough to justify separate review.
    """

    def inspect(self, *, candidate_ability_id: int = 117809) -> RotationUnnervingBoneyardFirstTickStabilityReport:
        if not self.logs_database_path.is_file():
            return self._report(unresolved=(f"ESO Logs database not found: {self.logs_database_path}",))

        aliases = self._cast_aliases()
        samples: list[float] = []
        grouped_samples: dict[tuple[str, int], list[float]] = {}

        with self._open_logs() as db:
            error = self._schema_error(db)
            if error:
                return self._report(unresolved=(error,))
            rows = db.execute(
                "SELECT report_code,fight_id,event_index,timestamp,event_type,source_id,"
                "ability_game_id,cast_track_id,raw_json FROM log_event "
                "ORDER BY report_code,fight_id,source_id,timestamp,event_index"
            ).fetchall()

        casts: dict[tuple[str, int, int, int], sqlite3.Row] = {}
        first_damage: dict[tuple[str, int, int, int], sqlite3.Row] = {}
        for row in rows:
            if row["source_id"] is None or row["cast_track_id"] is None:
                continue
            key = (
                str(row["report_code"]),
                int(row["fight_id"]),
                int(row["source_id"]),
                int(row["cast_track_id"]),
            )
            event_type = str(row["event_type"] or "").casefold()
            if event_type in self._CAST_TYPES and self._matches_boneyard_cast(row, aliases=aliases):
                casts.setdefault(key, row)
            if event_type == "damage" and row["ability_game_id"] == int(candidate_ability_id):
                current = first_damage.get(key)
                if current is None or (
                    float(row["timestamp"]), int(row["event_index"])
                ) < (
                    float(current["timestamp"]), int(current["event_index"])
                ):
                    first_damage[key] = row

        for key, cast in casts.items():
            damage = first_damage.get(key)
            if damage is None:
                continue
            offset = (float(damage["timestamp"]) - float(cast["timestamp"])) / 1000.0
            if offset < 0:
                continue
            samples.append(offset)
            grouped_samples.setdefault((key[0], key[2]), []).append(offset)

        if not samples:
            return self._report(unresolved=("no cast-track-linked first 117809 observations were found",))

        groups = tuple(
            RotationUnnervingBoneyardFirstTickGroupSummary(
                report_code=report,
                source_id=source,
                sample_count=len(values),
                median_offset_seconds=float(median(values)),
                minimum_offset_seconds=min(values),
                maximum_offset_seconds=max(values),
            )
            for (report, source), values in sorted(grouped_samples.items())
        )
        ordered = sorted(samples)
        return RotationUnnervingBoneyardFirstTickStabilityReport(
            sample_count=len(ordered),
            median_offset_seconds=float(median(ordered)),
            p10_offset_seconds=self._percentile(ordered, 0.10),
            p90_offset_seconds=self._percentile(ordered, 0.90),
            minimum_offset_seconds=ordered[0],
            maximum_offset_seconds=ordered[-1],
            groups=groups,
            unresolved=(),
        )

    @staticmethod
    def _percentile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        if len(values) == 1:
            return float(values[0])
        position = (len(values) - 1) * float(fraction)
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        weight = position - lower
        return float(values[lower] * (1.0 - weight) + values[upper] * weight)

    @staticmethod
    def _report(*, unresolved: tuple[str, ...]) -> RotationUnnervingBoneyardFirstTickStabilityReport:
        return RotationUnnervingBoneyardFirstTickStabilityReport(
            0, None, None, None, None, None, (), unresolved
        )


__all__ = [
    "RotationUnnervingBoneyardFirstTickGroupSummary",
    "RotationUnnervingBoneyardFirstTickStabilityReport",
    "RotationUnnervingBoneyardFirstTickStabilityService",
]
