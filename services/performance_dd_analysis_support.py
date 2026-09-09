from __future__ import annotations

"""Event-backed DD diagnostics for the Performance Dashboard.

The existing PerformanceDashboardService already provides total damage, DPS,
output-over-time, buff/debuff uptime, and per-ability damage. This support layer
adds one deliberately narrow DD diagnostic that is mechanically meaningful and
backed by ESO Logs' event query language: overall damage-event critical rate.

ESO Logs documents ``isCritical`` as a damage/heal event predicate and supports
filterExpression on report events. We count all damage events and critical
damage events separately instead of guessing from table payload fields that may
change shape.
"""

import json

_INSTALLED = False
_ORIGINAL_BUILD_SNAPSHOT = None
_EVENT_PAGE_LIMIT = 10000
_EVENT_PAGE_CAP = 12


def _decode_event_data(raw) -> list[dict]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    return [event for event in raw if isinstance(event, dict)]


def _count_filtered_damage_events(
    client,
    report_code: str,
    fight_id: int,
    start_time: float,
    end_time: float,
    actor_id: int,
    filter_expression: str,
) -> int:
    """Count matching player damage events, following ESO Logs pagination."""

    query = """
    query PerformanceDdEvents(
      $code: String!
      $fightIDs: [Int]!
      $startTime: Float!
      $endTime: Float!
      $sourceID: Int!
      $filterExpression: String!
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
            filterExpression: $filterExpression
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
    total = 0

    for _ in range(_EVENT_PAGE_CAP):
        data = client._query(
            query,
            {
                "code": code,
                "fightIDs": [int(fight_id)],
                "startTime": cursor,
                "endTime": float(end_time),
                "sourceID": int(actor_id),
                "filterExpression": filter_expression,
                "limit": _EVENT_PAGE_LIMIT,
            },
        )
        report = (data.get("reportData") or {}).get("report") or {}
        paginator = report.get("events") or {}
        events = _decode_event_data(paginator.get("data"))
        total += len(events)

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

    return total


def _critical_rate_percent(total_hits: int, critical_hits: int) -> float | None:
    if total_hits <= 0:
        return None
    critical_hits = max(0, min(int(critical_hits), int(total_hits)))
    return round((critical_hits / total_hits) * 100.0, 1)


def _build_snapshot_with_dd_analysis(self, *args, **kwargs):
    assert _ORIGINAL_BUILD_SNAPSHOT is not None
    snapshot = _ORIGINAL_BUILD_SNAPSHOT(self, *args, **kwargs)

    snapshot.CritRatePercent = None
    snapshot.CriticalDamageEvents = 0
    snapshot.DamageHitEvents = 0
    snapshot.DdAnalysisNote = ""

    if str(getattr(snapshot, "Role", "")).casefold() != "dps":
        return snapshot

    try:
        fight = self.capability_service.fetch_fight_summary(
            snapshot.ReportCode, int(snapshot.FightId)
        )
        start = float(fight["start_time"])
        end = float(fight["end_time"])
        actor_id = int(snapshot.ActorId)

        total_hits = _count_filtered_damage_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            actor_id,
            'type = "damage"',
        )
        critical_hits = _count_filtered_damage_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            actor_id,
            'type = "damage" AND isCritical = true',
        )

        snapshot.DamageHitEvents = total_hits
        snapshot.CriticalDamageEvents = critical_hits
        snapshot.CritRatePercent = _critical_rate_percent(total_hits, critical_hits)
        if snapshot.CritRatePercent is None:
            snapshot.DdAnalysisNote = "No qualifying damage events were available for crit analysis."
    except Exception as exc:
        # DD diagnostics are additive. A log/schema/rate-limit problem here must
        # never erase the already-valid base performance snapshot.
        snapshot.DdAnalysisNote = f"Crit analysis unavailable: {exc}"

    return snapshot


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_SNAPSHOT
    if _INSTALLED:
        return

    from services.performance_dashboard_service import PerformanceDashboardService

    _ORIGINAL_BUILD_SNAPSHOT = PerformanceDashboardService.build_snapshot
    PerformanceDashboardService.build_snapshot = _build_snapshot_with_dd_analysis
    _INSTALLED = True

    # Keep DD diagnostics layered in one startup hook. The DoT layer wraps this
    # crit-aware snapshot and likewise never writes to the local ESO database.
    from services.performance_dd_dot_support import install as install_dot_support

    install_dot_support()
