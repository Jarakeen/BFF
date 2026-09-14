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
class FightEndProjection:
    damage_required: float
    time_seconds: float | None
    resolved: bool
    reason: str


@dataclass(frozen=True)
class FightDamageTrajectoryProjection:
    maximum_health: float
    segments: tuple[RaidDamageSegment, ...]
    thresholds: tuple[HealthThresholdProjection, ...]


def _ordered_segments(
    segments: tuple[RaidDamageSegment, ...],
) -> tuple[RaidDamageSegment, ...]:
    ordered = tuple(sorted(segments, key=lambda item: item.start_seconds))
    previous_end: float | None = 0.0
    for index, segment in enumerate(ordered):
        if index == 0 and segment.start_seconds != 0:
            raise ValueError("raid damage trajectory must begin at 0 seconds")
        if previous_end is None:
            raise ValueError("an open-ended raid damage segment must be the final segment")
        if not math.isclose(segment.start_seconds, previous_end, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("raid damage trajectory segments must be contiguous")
        previous_end = segment.end_seconds
    return ordered


def _project_damage_time(
    *,
    damage_required: float,
    segments: tuple[RaidDamageSegment, ...],
) -> float | None:
    required = float(damage_required)
    if not math.isfinite(required) or required < 0:
        raise ValueError("required damage must be finite and non-negative")
    if required == 0:
        return 0.0

    remaining = required
    for segment in segments:
        if segment.end_seconds is None:
            return segment.start_seconds + remaining / segment.damage_per_second

        duration = segment.end_seconds - segment.start_seconds
        capacity = duration * segment.damage_per_second
        if remaining <= capacity + 1e-9:
            return segment.start_seconds + remaining / segment.damage_per_second
        remaining -= capacity
    return None


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

    ordered_segments = _ordered_segments(tuple(segments))

    projected = []
    for raw_threshold in thresholds:
        fraction = float(raw_threshold)
        if not math.isfinite(fraction) or not 0 < fraction < 1:
            raise ValueError("health threshold fraction must be between 0 and 1")

        damage_required = health * (1.0 - fraction)
        resolved_time = _project_damage_time(
            damage_required=damage_required,
            segments=ordered_segments,
        )
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


def project_fight_end_time(
    trajectory: FightDamageTrajectoryProjection,
) -> FightEndProjection:
    """Project the encounter end from the same explicit raid-damage trajectory.

    This is the 0-Health endpoint of the already-reviewed trajectory, not a default
    fight length. Finite evidence that ends before maximum Health is exhausted stays
    unresolved rather than extending the final DPS rate or inventing a fallback horizon.
    """

    time_seconds = _project_damage_time(
        damage_required=float(trajectory.maximum_health),
        segments=tuple(trajectory.segments),
    )
    return FightEndProjection(
        damage_required=float(trajectory.maximum_health),
        time_seconds=time_seconds,
        resolved=time_seconds is not None,
        reason=(
            "projected encounter end from explicit piecewise raid DPS trajectory"
            if time_seconds is not None
            else "supplied raid DPS trajectory ends before encounter Health reaches zero"
        ),
    )
