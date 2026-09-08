from __future__ import annotations

"""Build honest time-aligned support-effect windows for Performance Dashboard.

ESO Logs' aura table is excellent for aggregate uptime but cannot answer *when*
an effect was active. This module pairs those aura names/IDs with the report
``events`` stream and reconstructs observed apply/refresh/remove windows.

No mechanics are inferred here. An interval exists only when the combat log has
matching aura events. Open auras at fight end are clipped to the fight boundary
and marked accordingly so the dashboard can draw them without inventing a
mid-fight expiration.
"""

from dataclasses import dataclass
import json
from typing import Any

from services.esologs_client import EsoLogsApiError, EsoLogsClient


TRACKED_SUPPORT_EFFECTS = frozenset(
    name.casefold()
    for name in (
        "Major Brittle",
        "Minor Berserk",
        "Major Courage",
        "Major Slayer",
        "Major Vulnerability",
        "Minor Vulnerability",
        "Major Force",
        "Minor Force",
        "Major Breach",
        "Minor Breach",
        "Off Balance",
        "Major Resolve",
        "Minor Resolve",
        "Major Protection",
        "Minor Protection",
        "Major Mending",
        "Minor Mending",
        "Empower",
    )
)

_APPLY = {"applybuff", "applybuffstack", "applydebuff", "applydebuffstack"}
_REFRESH = {"refreshbuff", "refreshbuffstack", "refreshdebuff", "refreshdebuffstack"}
_REMOVE = {"removebuff", "removebuffstack", "removedebuff", "removedebuffstack"}


@dataclass(frozen=True)
class EffectWindow:
    Name: str
    StartSeconds: float
    EndSeconds: float
    Source: str
    TargetId: int | None = None
    AbilityId: int | None = None
    Confidence: str = "observed_remove"


_EVENT_QUERY = """
query PerformanceAuraEvents(
  $code: String!
  $fightIDs: [Int]!
  $startTime: Float!
  $endTime: Float!
  $dataType: EventDataType
  $hostilityType: HostilityType
  $targetID: Int
  $limit: Int!
) {
  reportData {
    report(code: $code) {
      events(
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        dataType: $dataType
        hostilityType: $hostilityType
        targetID: $targetID
        limit: $limit
        translate: true
        useAbilityIDs: true
        useActorIDs: true
      ) {
        data
        nextPageTimestamp
      }
    }
  }
}
"""


