from __future__ import annotations

"""Evidence-first healer diagnostics for the Performance Dashboard.

This layer adds healer-specific observations without grading HPS as a universal
performance score. It reports healing critical rate, observed HoT coverage,
response timing around comparatively large raid damage events, and internal
support-action gaps. Numeric ESO Logs ability IDs are report-local correlation
keys only and are never persisted as canonical skill identity.

The response analysis is deliberately conservative: a selected damage event is
only "precovered" when this healer has a periodic-healing tick on the same target
shortly beforehand, and "responded" when a healing event from this healer lands
on that target shortly afterward. Missing evidence is not labelled a healer
mistake because another healer, target death, mechanics, range, or assignment can
explain it.
"""

from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from models.performance_model import AbilityUptime
from services.performance_dd_activity_support import _analyze_action_gaps
from services.performance_dd_analysis_support import _decode_event_data
from services.performance_dd_dot_support import (
    _coverage_seconds_from_ticks,
    _entry_log_ability_id,
    _event_log_ability_id,
)
from services.performance_dd_weave_support import _dedupe_cast_events

_INSTALLED = False
_ORIGINAL_BUILD_SNAPSHOT = None
_EVENT_PAGE_LIMIT = 10000
_EVENT_PAGE_CAP = 12
_TOP_HOT_COUNT = 8
_RESPONSE_WINDOW_MS = 1500.0
_PRE_COVERAGE_WINDOW_MS = 1500.0
_SUPPORT_GAP_THRESHOLD_MS = 3000.0
_DAMAGE_SAMPLE_LIMIT = 30


@dataclass(frozen=True)
class HealerResponseDiagnostics:
    SelectedDamageEvents: int = 0
    PrecoveredEvents: int = 0
    RespondedEvents: int = 0
    UnansweredEvents: int = 0
    MedianResponseMs: float | None = None
    LargestResponseMs: float | None = None


def _critical_rate_percent(total_events: int, critical_events: int) -> float | None:
    if total_events <= 0:
        return None
    critical_events = max(0, min(int(critical_events), int(total_events)))
    return round((critical_events / total_events) * 100.0, 1)


def _fetch_events(
    client,
    report_code: str,
    fight_id: int,
    start_time: float,
    end_time: float,
    *,
    data_type: str,
    source_id: int | None = None,
    filter_expression: str = "",
) -> list[dict]:
    """Fetch paginated ESO Logs events for one fixed, validated data type."""

    allowed = {"Healing", "DamageTaken", "Casts"}
    if data_type not in allowed:
        raise ValueError(f"unsupported healer event data type: {data_type}")

    query = f"""
    query PerformanceHealerEvents(
      $code: String!
      $fightIDs: [Int]!
      $startTime: Float!
      $endTime: Float!
      $sourceID: Int
      $filterExpression: String!
      $limit: Int!
    ) {{
      reportData {{
        report(code: $code) {{
          events(
            fightIDs: $fightIDs
            startTime: $startTime
            endTime: $endTime
            dataType: {data_type}
            hostilityType: Friendlies
            sourceID: $sourceID
            filterExpression: $filterExpression
            limit: $limit
          ) {{
            data
            nextPageTimestamp
          }}
        }}
      }}
    }}
    """

    code = client.normalize_report_code(report_code)
    cursor = float(start_time)
    events: list[dict] = []

    for _ in range(_EVENT_PAGE_CAP):
        data = client._query(
            query,
            {
                "code": code,
                "fightIDs": [int(fight_id)],
                "startTime": cursor,
                "endTime": float(end_time),
                "sourceID": int(source_id) if source_id is not None else None,
                "filterExpression": str(filter_expression or ""),
                "limit": _EVENT_PAGE_LIMIT,
            },
        )
        report = (data.get("reportData") or {}).get("report") or {}
        paginator = report.get("events") or {}
        events.extend(_decode_event_data(paginator.get("data")))

        next_timestamp = paginator.get("nextPageTimestamp")
        if next_timestamp is None:
            break
        try:
            next_timestamp = float(next_timestamp)
        except (TypeError, ValueError):
            break
        if next_timestamp <= cursor or next_timestamp >= float(end_time):
            break
        cursor = next_timestamp

    return events


