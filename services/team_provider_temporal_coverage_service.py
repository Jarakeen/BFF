from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamProviderTimedApplication:
    """One planned activation of a team-facing provider effect.

    Timing is modeled separately from recipient capacity. The same application may
    cover all intended recipients, one six-target subgroup, or another subset. The
    coverage-capacity service answers *who* can be reached; this service answers
    *when* the named effect is active.
    """

    effect_key: str
    source: str
    start_seconds: float
    duration_seconds: float
    application_label: str = "application"

    def __post_init__(self) -> None:
        if not str(self.effect_key or "").strip():
            raise ValueError("effect_key is required")
        if not str(self.source or "").strip():
            raise ValueError("source is required")
        if self.start_seconds < 0:
            raise ValueError("start_seconds cannot be negative")
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

    @property
    def end_seconds(self) -> float:
        return float(self.start_seconds) + float(self.duration_seconds)


@dataclass(frozen=True)
class TeamProviderTemporalRequirement:
    """A timed encounter window that should receive one named provider effect.

    ``minimum_distinct_sources`` is a strategy constraint, not a universal property
    of the named buff. Use it when the encounter plan intentionally requires more
    than one carrier, for example alternating support ultimates through a burn phase.
    """

    effect_key: str
    start_seconds: float
    end_seconds: float
    label: str = "required window"
    minimum_distinct_sources: int = 1

    def __post_init__(self) -> None:
        if not str(self.effect_key or "").strip():
            raise ValueError("effect_key is required")
        if self.start_seconds < 0:
            raise ValueError("start_seconds cannot be negative")
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        if self.minimum_distinct_sources <= 0:
            raise ValueError("minimum_distinct_sources must be positive")

    @property
    def duration_seconds(self) -> float:
        return float(self.end_seconds) - float(self.start_seconds)


@dataclass(frozen=True)
class TeamProviderTemporalCoverageResult:
    effect_key: str
    required_start_seconds: float
    required_end_seconds: float
    required_duration_seconds: float
    covered_seconds: float
    uncovered_seconds: float
    simultaneous_overlap_seconds: float
    coverage_ratio: float
    full_window_covered: bool
    covered_intervals: tuple[tuple[float, float], ...]
    uncovered_intervals: tuple[tuple[float, float], ...]
    active_sources: tuple[str, ...]
    minimum_distinct_sources: int
    distinct_source_count: int
    distinct_source_requirement_met: bool

    @property
    def full_requirement_met(self) -> bool:
        return self.full_window_covered and self.distinct_source_requirement_met


class TeamProviderTemporalCoverageService:
    """Evaluate staggered provider uptime over a required encounter window.

    Duplicate copies of a named buff do not numerically stack, but multiple carriers
    may still be strategically correct. Staggered applications can extend uptime
    through a difficult phase, while intentional simultaneous overlap may be needed
    for recipient targeting or reliability. This service therefore reports overlap
    instead of automatically classifying it as waste.
    """

    @staticmethod
    def _canonical(value: object) -> str:
        return "_".join(str(value or "").strip().casefold().replace("-", " ").split())

    @classmethod
    def evaluate(
        cls,
        requirement: TeamProviderTemporalRequirement,
        *,
        applications: tuple[TeamProviderTimedApplication, ...],
    ) -> TeamProviderTemporalCoverageResult:
        required_key = cls._canonical(requirement.effect_key)
        start = float(requirement.start_seconds)
        end = float(requirement.end_seconds)

        clipped: list[tuple[float, float, str]] = []
        for application in applications:
            if cls._canonical(application.effect_key) != required_key:
                continue
            left = max(start, float(application.start_seconds))
            right = min(end, float(application.end_seconds))
            if right <= left:
                continue
            clipped.append((left, right, str(application.source)))

        clipped.sort(key=lambda item: (item[0], item[1], item[2].casefold(), item[2]))

        merged: list[list[float]] = []
        for left, right, _ in clipped:
            if not merged or left > merged[-1][1] + 1e-9:
                merged.append([left, right])
            else:
                merged[-1][1] = max(merged[-1][1], right)

        covered_intervals = tuple((left, right) for left, right in merged)
        covered_seconds = sum(right - left for left, right in covered_intervals)
        required_seconds = end - start
        uncovered_seconds = max(0.0, required_seconds - covered_seconds)

        total_application_seconds = sum(right - left for left, right, _ in clipped)
        overlap_seconds = max(0.0, total_application_seconds - covered_seconds)

        uncovered: list[tuple[float, float]] = []
        cursor = start
        for left, right in covered_intervals:
            if left > cursor + 1e-9:
                uncovered.append((cursor, left))
            cursor = max(cursor, right)
        if cursor < end - 1e-9:
            uncovered.append((cursor, end))

        sources = tuple(dict.fromkeys(source for _, _, source in clipped))
        distinct_source_count = len(sources)
        source_requirement_met = (
            distinct_source_count >= requirement.minimum_distinct_sources
        )
        ratio = 1.0 if required_seconds <= 0 else covered_seconds / required_seconds
        full = uncovered_seconds <= 1e-9
        return TeamProviderTemporalCoverageResult(
            effect_key=requirement.effect_key,
            required_start_seconds=start,
            required_end_seconds=end,
            required_duration_seconds=required_seconds,
            covered_seconds=covered_seconds,
            uncovered_seconds=uncovered_seconds,
            simultaneous_overlap_seconds=overlap_seconds,
            coverage_ratio=ratio,
            full_window_covered=full,
            covered_intervals=covered_intervals,
            uncovered_intervals=tuple(uncovered),
            active_sources=sources,
            minimum_distinct_sources=requirement.minimum_distinct_sources,
            distinct_source_count=distinct_source_count,
            distinct_source_requirement_met=source_requirement_met,
        )