def _scalar(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _ability_id(row: dict[str, Any]) -> int | None:
    for key in ("abilityGameID", "abilityGameId", "abilityID", "abilityId"):
        value = row.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
    ability = row.get("ability")
    if isinstance(ability, dict):
        for key in ("gameID", "gameId", "id", "guid"):
            value = ability.get(key)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
    return None


def _target_id(row: dict[str, Any]) -> int | None:
    value = row.get("targetID", row.get("targetId"))
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _event_type(row: dict[str, Any]) -> str:
    return str(row.get("type") or row.get("eventType") or "").strip().casefold()


def _event_timestamp(row: dict[str, Any]) -> float | None:
    try:
        return float(row.get("timestamp"))
    except (TypeError, ValueError):
        return None


def _effect_ids(auras: list[dict]) -> dict[int, str]:
    """Map tracked aura game IDs to their display names."""
    result: dict[int, str] = {}
    for aura in auras:
        if not isinstance(aura, dict):
            continue
        name = str(aura.get("name") or "").strip()
        if name.casefold() not in TRACKED_SUPPORT_EFFECTS:
            continue
        raw_id = aura.get("guid", aura.get("abilityGameID"))
        try:
            ability_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        result[ability_id] = name
    return result


def _coverage_seconds(windows: list[EffectWindow]) -> float:
    return sum(max(0.0, row.EndSeconds - row.StartSeconds) for row in windows)


def build_effect_windows(
    events: list[dict[str, Any]],
    *,
    id_to_name: dict[int, str],
    fight_start_ms: float,
    fight_end_ms: float,
    source_label: str,
    choose_primary_target: bool = False,
) -> list[EffectWindow]:
    """Reconstruct intervals from raw aura events.

    For raid debuffs, ESO Logs can return the same aura on several enemies. The
    dashboard wants boss coverage rather than a wall of add lanes, so when
    ``choose_primary_target`` is true we retain, per effect, the target with the
    greatest observed coverage. The chosen target ID is kept on every window so
    the inference remains inspectable.
    """
    active: dict[tuple[int, int | None], tuple[float, str]] = {}
    completed: list[EffectWindow] = []

    ordered = sorted(
        (row for row in events if isinstance(row, dict)),
        key=lambda row: _event_timestamp(row) if _event_timestamp(row) is not None else float("inf"),
    )

    for row in ordered:
        ability_id = _ability_id(row)
        if ability_id is None or ability_id not in id_to_name:
            continue
        timestamp = _event_timestamp(row)
        if timestamp is None:
            continue
        kind = _event_type(row)
        target_id = _target_id(row)
        key = (ability_id, target_id)
        name = id_to_name[ability_id]

        if kind in _APPLY:
            if key not in active:
                active[key] = (timestamp, name)
            # A second apply while active is functionally a refresh for coverage.
            continue

        if kind in _REFRESH:
            # Refresh without a visible apply can happen when the query starts in
            # the middle of an already-active aura. Anchor it to the fight start
            # rather than pretending the refresh itself began the coverage.
            active.setdefault(key, (fight_start_ms, name))
            continue

        if kind in _REMOVE:
            started = active.pop(key, None)
            if started is None:
                continue
            start_ms, active_name = started
            if timestamp <= start_ms:
                continue
            completed.append(
                EffectWindow(
                    Name=active_name,
                    StartSeconds=max(0.0, (start_ms - fight_start_ms) / 1000.0),
                    EndSeconds=max(0.0, (timestamp - fight_start_ms) / 1000.0),
                    Source=source_label,
                    TargetId=target_id,
                    AbilityId=ability_id,
                    Confidence="observed_remove",
                )
            )

    for (ability_id, target_id), (start_ms, name) in active.items():
        if fight_end_ms <= start_ms:
            continue
        completed.append(
            EffectWindow(
                Name=name,
                StartSeconds=max(0.0, (start_ms - fight_start_ms) / 1000.0),
                EndSeconds=max(0.0, (fight_end_ms - fight_start_ms) / 1000.0),
                Source=source_label,
                TargetId=target_id,
                AbilityId=ability_id,
                Confidence="open_at_fight_end",
            )
        )

    if not choose_primary_target:
        return sorted(completed, key=lambda row: (row.Name.casefold(), row.StartSeconds))

    by_name_target: dict[tuple[str, int | None], list[EffectWindow]] = {}
    for window in completed:
        by_name_target.setdefault((window.Name.casefold(), window.TargetId), []).append(window)

    chosen: dict[str, tuple[int | None, float]] = {}
    for (name, target_id), windows in by_name_target.items():
        coverage = _coverage_seconds(windows)
        current = chosen.get(name)
        if current is None or coverage > current[1]:
            chosen[name] = (target_id, coverage)

    filtered = [
        window
        for window in completed
        if chosen.get(window.Name.casefold(), (None, 0.0))[0] == window.TargetId
    ]
    return sorted(filtered, key=lambda row: (row.Name.casefold(), row.StartSeconds))


class PerformanceEffectTimelineService:
    def __init__(self, client: EsoLogsClient):
        self.client = client

    def _fetch_events(
        self,
        report_code: str,
        fight_id: int,
        start_ms: float,
        end_ms: float,
        *,
        data_type: str,
        hostility_type: str,
        target_id: int | None = None,
        limit: int = 10_000,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page_start = float(start_ms)

        for _ in range(max_pages):
            data = self.client._query(
                _EVENT_QUERY,
                {
                    "code": self.client.normalize_report_code(report_code),
                    "fightIDs": [int(fight_id)],
                    "startTime": page_start,
                    "endTime": float(end_ms),
                    "dataType": data_type,
                    "hostilityType": hostility_type,
                    "targetID": target_id,
                    "limit": max(100, min(int(limit), 10_000)),
                },
            )
            report = (data.get("reportData") or {}).get("report") or {}
            page = report.get("events") or {}
            data_rows = _scalar(page.get("data")) or []
            if isinstance(data_rows, dict):
                data_rows = [data_rows]
            if isinstance(data_rows, list):
                rows.extend(row for row in data_rows if isinstance(row, dict))
            next_timestamp = page.get("nextPageTimestamp")
            if not next_timestamp or not data_rows:
                break
            try:
                next_value = float(next_timestamp)
            except (TypeError, ValueError):
                break
            if next_value <= page_start or next_value >= float(end_ms):
                break
            page_start = next_value

        return rows

    def fetch_windows(
        self,
        report_code: str,
        fight_id: int,
        actor_id: int,
        start_ms: float,
        end_ms: float,
    ) -> list[EffectWindow]:
        """Fetch tracked buff-on-player and raid-debuff-on-enemy windows."""
        buff_auras = self.client.get_aura_table(
            report_code,
            fight_id,
            start_ms,
            end_ms,
            data_type="Buffs",
            hostility_type="Friendlies",
            target_id=actor_id,
        )
        debuff_auras = self.client.get_aura_table(
            report_code,
            fight_id,
            start_ms,
            end_ms,
            data_type="Debuffs",
            hostility_type="Enemies",
        )
        buff_ids = _effect_ids(buff_auras)
        debuff_ids = _effect_ids(debuff_auras)

        windows: list[EffectWindow] = []
        if buff_ids:
            buff_events = self._fetch_events(
                report_code,
                fight_id,
                start_ms,
                end_ms,
                data_type="Buffs",
                hostility_type="Friendlies",
                target_id=actor_id,
            )
            windows.extend(
                build_effect_windows(
                    buff_events,
                    id_to_name=buff_ids,
                    fight_start_ms=start_ms,
                    fight_end_ms=end_ms,
                    source_label="Your Buff",
                )
            )

        if debuff_ids:
            debuff_events = self._fetch_events(
                report_code,
                fight_id,
                start_ms,
                end_ms,
                data_type="Debuffs",
                hostility_type="Enemies",
            )
            windows.extend(
                build_effect_windows(
                    debuff_events,
                    id_to_name=debuff_ids,
                    fight_start_ms=start_ms,
                    fight_end_ms=end_ms,
                    source_label="Raid-Wide",
                    choose_primary_target=True,
                )
            )

        return sorted(windows, key=lambda row: (row.Name.casefold(), row.StartSeconds))
