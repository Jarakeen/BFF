from __future__ import annotations

"""Observed internal action-gap diagnostics for DD Performance Dashboard tabs.

This layer intentionally avoids the phrase ``dead time`` as a hard judgment.
Without exact mechanic/immunity-window boundaries, a long interval between two
eligible combat-skill casts may be execution loss, forced movement, target
unavailability, death, or another encounter mechanic. We therefore report only
what the log proves: internal skill-to-skill gaps that exceed a transparent
threshold.

Pull-start and fight-end silence are excluded. The analysis reuses eligible skill
cast timestamps already gathered by the weave layer, so it adds no extra ESO
Logs request and never touches the local ESO database.
"""

from dataclasses import dataclass

_INSTALLED = False
_ORIGINAL_BUILD_SNAPSHOT = None
_GAP_THRESHOLD_MS = 2500.0
_TOP_GAP_COUNT = 5


@dataclass(frozen=True)
class ObservedActionGap:
    StartTimestampMs: float
    EndTimestampMs: float
    DurationSeconds: float
    ExcessSeconds: float


@dataclass(frozen=True)
class ActivityDiagnostics:
    GapCount: int = 0
    LargestGapSeconds: float | None = None
    ExcessGapSeconds: float = 0.0
    Gaps: tuple[ObservedActionGap, ...] = ()


def _analyze_action_gaps(
    eligible_skill_timestamps_ms,
    threshold_ms: float = _GAP_THRESHOLD_MS,
    limit: int = _TOP_GAP_COUNT,
) -> ActivityDiagnostics:
    """Measure internal eligible-skill gaps longer than ``threshold_ms``.

    Duplicate timestamps are collapsed. Only intervals *between* eligible skill
    casts are considered, so pre-pull setup and post-combat silence cannot become
    false inactivity findings.
    """

    if threshold_ms <= 0:
        raise ValueError("threshold_ms must be positive")

    ordered = sorted({float(value) for value in eligible_skill_timestamps_ms})
    if len(ordered) < 2:
        return ActivityDiagnostics()

    gaps: list[ObservedActionGap] = []
    for start, end in zip(ordered, ordered[1:]):
        duration_ms = end - start
        if duration_ms <= threshold_ms:
            continue
        gaps.append(
            ObservedActionGap(
                StartTimestampMs=start,
                EndTimestampMs=end,
                DurationSeconds=round(duration_ms / 1000.0, 3),
                ExcessSeconds=round((duration_ms - threshold_ms) / 1000.0, 3),
            )
        )

    if not gaps:
        return ActivityDiagnostics()

    ranked = sorted(gaps, key=lambda gap: gap.DurationSeconds, reverse=True)
    largest = ranked[0].DurationSeconds
    excess = round(sum(gap.ExcessSeconds for gap in gaps), 3)

    return ActivityDiagnostics(
        GapCount=len(gaps),
        LargestGapSeconds=largest,
        ExcessGapSeconds=excess,
        Gaps=tuple(ranked[: max(0, int(limit))]),
    )


def _build_snapshot_with_activity_analysis(self, *args, **kwargs):
    assert _ORIGINAL_BUILD_SNAPSHOT is not None
    snapshot = _ORIGINAL_BUILD_SNAPSHOT(self, *args, **kwargs)

    snapshot.ObservedActionGapCount = 0
    snapshot.ObservedLargestActionGapSeconds = None
    snapshot.ObservedActionGapExcessSeconds = 0.0
    snapshot.ObservedActionGaps = ()
    snapshot.ActivityGapThresholdSeconds = _GAP_THRESHOLD_MS / 1000.0
    snapshot.ActivityAnalysisNote = ""

    if str(getattr(snapshot, "Role", "")).casefold() != "dps":
        return snapshot

    timestamps = tuple(
        getattr(snapshot, "WeaveEligibleSkillTimestampsMs", ()) or ()
    )
    diagnostics = _analyze_action_gaps(timestamps)

    snapshot.ObservedActionGapCount = diagnostics.GapCount
    snapshot.ObservedLargestActionGapSeconds = diagnostics.LargestGapSeconds
    snapshot.ObservedActionGapExcessSeconds = diagnostics.ExcessGapSeconds
    snapshot.ObservedActionGaps = diagnostics.Gaps

    if len(timestamps) < 2:
        snapshot.ActivityAnalysisNote = (
            "Fewer than two eligible combat-skill casts were available for internal action-gap analysis."
        )
    else:
        snapshot.ActivityAnalysisNote = (
            "Internal eligible-skill intervals only; pull-start and fight-end silence are excluded. "
            "Exact mechanic or boss-immunity window boundaries are not available here, so these are observed gaps, not graded dead time."
        )

    return snapshot


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_SNAPSHOT
    if _INSTALLED:
        return

    from services.performance_dashboard_service import PerformanceDashboardService

    _ORIGINAL_BUILD_SNAPSHOT = PerformanceDashboardService.build_snapshot
    PerformanceDashboardService.build_snapshot = _build_snapshot_with_activity_analysis
    _INSTALLED = True

    # The final DD layer compares observed personal gaps with raid-wide damage.
    # That provides context without pretending a quiet interval proves a mechanic
    # or an active interval proves player error.
    from services.performance_dd_gap_context_support import install as install_gap_context_support

    install_gap_context_support()
