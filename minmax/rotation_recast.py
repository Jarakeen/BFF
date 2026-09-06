from __future__ import annotations

from dataclasses import dataclass
import math

from .rotation_plan import RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationRecastRule:
    """Explicit verified duration evidence for one named scheduled ability.

    Phase 13 must not derive this value from skill names or tooltip folklore. A
    caller supplies a duration only after a canonical source has resolved it.
    ``refresh_lead_seconds`` allows a deliberate pre-expiry refresh window while
    keeping truly premature recasts distinguishable from intentional overlap.
    """

    skill_name: str
    duration_seconds: float
    bar: str | None = None
    refresh_lead_seconds: float = 0.0

    def __post_init__(self) -> None:
        name = str(self.skill_name or "").strip()
        if not name:
            raise ValueError("recast rule requires a skill name")
        object.__setattr__(self, "skill_name", name)

        duration = float(self.duration_seconds)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("recast rule duration must be finite and greater than zero")
        object.__setattr__(self, "duration_seconds", duration)

        lead = float(self.refresh_lead_seconds)
        if not math.isfinite(lead) or lead < 0:
            raise ValueError("recast refresh lead must be finite and non-negative")
        if lead > duration:
            raise ValueError("recast refresh lead cannot exceed the effect duration")
        object.__setattr__(self, "refresh_lead_seconds", lead)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("recast rule bar must be 'front' or 'back'")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationRecastWindow:
    skill_name: str
    bar: str | None
    cast_time_seconds: float
    active_until_seconds: float
    preferred_refresh_seconds: float
    next_cast_seconds: float | None
    gap_seconds: float
    premature_seconds: float


@dataclass(frozen=True)
class RotationRecastSummary:
    skill_name: str
    bar: str | None
    duration_seconds: float
    cast_count: int
    active_seconds: float
    uptime_fraction: float
    total_gap_seconds: float
    total_premature_seconds: float


@dataclass(frozen=True)
class RotationRecastAnalysis:
    windows: tuple[RotationRecastWindow, ...]
    summaries: tuple[RotationRecastSummary, ...]
    unresolved: tuple[str, ...] = ()


class RotationRecastAnalyzer:
    """Measure duration/recast behavior without changing the authored schedule."""

    def analyze(
        self,
        plan: RotationPlan,
        rules: tuple[RotationRecastRule, ...],
    ) -> RotationRecastAnalysis:
        normalized_rules = tuple(rules)
        self._validate_rule_uniqueness(normalized_rules)

        windows: list[RotationRecastWindow] = []
        summaries: list[RotationRecastSummary] = []
        unresolved: list[str] = []

        for rule in normalized_rules:
            casts = [
                action
                for action in plan.actions
                if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
                and action.name
                and action.name.casefold() == rule.skill_name.casefold()
                and (rule.bar is None or action.bar == rule.bar)
            ]

            if not casts:
                scope = f" on {rule.bar} bar" if rule.bar else ""
                unresolved.append(
                    f"duration rule for '{rule.skill_name}'{scope} matched no scheduled casts"
                )
                continue

            intervals: list[tuple[float, float]] = []
            total_gap = 0.0
            total_premature = 0.0

            for index, cast in enumerate(casts):
                active_until = min(
                    plan.duration_seconds,
                    cast.time_seconds + rule.duration_seconds,
                )
                preferred_refresh = max(
                    cast.time_seconds,
                    cast.time_seconds
                    + rule.duration_seconds
                    - rule.refresh_lead_seconds,
                )
                next_cast = casts[index + 1].time_seconds if index + 1 < len(casts) else None
                gap = 0.0
                premature = 0.0
                if next_cast is not None:
                    raw_expiry = cast.time_seconds + rule.duration_seconds
                    if next_cast > raw_expiry:
                        gap = next_cast - raw_expiry
                    elif next_cast < preferred_refresh:
                        premature = preferred_refresh - next_cast

                total_gap += gap
                total_premature += premature
                intervals.append((cast.time_seconds, active_until))
                windows.append(
                    RotationRecastWindow(
                        skill_name=rule.skill_name,
                        bar=cast.bar,
                        cast_time_seconds=cast.time_seconds,
                        active_until_seconds=active_until,
                        preferred_refresh_seconds=preferred_refresh,
                        next_cast_seconds=next_cast,
                        gap_seconds=gap,
                        premature_seconds=premature,
                    )
                )

            active_seconds = self._union_duration(intervals)
            uptime_fraction = (
                active_seconds / plan.duration_seconds
                if plan.duration_seconds > 0
                else 0.0
            )
            summaries.append(
                RotationRecastSummary(
                    skill_name=rule.skill_name,
                    bar=rule.bar,
                    duration_seconds=rule.duration_seconds,
                    cast_count=len(casts),
                    active_seconds=active_seconds,
                    uptime_fraction=uptime_fraction,
                    total_gap_seconds=total_gap,
                    total_premature_seconds=total_premature,
                )
            )

        return RotationRecastAnalysis(
            windows=tuple(windows),
            summaries=tuple(summaries),
            unresolved=tuple(unresolved),
        )

    @staticmethod
    def _validate_rule_uniqueness(rules: tuple[RotationRecastRule, ...]) -> None:
        seen: set[tuple[str, str | None]] = set()
        for rule in rules:
            key = (rule.skill_name.casefold(), rule.bar)
            if key in seen:
                raise ValueError(
                    f"duplicate recast rule for {rule.skill_name!r} on {rule.bar or 'any'} bar"
                )
            seen.add(key)

    @staticmethod
    def _union_duration(intervals: list[tuple[float, float]]) -> float:
        if not intervals:
            return 0.0
        ordered = sorted(intervals)
        start, end = ordered[0]
        total = 0.0
        for next_start, next_end in ordered[1:]:
            if next_start <= end:
                end = max(end, next_end)
                continue
            total += max(0.0, end - start)
            start, end = next_start, next_end
        total += max(0.0, end - start)
        return total