def _observed_hot_uptimes(
    periodic_heal_events: list[dict],
    ability_names_by_log_id: dict[int, str],
    fight_start_ms: float,
    fight_end_ms: float,
    denominator_seconds: float,
    limit: int = _TOP_HOT_COUNT,
) -> list[AbilityUptime]:
    """Estimate observed periodic-healing coverage from real tick timestamps."""

    ticks_by_name: dict[str, list[float]] = defaultdict(list)
    for event in periodic_heal_events:
        log_id = _event_log_ability_id(event)
        if log_id is None:
            continue
        name = str(ability_names_by_log_id.get(log_id, "")).strip()
        if not name:
            continue
        try:
            timestamp = float(event.get("timestamp"))
        except (TypeError, ValueError):
            continue
        ticks_by_name[name].append(timestamp)

    rows: list[AbilityUptime] = []
    for name, timestamps in ticks_by_name.items():
        coverage = _coverage_seconds_from_ticks(
            timestamps,
            fight_start_ms=fight_start_ms,
            fight_end_ms=fight_end_ms,
        )
        if coverage <= 0:
            continue
        pct = (coverage / denominator_seconds * 100.0) if denominator_seconds > 0 else 0.0
        rows.append(
            AbilityUptime(
                Name=name,
                UptimeSeconds=coverage,
                UptimePercent=round(min(100.0, max(0.0, pct)), 1),
            )
        )

    rows.sort(key=lambda row: row.UptimeSeconds, reverse=True)
    return rows[: max(0, int(limit))]


