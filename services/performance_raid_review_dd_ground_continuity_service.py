from __future__ import annotations

"""Measure DD boss-damage continuity inside reviewed eligible encounter time.

This service owns no encounter mechanics.  Callers supply reviewed mechanic windows to
exclude from eligibility (for example, Lokkestiiz flight windows).  The remaining
intervals are treated as eligible ground time for one narrow observation: gaps between
consecutive positive boss-damage events from a DD.

The inactivity threshold is an analysis parameter, not ESO mechanics truth.  Leading
and trailing time in each eligible interval are intentionally not scored because the
absence of a damage event alone does not prove the player was obligated and able to hit
the boss at those boundaries.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_landing_recovery_service import RaidReviewRecoveryActor
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow


_DAMAGE_TYPES = {"damage", "calculateddamage"}


@dataclass(frozen=True, slots=True)
class RaidReviewDDGroundContinuityObservation:
    report_code: str
    fight_id: int
    actor_id: int
    actor_label: str
    member_key: str
    damage_event_count: int
    measured_gap_count: int
    inactivity_gap_count: int
    total_inactivity_seconds: float
    longest_inactivity_seconds: float
    inactivity_windows: tuple[tuple[float, float], ...]
    inactivity_threshold_seconds: float


@dataclass(frozen=True, slots=True)
class RaidReviewDDGroundContinuityResult:
    observations: tuple[RaidReviewDDGroundContinuityObservation, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewDDGroundContinuityService:
    """Measure positive boss-damage silence between hits in eligible ground windows."""

    def measure(
        self,
        *,
        report_code: str,
        fight_id: int,
        fight_start_time_ms: float,
        fight_end_time_ms: float,
        events: Iterable[dict],
        boss_actor_id: int,
        actors: Iterable[RaidReviewRecoveryActor],
        excluded_mechanic_windows: Iterable[RaidReviewEncounterWindow] = (),
        inactivity_threshold_seconds: float = 3.0,
    ) -> RaidReviewDDGroundContinuityResult:
        start_ms = float(fight_start_time_ms)
        end_ms = float(fight_end_time_ms)
        if end_ms <= start_ms:
            raise ValueError("fight_end_time_ms must be after fight_start_time_ms")

        threshold = float(inactivity_threshold_seconds)
        if threshold <= 0:
            raise ValueError("inactivity_threshold_seconds must be positive")

        duration_seconds = (end_ms - start_ms) / 1000.0
        eligible_segments = self._eligible_segments(
            duration_seconds=duration_seconds,
            report_code=str(report_code),
            fight_id=int(fight_id),
            excluded_windows=tuple(excluded_mechanic_windows),
        )

        rows = tuple(event for event in events if isinstance(event, dict))
        dd_actors = tuple(
            actor for actor in actors if self._canonical_role(actor.role) == "DPS"
        )
        unresolved: list[str] = []
        observations: list[RaidReviewDDGroundContinuityObservation] = []

        if not dd_actors:
            return RaidReviewDDGroundContinuityResult(
                observations=(),
                unresolved=("No DPS actors were supplied for ground-continuity analysis.",),
            )

        for actor in dd_actors:
            timestamps = tuple(
                sorted(
                    time_seconds
                    for row in rows
                    if self._is_positive_boss_damage(
                        row,
                        actor_id=int(actor.actor_id),
                        boss_actor_id=int(boss_actor_id),
                    )
                    if (time_seconds := self._relative_seconds(row, start_ms)) is not None
                    and 0.0 <= time_seconds <= duration_seconds
                )
            )

            inactivity_windows: list[tuple[float, float]] = []
            measured_gap_count = 0
            participating_events = 0

            for segment_start, segment_end in eligible_segments:
                segment_events = tuple(
                    value
                    for value in timestamps
                    if segment_start <= value <= segment_end
                )
                participating_events += len(segment_events)
                if len(segment_events) < 2:
                    continue
                for earlier, later in zip(segment_events, segment_events[1:]):
                    gap = later - earlier
                    if gap <= 0:
                        continue
                    measured_gap_count += 1
                    if gap > threshold:
                        inactivity_windows.append((round(earlier, 6), round(later, 6)))

            if measured_gap_count == 0:
                unresolved.append(
                    f"{actor.actor_label}: fewer than two positive boss-damage events were observed within the same eligible ground interval; DD continuity was not inferred."
                )
                continue

            gap_lengths = tuple(end - start for start, end in inactivity_windows)
            observations.append(
                RaidReviewDDGroundContinuityObservation(
                    report_code=str(report_code),
                    fight_id=int(fight_id),
                    actor_id=int(actor.actor_id),
                    actor_label=str(actor.actor_label),
                    member_key=str(actor.member_key or ""),
                    damage_event_count=participating_events,
                    measured_gap_count=measured_gap_count,
                    inactivity_gap_count=len(inactivity_windows),
                    total_inactivity_seconds=round(sum(gap_lengths), 6),
                    longest_inactivity_seconds=round(max(gap_lengths, default=0.0), 6),
                    inactivity_windows=tuple(inactivity_windows),
                    inactivity_threshold_seconds=threshold,
                )
            )

        observations.sort(key=lambda row: (row.actor_label.casefold(), row.actor_id))
        return RaidReviewDDGroundContinuityResult(
            observations=tuple(observations),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _eligible_segments(
        *,
        duration_seconds: float,
        report_code: str,
        fight_id: int,
        excluded_windows: tuple[RaidReviewEncounterWindow, ...],
    ) -> tuple[tuple[float, float], ...]:
        exclusions = sorted(
            (
                max(0.0, float(window.start_seconds)),
                min(duration_seconds, float(window.end_seconds)),
            )
            for window in excluded_windows
            if window.reviewed
            and str(window.report_code) == report_code
            and int(window.fight_id) == fight_id
            and float(window.end_seconds) > 0.0
            and float(window.start_seconds) < duration_seconds
        )

        merged: list[list[float]] = []
        for start, end in exclusions:
            if end <= start:
                continue
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        segments: list[tuple[float, float]] = []
        cursor = 0.0
        for start, end in merged:
            if start > cursor:
                segments.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < duration_seconds:
            segments.append((cursor, duration_seconds))
        return tuple(segments)

    @staticmethod
    def _is_positive_boss_damage(row: dict, *, actor_id: int, boss_actor_id: int) -> bool:
        if str(row.get("type") or "").strip().casefold() not in _DAMAGE_TYPES:
            return False
        try:
            if int(row.get("sourceID")) != actor_id or int(row.get("targetID")) != boss_actor_id:
                return False
            return float(row.get("amount", 0.0) or 0.0) > 0.0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _relative_seconds(row: dict, start_ms: float) -> float | None:
        try:
            return (float(row.get("timestamp")) - start_ms) / 1000.0
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _canonical_role(role: str) -> str:
        value = str(role or "").strip().casefold()
        if value in {"healer", "healing"}:
            return "Healer"
        if value in {"tank", "tanking"}:
            return "Tank"
        return "DPS"


__all__ = [
    "PerformanceRaidReviewDDGroundContinuityService",
    "RaidReviewDDGroundContinuityObservation",
    "RaidReviewDDGroundContinuityResult",
]
