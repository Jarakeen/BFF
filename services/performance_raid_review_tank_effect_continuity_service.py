from __future__ import annotations

"""Measure reviewed tank-owned effect continuity in eligible encounter time.

This is a role/assignment interpretation layer over canonical RuntimeEffectActiveWindow
instances. It owns no aura lifetime mechanics. Callers provide reviewed mechanic windows
to exclude from eligibility (for example, Lokkestiiz flight) plus explicit tank effect
assignments. Coverage is measured only from observed active windows; missing effect end
evidence must remain unresolved upstream rather than being invented here.
"""

from dataclasses import dataclass
from typing import Iterable

from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from services.performance_raid_review_landing_recovery_service import RaidReviewRecoveryActor
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow


@dataclass(frozen=True, slots=True)
class RaidReviewTankEffectRequirement:
    semantic_key: str
    label: str
    effect_names: tuple[str, ...]
    source_actor_id: int
    reviewed: bool = True

    def __post_init__(self) -> None:
        if self.reviewed and not str(self.semantic_key or "").strip():
            raise ValueError("Reviewed tank effect requirements require semantic_key.")
        if self.reviewed and not tuple(name for name in self.effect_names if str(name).strip()):
            raise ValueError("Reviewed tank effect requirements require effect_names.")
        if self.reviewed and int(self.source_actor_id) <= 0:
            raise ValueError("Reviewed tank effect requirements require a positive source_actor_id.")


@dataclass(frozen=True, slots=True)
class RaidReviewTankEffectContinuityObservation:
    report_code: str
    fight_id: int
    actor_id: int
    actor_label: str
    member_key: str
    requirement_semantic_key: str
    requirement_label: str
    eligible_seconds: float
    covered_seconds: float
    coverage_percent: float
    active_effect_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RaidReviewTankEffectContinuityResult:
    observations: tuple[RaidReviewTankEffectContinuityObservation, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewTankEffectContinuityService:
    """Measure tank-owned named effect coverage across reviewed eligible time."""

    def measure(
        self,
        *,
        report_code: str,
        fight_id: int,
        fight_duration_seconds: float,
        effect_windows: Iterable[RuntimeEffectActiveWindow],
        actors: Iterable[RaidReviewRecoveryActor],
        requirements: Iterable[RaidReviewTankEffectRequirement],
        excluded_mechanic_windows: Iterable[RaidReviewEncounterWindow] = (),
    ) -> RaidReviewTankEffectContinuityResult:
        duration = float(fight_duration_seconds)
        if duration <= 0:
            raise ValueError("fight_duration_seconds must be positive")

        tank_actors = {
            int(actor.actor_id): actor
            for actor in actors
            if self._canonical_role(actor.role) == "Tank"
        }
        reviewed = tuple(item for item in requirements if item.reviewed)
        if not reviewed:
            return RaidReviewTankEffectContinuityResult(
                observations=(),
                unresolved=("No reviewed tank effect requirements were supplied.",),
            )

        eligible_segments = self._eligible_segments(
            duration_seconds=duration,
            report_code=str(report_code),
            fight_id=int(fight_id),
            excluded_windows=tuple(excluded_mechanic_windows),
        )
        eligible_seconds = sum(end - start for start, end in eligible_segments)
        if eligible_seconds <= 0:
            return RaidReviewTankEffectContinuityResult(
                observations=(),
                unresolved=("No eligible encounter time remained for tank effect continuity analysis.",),
            )

        windows = tuple(effect_windows)
        observations: list[RaidReviewTankEffectContinuityObservation] = []
        unresolved: list[str] = []

        for requirement in reviewed:
            actor = tank_actors.get(int(requirement.source_actor_id))
            if actor is None:
                unresolved.append(
                    f"{requirement.label}: assigned tank actor {requirement.source_actor_id} was not supplied as a Tank."
                )
                continue

            wanted_names = {
                str(name).strip().casefold()
                for name in requirement.effect_names
                if str(name).strip()
            }
            wanted_source = f"esologs:actor:{int(requirement.source_actor_id)}"
            matching = tuple(
                window
                for window in windows
                if str(window.effect_name or "").strip().casefold() in wanted_names
                and str(window.source or "") == wanted_source
            )

            covered_intervals: list[tuple[float, float]] = []
            active_names: set[str] = set()
            for window in matching:
                active_names.add(str(window.effect_name))
                window_start = float(window.start_seconds)
                window_end = float(window.end_seconds)
                for segment_start, segment_end in eligible_segments:
                    start = max(window_start, segment_start)
                    end = min(window_end, segment_end)
                    if end > start:
                        covered_intervals.append((start, end))

            merged = self._merge_intervals(covered_intervals)
            covered_seconds = sum(end - start for start, end in merged)
            observations.append(
                RaidReviewTankEffectContinuityObservation(
                    report_code=str(report_code),
                    fight_id=int(fight_id),
                    actor_id=int(actor.actor_id),
                    actor_label=str(actor.actor_label),
                    member_key=str(actor.member_key or ""),
                    requirement_semantic_key=str(requirement.semantic_key),
                    requirement_label=str(requirement.label),
                    eligible_seconds=round(eligible_seconds, 6),
                    covered_seconds=round(covered_seconds, 6),
                    coverage_percent=round((covered_seconds / eligible_seconds) * 100.0, 2),
                    active_effect_names=tuple(sorted(active_names, key=str.casefold)),
                )
            )

        observations.sort(
            key=lambda row: (
                row.actor_label.casefold(),
                row.requirement_semantic_key,
            )
        )
        return RaidReviewTankEffectContinuityResult(
            observations=tuple(observations),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _merge_intervals(intervals: Iterable[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
        ordered = sorted((float(start), float(end)) for start, end in intervals if end > start)
        merged: list[list[float]] = []
        for start, end in ordered:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        return tuple((start, end) for start, end in merged)

    @classmethod
    def _eligible_segments(
        cls,
        *,
        duration_seconds: float,
        report_code: str,
        fight_id: int,
        excluded_windows: tuple[RaidReviewEncounterWindow, ...],
    ) -> tuple[tuple[float, float], ...]:
        exclusions = cls._merge_intervals(
            (
                max(0.0, float(window.start_seconds)),
                min(float(duration_seconds), float(window.end_seconds)),
            )
            for window in excluded_windows
            if window.reviewed
            and str(window.report_code) == report_code
            and int(window.fight_id) == fight_id
            and float(window.end_seconds) > 0.0
            and float(window.start_seconds) < float(duration_seconds)
        )
        segments: list[tuple[float, float]] = []
        cursor = 0.0
        for start, end in exclusions:
            if start > cursor:
                segments.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < duration_seconds:
            segments.append((cursor, duration_seconds))
        return tuple(segments)

    @staticmethod
    def _canonical_role(role: str) -> str:
        value = str(role or "").strip().casefold()
        if value in {"healer", "healing"}:
            return "Healer"
        if value in {"tank", "tanking"}:
            return "Tank"
        return "DPS"


__all__ = [
    "PerformanceRaidReviewTankEffectContinuityService",
    "RaidReviewTankEffectContinuityObservation",
    "RaidReviewTankEffectContinuityResult",
    "RaidReviewTankEffectRequirement",
]
