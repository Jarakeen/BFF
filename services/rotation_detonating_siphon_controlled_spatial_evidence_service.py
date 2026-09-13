from __future__ import annotations

"""Research-only controlled spatial evidence analysis for Detonating Siphon.

This module evaluates explicitly observed hit/no-hit samples against competing spatial
hypotheses. It does not write production mechanic rules, infer ESO coordinate units, or
promote a hypothesis merely because it fits too few samples.
"""

from dataclasses import dataclass
import math


Point = tuple[float, float]


@dataclass(frozen=True)
class RotationDetonatingSiphonControlledSpatialSample:
    label: str
    caster: Point
    corpse_candidate: Point
    target: Point
    damage_observed: bool

    def __post_init__(self) -> None:
        label = str(self.label or "").strip()
        if not label:
            raise ValueError("controlled Siphon spatial sample requires label")
        object.__setattr__(self, "label", label)
        for field_name in ("caster", "corpse_candidate", "target"):
            raw = getattr(self, field_name)
            if len(raw) != 2:
                raise ValueError(f"{field_name} must be an x/y pair")
            point = (float(raw[0]), float(raw[1]))
            if not all(math.isfinite(value) for value in point):
                raise ValueError(f"{field_name} coordinates must be finite")
            object.__setattr__(self, field_name, point)
        object.__setattr__(self, "damage_observed", bool(self.damage_observed))


@dataclass(frozen=True)
class RotationDetonatingSiphonSpatialHypothesisResult:
    name: str
    matching_samples: int
    conflicting_samples: tuple[str, ...]

    @property
    def consistent(self) -> bool:
        return not self.conflicting_samples


@dataclass(frozen=True)
class RotationDetonatingSiphonControlledSpatialEvidenceReport:
    sample_count: int
    caster_circle: RotationDetonatingSiphonSpatialHypothesisResult
    corpse_circle: RotationDetonatingSiphonSpatialHypothesisResult
    hit_sample_minimum_segment_half_width: float | None
    no_hit_segment_upper_bound: float | None
    corridor_width_resolved: bool
    unresolved: tuple[str, ...] = ()


class RotationDetonatingSiphonControlledSpatialEvidenceService:
    """Compare controlled observations with candidate Siphon spatial hypotheses.

    Circle hypotheses are intentionally evaluated *alone*. A mismatch does not mean the
    complete Siphon geometry is wrong because the tether/corridor may independently cause
    damage. The results answer only whether a standalone 5-unit circle at each endpoint
    explains each sample.

    Corridor evidence is represented as bounds on perpendicular distance to the bounded
    caster->corpse-candidate segment. Hit samples establish a lower bound on the half-width
    required to include them. No-hit samples establish an upper bound only when the target
    projects onto the interior of the segment; endpoint-adjacent samples are not used for
    that bound because endpoint-circle behavior can confound them.
    """

    def analyze(
        self,
        samples: tuple[RotationDetonatingSiphonControlledSpatialSample, ...],
        *,
        circle_radius: float = 5.0,
    ) -> RotationDetonatingSiphonControlledSpatialEvidenceReport:
        radius = float(circle_radius)
        if not math.isfinite(radius) or radius < 0.0:
            raise ValueError("circle_radius must be finite and non-negative")
        observations = tuple(samples)
        if not observations:
            return self._empty("controlled Siphon spatial evidence requires at least one sample")

        caster_conflicts: list[str] = []
        corpse_conflicts: list[str] = []
        caster_matches = 0
        corpse_matches = 0
        hit_segment_distances: list[float] = []
        no_hit_interior_distances: list[float] = []

        for sample in observations:
            caster_inside = self._distance(sample.target, sample.caster) <= radius + 1e-9
            corpse_inside = (
                self._distance(sample.target, sample.corpse_candidate) <= radius + 1e-9
            )
            if caster_inside == sample.damage_observed:
                caster_matches += 1
            else:
                caster_conflicts.append(sample.label)
            if corpse_inside == sample.damage_observed:
                corpse_matches += 1
            else:
                corpse_conflicts.append(sample.label)

            segment_distance, projection = self._distance_to_segment_with_projection(
                sample.target,
                sample.caster,
                sample.corpse_candidate,
            )
            if sample.damage_observed:
                hit_segment_distances.append(segment_distance)
            elif 1e-9 < projection < 1.0 - 1e-9:
                no_hit_interior_distances.append(segment_distance)

        minimum_width = max(hit_segment_distances) if hit_segment_distances else None
        upper_bound = min(no_hit_interior_distances) if no_hit_interior_distances else None
        corridor_resolved = (
            minimum_width is not None
            and upper_bound is not None
            and minimum_width < upper_bound
        )

        unresolved: list[str] = []
        if not any(sample.damage_observed for sample in observations):
            unresolved.append("controlled sample set contains no observed-hit cases")
        if all(sample.damage_observed for sample in observations):
            unresolved.append("controlled sample set contains no observed-no-hit cases")
        if upper_bound is None:
            unresolved.append(
                "no interior-segment no-hit sample is available to bound tether half-width"
            )
        elif minimum_width is not None and minimum_width >= upper_bound:
            unresolved.append(
                "observed hit/no-hit segment distances do not define a non-overlapping tether half-width interval"
            )

        return RotationDetonatingSiphonControlledSpatialEvidenceReport(
            sample_count=len(observations),
            caster_circle=RotationDetonatingSiphonSpatialHypothesisResult(
                name="caster_centered_circle",
                matching_samples=caster_matches,
                conflicting_samples=tuple(caster_conflicts),
            ),
            corpse_circle=RotationDetonatingSiphonSpatialHypothesisResult(
                name="corpse_centered_circle",
                matching_samples=corpse_matches,
                conflicting_samples=tuple(corpse_conflicts),
            ),
            hit_sample_minimum_segment_half_width=minimum_width,
            no_hit_segment_upper_bound=upper_bound,
            corridor_width_resolved=corridor_resolved,
            unresolved=tuple(unresolved),
        )

    @staticmethod
    def _distance(a: Point, b: Point) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @classmethod
    def _distance_to_segment_with_projection(
        cls,
        point: Point,
        start: Point,
        end: Point,
    ) -> tuple[float, float]:
        vx = end[0] - start[0]
        vy = end[1] - start[1]
        length_squared = vx * vx + vy * vy
        if length_squared <= 1e-18:
            return cls._distance(point, start), 0.0
        raw_projection = (
            (point[0] - start[0]) * vx + (point[1] - start[1]) * vy
        ) / length_squared
        projection = max(0.0, min(1.0, raw_projection))
        closest = (start[0] + projection * vx, start[1] + projection * vy)
        return cls._distance(point, closest), raw_projection

    @staticmethod
    def _empty(
        message: str,
    ) -> RotationDetonatingSiphonControlledSpatialEvidenceReport:
        empty_hypothesis = RotationDetonatingSiphonSpatialHypothesisResult(
            name="unavailable",
            matching_samples=0,
            conflicting_samples=(),
        )
        return RotationDetonatingSiphonControlledSpatialEvidenceReport(
            sample_count=0,
            caster_circle=empty_hypothesis,
            corpse_circle=empty_hypothesis,
            hit_sample_minimum_segment_half_width=None,
            no_hit_segment_upper_bound=None,
            corridor_width_resolved=False,
            unresolved=(message,),
        )


__all__ = [
    "RotationDetonatingSiphonControlledSpatialEvidenceReport",
    "RotationDetonatingSiphonControlledSpatialEvidenceService",
    "RotationDetonatingSiphonControlledSpatialSample",
    "RotationDetonatingSiphonSpatialHypothesisResult",
]
