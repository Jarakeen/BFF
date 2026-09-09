from __future__ import annotations

"""Observed DoT activity diagnostics for DD Performance Dashboard tabs.

ESO Logs exposes periodic damage through the event filter predicate ``isTick``.
This support layer uses those periodic-damage events only. It deliberately does
not treat ESO numeric ability IDs as canonical skill identity: IDs are used only
inside one fetched report to correlate tick events with the readable ability
names already returned by that report's DamageDone table.

The resulting percentage is labelled *observed DoT uptime*. It is an event-
coverage estimate built from real periodic ticks, not a claim that we know an
ability's canonical duration. Long gaps split activity into separate windows.
"""

from collections import defaultdict
from statistics import median

from models.performance_model import AbilityUptime
from services.performance_dd_analysis_support import _decode_event_data

_INSTALLED = False
_ORIGINAL_BUILD_SNAPSHOT = None
_EVENT_PAGE_LIMIT = 10000
_EVENT_PAGE_CAP = 12
_TOP_DOT_COUNT = 8


def _entry_log_ability_id(entry: dict) -> int | None:
    """Return a report-local ability id for correlation only, never persistence."""

    for key in ("guid", "abilityGameID", "id"):
        value = entry.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _event_log_ability_id(event: dict) -> int | None:
    for key in ("abilityGameID", "guid", "abilityID"):
        value = event.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _fetch_periodic_damage_events(
    client,
    report_code: str,
    fight_id: int,
    start_time: float,
    end_time: float,
    actor_id: int,
) -> list[dict]:
    """Fetch all player periodic-damage events, following ESO Logs pagination."""

    query = """
    query PerformanceDdDotEvents(
      $code: String!
      $fightIDs: [Int]!
      $startTime: Float!
      $endTime: Float!
      $sourceID: Int!
      $limit: Int!
    ) {
      reportData {
        report(code: $code) {
          events(
            fightIDs: $fightIDs
            startTime: $startTime
            endTime: $endTime
            dataType: DamageDone
            hostilityType: Friendlies
            sourceID: $sourceID
            filterExpression: "type = \"damage\" AND isTick = true"
            limit: $limit
          ) {
            data
            nextPageTimestamp
          }
        }
      }
    }
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
                "sourceID": int(actor_id),
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


def _coverage_seconds_from_ticks(
    timestamps_ms: list[float],
    fight_start_ms: float,
    fight_end_ms: float,
) -> float:
    """Estimate observed periodic-activity coverage from real tick timestamps.

    A cadence is inferred from the median positive inter-tick gap. Each tick
    contributes one cadence of coverage. Gaps larger than 2.5 cadences naturally
    leave uncovered space, so target swaps/deaths/mechanics do not become fake
    continuous DoT uptime. A single isolated tick is not enough evidence to
    estimate uptime and therefore contributes zero seconds.
    """

    ordered = sorted(float(t) for t in timestamps_ms if t is not None)
    if len(ordered) < 2 or fight_end_ms <= fight_start_ms:
        return 0.0

    gaps = [b - a for a, b in zip(ordered, ordered[1:]) if b > a]
    if not gaps:
        return 0.0

    cadence = float(median(gaps))
    if cadence <= 0:
        return 0.0

    max_link_gap = cadence * 2.5
    intervals: list[tuple[float, float]] = []

    segment_start = ordered[0]
    segment_end = min(ordered[0] + cadence, fight_end_ms)

    for previous, current in zip(ordered, ordered[1:]):
        if current - previous <= max_link_gap:
            segment_end = min(current + cadence, fight_end_ms)
            continue

        intervals.append((max(segment_start, fight_start_ms), segment_end))
        segment_start = current
        segment_end = min(current + cadence, fight_end_ms)

    intervals.append((max(segment_start, fight_start_ms), segment_end))

    total_ms = sum(max(0.0, end - start) for start, end in intervals)
    return total_ms / 1000.0


def _observed_dot_uptimes(
    events: list[dict],
    ability_names_by_log_id: dict[int, str],
    fight_start_ms: float,
    fight_end_ms: float,
    denominator_seconds: float,
    limit: int = _TOP_DOT_COUNT,
) -> list[AbilityUptime]:
    """Build readable DoT activity rows without persisting numeric log IDs."""

    ticks_by_name: dict[str, list[float]] = defaultdict(list)

    for event in events:
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
    return rows[:limit]


def _build_snapshot_with_dot_analysis(self, *args, **kwargs):
    assert _ORIGINAL_BUILD_SNAPSHOT is not None
    snapshot = _ORIGINAL_BUILD_SNAPSHOT(self, *args, **kwargs)

    snapshot.ObservedDotUptimes = []
    snapshot.DotAnalysisNote = ""

    if str(getattr(snapshot, "Role", "")).casefold() != "dps":
        return snapshot

    try:
        fight = self.capability_service.fetch_fight_summary(
            snapshot.ReportCode, int(snapshot.FightId)
        )
        start = float(fight["start_time"])
        end = float(fight["end_time"])
        actor_id = int(snapshot.ActorId)

        entries, _total = self.client.get_actor_table(
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="DamageDone",
            hostility_type="Friendlies",
            source_id=actor_id,
            view_by="Ability",
        )

        ability_names_by_log_id: dict[int, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            log_id = _entry_log_ability_id(entry)
            name = str(entry.get("name", "")).strip()
            if log_id is not None and name:
                ability_names_by_log_id[log_id] = name

        events = _fetch_periodic_damage_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            actor_id,
        )

        denominator = (
            float(snapshot.BossActiveSeconds)
            if snapshot.BossActiveSeconds is not None
            else float(snapshot.FightDurationSeconds)
        )
        snapshot.ObservedDotUptimes = _observed_dot_uptimes(
            events,
            ability_names_by_log_id,
            fight_start_ms=start,
            fight_end_ms=end,
            denominator_seconds=denominator,
        )

        if not snapshot.ObservedDotUptimes:
            snapshot.DotAnalysisNote = (
                "No periodic-damage abilities had enough report-local tick evidence "
                "to estimate observed DoT uptime."
            )
    except Exception as exc:
        snapshot.DotAnalysisNote = f"Observed DoT analysis unavailable: {exc}"

    return snapshot


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_SNAPSHOT
    if _INSTALLED:
        return

    from services.performance_dashboard_service import PerformanceDashboardService

    _ORIGINAL_BUILD_SNAPSHOT = PerformanceDashboardService.build_snapshot
    PerformanceDashboardService.build_snapshot = _build_snapshot_with_dot_analysis
    _INSTALLED = True

    # Keep the DD stack contiguous: crit -> observed DoT -> observed LA pairing.
    # Every layer is additive and read-only with respect to the local ESO database.
    from services.performance_dd_weave_support import install as install_weave_support

    install_weave_support()