def _event_amount(event: dict) -> float:
    try:
        return max(0.0, float(event.get("amount", 0.0) or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _select_high_damage_events(
    events: list[dict],
    limit: int = _DAMAGE_SAMPLE_LIMIT,
) -> list[dict]:
    """Select the upper quartile of observed raid damage events, capped by limit.

    This is an evidence-relative sample, not a claim about a universal dangerous
    damage threshold. Health pools and encounter assignments are not inferred.
    """

    usable = [event for event in events if _event_amount(event) > 0]
    if not usable:
        return []

    amounts = sorted(_event_amount(event) for event in usable)
    quartile_index = int(round((len(amounts) - 1) * 0.75))
    threshold = amounts[quartile_index]
    selected = [event for event in usable if _event_amount(event) >= threshold]
    selected.sort(key=lambda event: _event_amount(event), reverse=True)
    selected = selected[: max(0, int(limit))]
    selected.sort(key=lambda event: float(event.get("timestamp", 0.0) or 0.0))
    return selected


def _target_id(event: dict) -> int | None:
    for key in ("targetID", "targetId", "target_id"):
        value = event.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _timestamp_ms(event: dict) -> float | None:
    try:
        return float(event.get("timestamp"))
    except (TypeError, ValueError):
        return None


def _analyze_healer_response(
    damage_events: list[dict],
    healing_events: list[dict],
    periodic_heal_events: list[dict],
    *,
    response_window_ms: float = _RESPONSE_WINDOW_MS,
    precoverage_window_ms: float = _PRE_COVERAGE_WINDOW_MS,
) -> HealerResponseDiagnostics:
    if response_window_ms <= 0 or precoverage_window_ms < 0:
        raise ValueError("response windows must be positive")

    selected = _select_high_damage_events(damage_events)
    if not selected:
        return HealerResponseDiagnostics()

    heals_by_target: dict[int, list[float]] = defaultdict(list)
    ticks_by_target: dict[int, list[float]] = defaultdict(list)

    for event in healing_events:
        target = _target_id(event)
        timestamp = _timestamp_ms(event)
        if target is not None and timestamp is not None:
            heals_by_target[target].append(timestamp)

    for event in periodic_heal_events:
        target = _target_id(event)
        timestamp = _timestamp_ms(event)
        if target is not None and timestamp is not None:
            ticks_by_target[target].append(timestamp)

    for values in heals_by_target.values():
        values.sort()
    for values in ticks_by_target.values():
        values.sort()

    precovered = responded = unanswered = 0
    response_delays: list[float] = []

    for damage in selected:
        target = _target_id(damage)
        timestamp = _timestamp_ms(damage)
        if target is None or timestamp is None:
            unanswered += 1
            continue

        had_precoverage = any(
            timestamp - precoverage_window_ms <= tick <= timestamp
            for tick in ticks_by_target.get(target, ())
        )
        if had_precoverage:
            precovered += 1

        future = [
            heal - timestamp
            for heal in heals_by_target.get(target, ())
            if timestamp <= heal <= timestamp + response_window_ms
        ]
        if future:
            delay = min(future)
            responded += 1
            response_delays.append(delay)
        elif not had_precoverage:
            unanswered += 1

    return HealerResponseDiagnostics(
        SelectedDamageEvents=len(selected),
        PrecoveredEvents=precovered,
        RespondedEvents=responded,
        UnansweredEvents=unanswered,
        MedianResponseMs=round(float(median(response_delays)), 1) if response_delays else None,
        LargestResponseMs=round(max(response_delays), 1) if response_delays else None,
    )


def _support_cast_timestamps(
    cast_events: list[dict],
    ability_names_by_log_id: dict[int, str],
) -> tuple[float, ...]:
    """Return timestamps for meaningful healer actions, including heavy/synergy use."""

    excluded = {"light attack", "weapon swap", "break free", "dodge roll", "roll dodge"}
    timestamps: list[float] = []

    for event in _dedupe_cast_events(cast_events):
        ability_id = _event_log_ability_id(event)
        if ability_id is None:
            continue
        name = " ".join(str(ability_names_by_log_id.get(ability_id, "")).casefold().split())
        if not name or name in excluded:
            continue
        timestamp = _timestamp_ms(event)
        if timestamp is not None:
            timestamps.append(timestamp)

    return tuple(sorted(set(timestamps)))


def _build_snapshot_with_healer_analysis(self, *args, **kwargs):
    assert _ORIGINAL_BUILD_SNAPSHOT is not None
    snapshot = _ORIGINAL_BUILD_SNAPSHOT(self, *args, **kwargs)

    snapshot.HealerCritRatePercent = None
    snapshot.HealerCriticalEvents = 0
    snapshot.HealerHealingEvents = 0
    snapshot.ObservedHotUptimes = []
    snapshot.HealerResponseSelectedEvents = 0
    snapshot.HealerPrecoveredEvents = 0
    snapshot.HealerRespondedEvents = 0
    snapshot.HealerUnansweredEvents = 0
    snapshot.HealerMedianResponseMs = None
    snapshot.HealerLargestResponseMs = None
    snapshot.HealerSupportCastCount = 0
    snapshot.HealerSupportGapCount = 0
    snapshot.HealerLargestSupportGapSeconds = None
    snapshot.HealerSupportGapExcessSeconds = 0.0
    snapshot.HealerSupportGapThresholdSeconds = _SUPPORT_GAP_THRESHOLD_MS / 1000.0
    snapshot.HealerAnalysisNote = ""

    if str(getattr(snapshot, "Role", "")).casefold() != "healer":
        return snapshot

    try:
        fight = self.capability_service.fetch_fight_summary(
            snapshot.ReportCode, int(snapshot.FightId)
        )
        start = float(fight["start_time"])
        end = float(fight["end_time"])
        actor_id = int(snapshot.ActorId)

        healing_entries, _total = self.client.get_actor_table(
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="Healing",
            hostility_type="Friendlies",
            source_id=actor_id,
            view_by="Ability",
        )
        healing_names: dict[int, str] = {}
        for entry in healing_entries:
            if not isinstance(entry, dict):
                continue
            ability_id = _entry_log_ability_id(entry)
            name = str(entry.get("name", "")).strip()
            if ability_id is not None and name:
                healing_names[ability_id] = name

        healing_events = _fetch_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="Healing",
            source_id=actor_id,
            filter_expression='type = "heal"',
        )
        critical_events = _fetch_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="Healing",
            source_id=actor_id,
            filter_expression='type = "heal" AND isCritical = true',
        )
        periodic_events = _fetch_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="Healing",
            source_id=actor_id,
            filter_expression='type = "heal" AND isTick = true',
        )

        snapshot.HealerHealingEvents = len(healing_events)
        snapshot.HealerCriticalEvents = len(critical_events)
        snapshot.HealerCritRatePercent = _critical_rate_percent(
            len(healing_events), len(critical_events)
        )
        snapshot.ObservedHotUptimes = _observed_hot_uptimes(
            periodic_events,
            healing_names,
            fight_start_ms=start,
            fight_end_ms=end,
            denominator_seconds=float(snapshot.FightDurationSeconds),
        )

        raid_damage_events = _fetch_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="DamageTaken",
            source_id=None,
            filter_expression='type = "damage"',
        )
        response = _analyze_healer_response(
            raid_damage_events,
            healing_events,
            periodic_events,
        )
        snapshot.HealerResponseSelectedEvents = response.SelectedDamageEvents
        snapshot.HealerPrecoveredEvents = response.PrecoveredEvents
        snapshot.HealerRespondedEvents = response.RespondedEvents
        snapshot.HealerUnansweredEvents = response.UnansweredEvents
        snapshot.HealerMedianResponseMs = response.MedianResponseMs
        snapshot.HealerLargestResponseMs = response.LargestResponseMs

        cast_entries, _cast_total = self.client.get_actor_table(
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="Casts",
            hostility_type="Friendlies",
            source_id=actor_id,
            view_by="Ability",
        )
        cast_names: dict[int, str] = {}
        for entry in cast_entries:
            if not isinstance(entry, dict):
                continue
            ability_id = _entry_log_ability_id(entry)
            name = str(entry.get("name", "")).strip()
            if ability_id is not None and name:
                cast_names[ability_id] = name

        cast_events = _fetch_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="Casts",
            source_id=actor_id,
            filter_expression="",
        )
        support_timestamps = _support_cast_timestamps(cast_events, cast_names)
        snapshot.HealerSupportCastCount = len(support_timestamps)
        gaps = _analyze_action_gaps(
            support_timestamps,
            threshold_ms=_SUPPORT_GAP_THRESHOLD_MS,
        )
        snapshot.HealerSupportGapCount = gaps.GapCount
        snapshot.HealerLargestSupportGapSeconds = gaps.LargestGapSeconds
        snapshot.HealerSupportGapExcessSeconds = gaps.ExcessGapSeconds

        snapshot.HealerAnalysisNote = (
            "Observed healer evidence only. HoT coverage is inferred from periodic-healing ticks; "
            "response timing uses the upper quartile of observed raid damage events; support gaps "
            "are internal cast intervals and are not graded as mistakes."
        )
    except Exception as exc:
        snapshot.HealerAnalysisNote = f"Healer diagnostics unavailable: {exc}"

    return snapshot


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_SNAPSHOT
    if _INSTALLED:
        return

    from services.performance_dashboard_service import PerformanceDashboardService

    _ORIGINAL_BUILD_SNAPSHOT = PerformanceDashboardService.build_snapshot
    PerformanceDashboardService.build_snapshot = _build_snapshot_with_healer_analysis
    _INSTALLED = True
