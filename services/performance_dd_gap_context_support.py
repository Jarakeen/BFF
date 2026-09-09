from __future__ import annotations

"""Context for observed DD action gaps using raid-wide damage activity.

This is deliberately evidence-first. A long personal skill gap is not called a
mistake merely because it exists. We compare the interval with the raid-wide
DamageDone graph from the same fight:

* ``raid_quiet`` means raid damage collapsed during the interval, which is
  consistent with transition/target-unavailable/group-downtime context.
* ``raid_active`` means raid damage stayed substantial while this actor had an
  observed action gap, making the interval more useful for personal review.
* ``unknown`` means the graph does not support either conclusion.

These labels are observational, not encounter-mechanic diagnoses.
"""

from dataclasses import dataclass
from statistics import median

_INSTALLED = False
_ORIGINAL_BUILD_SNAPSHOT = None
_RAID_QUIET_RATIO = 0.10
_RAID_ACTIVE_RATIO = 0.50


@dataclass(frozen=True)
class ActionGapContext:
    StartTimestampMs: float
    EndTimestampMs: float
    DurationSeconds: float
    Classification: str
    RaidActivityRatio: float | None = None


@dataclass(frozen=True)
class ActionGapContextDiagnostics:
    RaidQuietCount: int = 0
    RaidActiveCount: int = 0
    UnknownCount: int = 0
    Rows: tuple[ActionGapContext, ...] = ()


def _raid_activity_baseline(values) -> float:
    """Return a conservative normal-raid-activity reference level.

    A median across every positive bucket is too easy for a long low-damage
    transition to drag downward. That can make merely partial raid activity look
    fully active. Use the median of the upper half of positive raid-damage
    buckets instead, which represents the report's ordinary active-damage state
    while still resisting one-off burst spikes.
    """

    positive = sorted(float(value) for value in values if float(value) > 0)
    if not positive:
        return 0.0

    upper_half = positive[len(positive) // 2 :]
    return float(median(upper_half))


def _classify_action_gap_context(
    gaps,
    raid_damage_points,
    fight_start_ms: float,
    quiet_ratio: float = _RAID_QUIET_RATIO,
    active_ratio: float = _RAID_ACTIVE_RATIO,
) -> ActionGapContextDiagnostics:
    if quiet_ratio < 0 or active_ratio <= quiet_ratio:
        raise ValueError("activity ratios must satisfy 0 <= quiet < active")

    points = sorted(
        (float(t), float(v))
        for t, v in raid_damage_points
        if t is not None and v is not None
    )
    baseline = _raid_activity_baseline(value for _time, value in points)

    rows: list[ActionGapContext] = []
    quiet = active = unknown = 0

    for gap in gaps:
        start_ms = float(getattr(gap, "StartTimestampMs"))
        end_ms = float(getattr(gap, "EndTimestampMs"))
        duration = float(getattr(gap, "DurationSeconds"))
        start_s = (start_ms - float(fight_start_ms)) / 1000.0
        end_s = (end_ms - float(fight_start_ms)) / 1000.0
        window = [value for time_s, value in points if start_s <= time_s <= end_s]

        ratio: float | None = None
        classification = "unknown"
        if window and baseline > 0:
            ratio = sum(window) / len(window) / baseline
            if ratio <= quiet_ratio:
                classification = "raid_quiet"
                quiet += 1
            elif ratio >= active_ratio:
                classification = "raid_active"
                active += 1
            else:
                unknown += 1
        else:
            unknown += 1

        rows.append(
            ActionGapContext(
                StartTimestampMs=start_ms,
                EndTimestampMs=end_ms,
                DurationSeconds=duration,
                Classification=classification,
                RaidActivityRatio=round(ratio, 3) if ratio is not None else None,
            )
        )

    return ActionGapContextDiagnostics(
        RaidQuietCount=quiet,
        RaidActiveCount=active,
        UnknownCount=unknown,
        Rows=tuple(rows),
    )


def _build_snapshot_with_gap_context(self, *args, **kwargs):
    assert _ORIGINAL_BUILD_SNAPSHOT is not None
    snapshot = _ORIGINAL_BUILD_SNAPSHOT(self, *args, **kwargs)

    snapshot.ActionGapRaidQuietCount = 0
    snapshot.ActionGapRaidActiveCount = 0
    snapshot.ActionGapUnknownCount = 0
    snapshot.ActionGapContextRows = ()
    snapshot.ActionGapContextNote = ""

    if str(getattr(snapshot, "Role", "")).casefold() != "dps":
        return snapshot

    gaps = tuple(getattr(snapshot, "ObservedActionGaps", ()) or ())
    if not gaps:
        snapshot.ActionGapContextNote = "No long internal action gaps required raid-context classification."
        return snapshot

    try:
        fight = self.capability_service.fetch_fight_summary(
            snapshot.ReportCode, int(snapshot.FightId)
        )
        start = float(fight["start_time"])
        end = float(fight["end_time"])
        raid_points = self.client.get_output_graph(
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="DamageDone",
            hostility_type="Friendlies",
            source_id=None,
        )
        diagnostics = _classify_action_gap_context(gaps, raid_points, start)
        snapshot.ActionGapRaidQuietCount = diagnostics.RaidQuietCount
        snapshot.ActionGapRaidActiveCount = diagnostics.RaidActiveCount
        snapshot.ActionGapUnknownCount = diagnostics.UnknownCount
        snapshot.ActionGapContextRows = diagnostics.Rows
        snapshot.ActionGapContextNote = (
            "Context compares each personal action gap with raid-wide damage in the same interval. "
            "Raid-quiet does not prove a mechanic; raid-active does not prove player error."
        )
    except Exception as exc:
        snapshot.ActionGapUnknownCount = len(gaps)
        snapshot.ActionGapContextNote = f"Raid-context classification unavailable: {exc}"

    return snapshot


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_SNAPSHOT
    if _INSTALLED:
        return

    from services.performance_dashboard_service import PerformanceDashboardService

    _ORIGINAL_BUILD_SNAPSHOT = PerformanceDashboardService.build_snapshot
    PerformanceDashboardService.build_snapshot = _build_snapshot_with_gap_context
    _INSTALLED = True
