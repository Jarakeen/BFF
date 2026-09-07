from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RaidDamageSegment:
    """Caller-supplied raid DPS over one bounded wall-clock interval.

    This model deliberately does not derive raid DPS from single-event potency,
    parse metadata, or build-candidate scores. The caller must provide a verified
    or explicitly assumed damage rate for each segment.
    """

    start_seconds: float
    end_seconds: float | None
    damage_per_second: float
    source: str = "caller supplied"

    def __post_init__(self) -> None:
        start = float(self.start_seconds)
        if not math.isfinite(start) or start < 0:
            raise ValueError("raid damage segment start must be finite and non-negative")
        object.__setattr__(self, "start_seconds", start)

        if self.end_seconds is not None:
            end = float(self.end_seconds)
            if not math.isfinite(end) or end <= start:
                raise ValueError("raid damage segment end must be finite and after start")
            object.__setattr__(self, "end_seconds", end)

        dps = float(self.damage_per_second)
        if not math.isfinite(dps) or dps <= 0:
            raise ValueError("raid damage segment DPS must be finite and positive")
        object.__setattr__(self, "damage_per_second", dps)

        source = str(self.source or "").strip()
        object.__setattr__(self, "source", source or "caller supplied")


@dataclass(frozen=True)
class HealthThresholdProjection:
    threshold_fraction: float
    health_at_threshold: float
    damage_required: float
    time_seconds: float | None
    resolved: bool
    reason: str


@dataclass(frozen=True)
class FightDamageTrajectoryProjection:
    maximum_health: float
    segments: tuple[RaidDamageSegment, ...]
    thresholds: tuple[HealthThresholdProjection, ...]


def project_health_threshold_times(
    *,
    maximum_health: float,
    thresholds: tuple[float, ...],
    segments: tuple[RaidDamageSegment, ...],
) -> FightDamageTrajectoryProjection:
    """Project health thresholds into wall-clock time from explicit raid DPS evidence.

    Threshold values are fractions of maximum health remaining, e.g. 0.70 for 70%.
    Damage is integrated through the supplied piecewise-constant DPS trajectory.
    Gaps or exhausted finite segments leave later thresholds unresolved rather than
    extending the final known DPS rate implicitly.
    """

    health = float(maximum_health)
    if not math.isfinite(health) or health <= 0:
        raise ValueError("maximum encounter health must be finite and positive")

    ordered_segments = tuple(sorted(segments, key=lambda item: item.start_seconds))
    previous_end: float | None = 0.0
    for index, segment in enumerate(ordered_segments):
        if index == 0 and segment.start_seconds != 0:
            raise ValueError("raid damage trajectory must begin at 0 seconds")
        if previous_end is None:
            raise ValueError("an open-ended raid damage segment must be the final segment")
        if not math.isclose(segment.start_seconds, previous_end, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("raid damage trajectory segments must be contiguous")
        previous_end = segment.end_seconds

    projected = []
    for raw_threshold in thresholds:
        fraction = float(raw_threshold)
        if not math.isfinite(fraction) or not 0 < fraction < 1:
            raise ValueError("health threshold fraction must be between 0 and 1")

        damage_required = health * (1.0 - fraction)
        remaining = damage_required
        resolved_time: float | None = None

        for segment in ordered_segments:
            if segment.end_seconds is None:
                resolved_time = segment.start_seconds + remaining / segment.damage_per_second
                remaining = 0.0
                break

            duration = segment.end_seconds - segment.start_seconds
            capacity = duration * segment.damage_per_second
            if remaining <= capacity + 1e-9:
                resolved_time = segment.start_seconds + remaining / segment.damage_per_second
                remaining = 0.0
                break
            remaining -= capacity

        projected.append(
            HealthThresholdProjection(
                threshold_fraction=fraction,
                health_at_threshold=health * fraction,
                damage_required=damage_required,
                time_seconds=resolved_time,
                resolved=resolved_time is not None,
                reason=(
                    "projected from explicit piecewise raid DPS trajectory"
                    if resolved_time is not None
                    else "supplied raid DPS trajectory ends before this health threshold is reached"
                ),
            )
        )

    return FightDamageTrajectoryProjection(
        maximum_health=health,
        segments=ordered_segments,
        thresholds=tuple(projected),
    )
