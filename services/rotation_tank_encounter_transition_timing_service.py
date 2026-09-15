from __future__ import annotations

"""Project reviewed encounter transition delays onto canonical Tank timing.

Health-threshold projection owns when a boss reaches a reviewed health boundary during
active damage. Reviewed transition evidence may add empirical non-damage time after that
boundary. This service keeps those concerns separate and shifts every later boundary and
encounter end by the cumulative reviewed transition delays.

The reviewed delay median is a planning estimate, not a claim that the encounter has a
fixed transition duration. The observed range, sample count, and source remain attached
as evidence so callers can expose that uncertainty instead of hiding it.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path

from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
)
from services.paths import DATA
from services.rotation_tank_encounter_horizon_service import RotationTankEncounterHorizon


_DEFAULT_PATH = DATA / "encounter_transition_timing" / "reviewed.json"


@dataclass(frozen=True)
class ReviewedEncounterTransitionDelay:
    encounter_id: str
    threshold_fraction: float
    median_delay_seconds: float
    observed_min_delay_seconds: float
    observed_max_delay_seconds: float
    sample_count: int
    source: str

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip()
        source = str(self.source or "").strip()
        if not encounter_id:
            raise ValueError("reviewed encounter transition timing requires encounter_id")
        if not source:
            raise ValueError("reviewed encounter transition timing requires source")
        fraction = float(self.threshold_fraction)
        if not 0.0 < fraction < 1.0:
            raise ValueError("reviewed encounter transition threshold_fraction must be between 0 and 1")
        median = float(self.median_delay_seconds)
        minimum = float(self.observed_min_delay_seconds)
        maximum = float(self.observed_max_delay_seconds)
        if any(not math.isfinite(value) or value < 0 for value in (median, minimum, maximum)):
            raise ValueError("reviewed encounter transition delays must be finite and non-negative")
        if not minimum <= median <= maximum:
            raise ValueError("reviewed encounter transition median must fall inside observed range")
        count = int(self.sample_count)
        if count <= 0:
            raise ValueError("reviewed encounter transition sample_count must be positive")
        object.__setattr__(self, "encounter_id", encounter_id)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "threshold_fraction", fraction)
        object.__setattr__(self, "median_delay_seconds", median)
        object.__setattr__(self, "observed_min_delay_seconds", minimum)
        object.__setattr__(self, "observed_max_delay_seconds", maximum)
        object.__setattr__(self, "sample_count", count)


@dataclass(frozen=True)
class RotationTankEncounterTransitionBoundary:
    threshold_fraction: float
    crossing_time_seconds: float
    resume_time_seconds: float
    reviewed_delay_seconds: float
    observed_min_delay_seconds: float
    observed_max_delay_seconds: float
    sample_count: int
    source: str


@dataclass(frozen=True)
class RotationTankEncounterTransitionTiming:
    encounter_id: str
    boundaries: tuple[RotationTankEncounterTransitionBoundary, ...]
    adjusted_end_seconds: float | None
    resolved: bool
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def crossing_time_for(self, threshold_fraction: float) -> float | None:
        fraction = float(threshold_fraction)
        for boundary in self.boundaries:
            if math.isclose(boundary.threshold_fraction, fraction, rel_tol=0.0, abs_tol=1e-9):
                return boundary.crossing_time_seconds
        return None

    def resume_time_for(self, threshold_fraction: float) -> float | None:
        fraction = float(threshold_fraction)
        for boundary in self.boundaries:
            if math.isclose(boundary.threshold_fraction, fraction, rel_tol=0.0, abs_tol=1e-9):
                return boundary.resume_time_seconds
        return None


class RotationTankEncounterTransitionTimingService:
    def __init__(self, path: Path | str = _DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._rows = self._load(self.path)

    @staticmethod
    def _load(path: Path) -> tuple[ReviewedEncounterTransitionDelay, ...]:
        if not path.exists():
            return ()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) != 1:
            raise ValueError("unsupported encounter transition timing schema_version")
        raw_rows = payload.get("transitions")
        if not isinstance(raw_rows, list):
            raise ValueError("encounter transition timing transitions must be a list")
        rows = tuple(
            ReviewedEncounterTransitionDelay(
                encounter_id=str(raw.get("encounter_id") or ""),
                threshold_fraction=float(raw.get("threshold_fraction")),
                median_delay_seconds=float(raw.get("median_delay_seconds")),
                observed_min_delay_seconds=float(raw.get("observed_min_delay_seconds")),
                observed_max_delay_seconds=float(raw.get("observed_max_delay_seconds")),
                sample_count=int(raw.get("sample_count")),
                source=str(raw.get("source") or ""),
            )
            for raw in raw_rows
        )
        identities = [
            (row.encounter_id.casefold(), round(row.threshold_fraction, 9))
            for row in rows
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("encounter transition timing cannot duplicate encounter/threshold identity")
        return rows

    def reviewed_for(self, encounter_id: str) -> tuple[ReviewedEncounterTransitionDelay, ...]:
        encounter_key = str(encounter_id or "").strip().casefold()
        if not encounter_key:
            raise ValueError("encounter transition timing lookup requires encounter_id")
        return tuple(
            sorted(
                (row for row in self._rows if row.encounter_id.casefold() == encounter_key),
                key=lambda row: row.threshold_fraction,
                reverse=True,
            )
        )

    @staticmethod
    def _base_threshold_time(
        projection: EncounterHealthThresholdProjection,
        fraction: float,
    ) -> tuple[float | None, tuple[str, ...]]:
        matches = tuple(
            point
            for point in projection.points
            if math.isclose(
                float(point.threshold_fraction),
                float(fraction),
                rel_tol=0.0,
                abs_tol=1e-9,
            )
        )
        if not matches:
            return None, (f"no canonical {fraction * 100:g}% health-threshold clock point is available",)
        unresolved = tuple(point for point in matches if not point.resolved or point.time_seconds is None)
        if unresolved:
            reasons = "; ".join(dict.fromkeys(str(point.reason or "unresolved threshold") for point in unresolved))
            return None, (f"canonical {fraction * 100:g}% health-threshold clock point is unresolved: {reasons}",)
        value = float(matches[0].time_seconds)
        if any(
            not math.isclose(float(point.time_seconds), value, rel_tol=0.0, abs_tol=1e-9)
            for point in matches[1:]
        ):
            return None, (f"corroborating {fraction * 100:g}% health-threshold facts disagree on projected clock time",)
        return value, ()

    def project(
        self,
        *,
        encounter_id: str,
        health_threshold_projection: EncounterHealthThresholdProjection | None,
        horizon: RotationTankEncounterHorizon,
    ) -> RotationTankEncounterTransitionTiming:
        resolved_encounter = str(encounter_id or "").strip()
        if not resolved_encounter:
            raise ValueError("Tank encounter transition timing requires encounter_id")
        if horizon.encounter_id != resolved_encounter:
            raise ValueError("Tank encounter horizon does not match transition timing encounter")

        reviewed = self.reviewed_for(resolved_encounter)
        if not reviewed:
            return RotationTankEncounterTransitionTiming(
                encounter_id=resolved_encounter,
                boundaries=(),
                adjusted_end_seconds=(
                    float(horizon.end_seconds)
                    if horizon.resolved and horizon.end_seconds is not None
                    else None
                ),
                resolved=bool(horizon.resolved and horizon.end_seconds is not None),
                evidence=tuple(horizon.evidence),
                unresolved=tuple(horizon.unresolved),
            )

        projection = health_threshold_projection
        if projection is None:
            return RotationTankEncounterTransitionTiming(
                encounter_id=resolved_encounter,
                boundaries=(),
                adjusted_end_seconds=None,
                resolved=False,
                unresolved=("canonical health-threshold projection is unavailable for reviewed encounter transitions",),
            )
        if projection.encounter_id != resolved_encounter:
            raise ValueError("Tank health-threshold projection does not match transition timing encounter")
        if not horizon.resolved or horizon.end_seconds is None:
            return RotationTankEncounterTransitionTiming(
                encounter_id=resolved_encounter,
                boundaries=(),
                adjusted_end_seconds=None,
                resolved=False,
                unresolved=tuple(horizon.unresolved) or ("Tank encounter horizon is unresolved",),
            )

        cumulative_delay = 0.0
        boundaries: list[RotationTankEncounterTransitionBoundary] = []
        evidence: list[str] = list(horizon.evidence)
        for row in reviewed:
            base_time, unresolved = self._base_threshold_time(projection, row.threshold_fraction)
            if unresolved or base_time is None:
                return RotationTankEncounterTransitionTiming(
                    encounter_id=resolved_encounter,
                    boundaries=tuple(boundaries),
                    adjusted_end_seconds=None,
                    resolved=False,
                    evidence=tuple(evidence),
                    unresolved=unresolved,
                )
            crossing = float(base_time) + cumulative_delay
            resume = crossing + row.median_delay_seconds
            boundaries.append(
                RotationTankEncounterTransitionBoundary(
                    threshold_fraction=row.threshold_fraction,
                    crossing_time_seconds=crossing,
                    resume_time_seconds=resume,
                    reviewed_delay_seconds=row.median_delay_seconds,
                    observed_min_delay_seconds=row.observed_min_delay_seconds,
                    observed_max_delay_seconds=row.observed_max_delay_seconds,
                    sample_count=row.sample_count,
                    source=row.source,
                )
            )
            evidence.extend(
                (
                    f"transition_threshold={row.threshold_fraction * 100:g}% crossing={crossing:g} resume={resume:g}",
                    f"transition_delay_median={row.median_delay_seconds:g}s range={row.observed_min_delay_seconds:g}-{row.observed_max_delay_seconds:g}s samples={row.sample_count}",
                    row.source,
                )
            )
            cumulative_delay += row.median_delay_seconds

        adjusted_end = float(horizon.end_seconds) + cumulative_delay
        evidence.append(f"transition_adjusted_encounter_end={adjusted_end:g}")
        return RotationTankEncounterTransitionTiming(
            encounter_id=resolved_encounter,
            boundaries=tuple(boundaries),
            adjusted_end_seconds=adjusted_end,
            resolved=True,
            evidence=tuple(evidence),
        )


__all__ = [
    "ReviewedEncounterTransitionDelay",
    "RotationTankEncounterTransitionBoundary",
    "RotationTankEncounterTransitionTiming",
    "RotationTankEncounterTransitionTimingService",
]
