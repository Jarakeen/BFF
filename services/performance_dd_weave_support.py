from __future__ import annotations

"""Observed light-attack pairing diagnostics for DD Performance Dashboard tabs.

This module intentionally reports *observed LA pairing*, not a universal ESO
"weave score". ESO Logs cast timing is enough to answer a narrower and useful
question: how often did a Light Attack cast occur immediately before a combat
skill cast? That avoids pretending every class, channel, ultimate, synergy, or
mechanics interruption obeys one idealized cadence.

Numeric ability IDs are report-local correlation keys only. Readable ability
names come from the same report's Casts table and numeric IDs are never persisted
as canonical skill identity.
"""

import json
from dataclasses import dataclass
from statistics import median

from services.performance_dd_analysis_support import _decode_event_data

_INSTALLED = False
_ORIGINAL_BUILD_SNAPSHOT = None
_EVENT_PAGE_LIMIT = 10000
_EVENT_PAGE_CAP = 12
_PAIR_WINDOW_MS = 1200.0

_LIGHT_ATTACK_NAMES = {
    "light attack",
}

# Cast tables can contain actions that are real player inputs but are not normal
# rotation skill opportunities. Do not count those as "missed weaves".
_UTILITY_CAST_NAMES = {
    "bash",
    "break free",
    "dodge roll",
    "roll dodge",
    "weapon swap",
}


@dataclass(frozen=True)
class WeaveDiagnostics:
    LightAttackCasts: int = 0
    SkillCasts: int = 0
    PairedSkillCasts: int = 0
    PairingPercent: float | None = None
    MedianPairDelayMs: float | None = None
    UnpairedSkillCasts: int = 0


def _decode_cast_event_data(raw) -> list[dict]:
    """Keep the same tolerant JSON-scalar behavior as damage-event support."""
    return _decode_event_data(raw)


def _entry_log_ability_id(entry: dict) -> int | None:
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


def _fetch_cast_events(
    client,
    report_code: str,
    fight_id: int,
    start_time: float,
    end_time: float,
    actor_id: int,
) -> list[dict]:
    """Fetch actor cast events, following ESO Logs pagination."""

    query = """
    query PerformanceDdCastEvents(
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
            dataType: Casts
            hostilityType: Friendlies
            sourceID: $sourceID
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
        events.extend(_decode_cast_event_data(paginator.get("data")))

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


def _normalized_name(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _is_light_attack_name(name: str) -> bool:
    return _normalized_name(name) in _LIGHT_ATTACK_NAMES


def _is_rotation_skill_name(name: str) -> bool:
    normalized = _normalized_name(name)
    if not normalized or normalized in _LIGHT_ATTACK_NAMES:
        return False
    if normalized in _UTILITY_CAST_NAMES:
        return False
    if "heavy attack" in normalized:
        return False
    if "synergy" in normalized:
        return False
    return True


def _dedupe_cast_events(events: list[dict]) -> list[dict]:
    """Deduplicate repeated cast rows, preferring castTrackID when available."""

    seen: set[tuple] = set()
    result: list[dict] = []

    for event in sorted(events, key=lambda row: float(row.get("timestamp", 0.0) or 0.0)):
        cast_track = event.get("castTrackID")
        ability_id = _event_log_ability_id(event)
        try:
            timestamp = float(event.get("timestamp"))
        except (TypeError, ValueError):
            continue

        if cast_track is not None:
            key = ("track", cast_track)
        else:
            key = ("fallback", timestamp, ability_id, str(event.get("type", "")))

        if key in seen:
            continue
        seen.add(key)
        result.append(event)

    return result


def _analyze_weave_pairing(
    events: list[dict],
    ability_names_by_log_id: dict[int, str],
    pair_window_ms: float = _PAIR_WINDOW_MS,
) -> WeaveDiagnostics:
    """Pair each eligible skill with the nearest unused preceding Light Attack.

    Pairing is local to casts, so long periods of mechanics downtime are not
    automatically counted as misses. A Light Attack can satisfy at most one
    skill cast. This is intentionally an execution observation, not a class-
    specific optimal-rotation judgment.
    """

    casts: list[tuple[float, int, str]] = []
    for event in _dedupe_cast_events(events):
        ability_id = _event_log_ability_id(event)
        if ability_id is None:
            continue
        name = str(ability_names_by_log_id.get(ability_id, "")).strip()
        if not name:
            continue
        try:
            timestamp = float(event.get("timestamp"))
        except (TypeError, ValueError):
            continue
        casts.append((timestamp, ability_id, name))

    light_attacks = [(ts, ability_id) for ts, ability_id, name in casts if _is_light_attack_name(name)]
    skill_casts = [(ts, ability_id, name) for ts, ability_id, name in casts if _is_rotation_skill_name(name)]

    used_light_attack_indices: set[int] = set()
    pair_delays: list[float] = []

    for skill_ts, _skill_id, _skill_name in skill_casts:
        best_index: int | None = None
        best_delay: float | None = None

        for index, (la_ts, _la_id) in enumerate(light_attacks):
            if index in used_light_attack_indices:
                continue
            delay = skill_ts - la_ts
            if delay < 0 or delay > pair_window_ms:
                continue
            if best_delay is None or delay < best_delay:
                best_delay = delay
                best_index = index

        if best_index is not None and best_delay is not None:
            used_light_attack_indices.add(best_index)
            pair_delays.append(best_delay)

    skill_count = len(skill_casts)
    paired = len(pair_delays)
    pairing_percent = round((paired / skill_count) * 100.0, 1) if skill_count else None
    median_delay = round(float(median(pair_delays)), 1) if pair_delays else None

    return WeaveDiagnostics(
        LightAttackCasts=len(light_attacks),
        SkillCasts=skill_count,
        PairedSkillCasts=paired,
        PairingPercent=pairing_percent,
        MedianPairDelayMs=median_delay,
        UnpairedSkillCasts=max(0, skill_count - paired),
    )


def _build_snapshot_with_weave_analysis(self, *args, **kwargs):
    assert _ORIGINAL_BUILD_SNAPSHOT is not None
    snapshot = _ORIGINAL_BUILD_SNAPSHOT(self, *args, **kwargs)

    snapshot.WeavePairingPercent = None
    snapshot.WeaveLightAttackCasts = 0
    snapshot.WeaveSkillCasts = 0
    snapshot.WeavePairedSkillCasts = 0
    snapshot.WeaveUnpairedSkillCasts = 0
    snapshot.WeaveMedianPairDelayMs = None
    snapshot.WeaveAnalysisNote = ""

    if str(getattr(snapshot, "Role", "")).casefold() != "dps":
        return snapshot

    try:
        fight = self.capability_service.fetch_fight_summary(
            snapshot.ReportCode, int(snapshot.FightId)
        )
        start = float(fight["start_time"])
        end = float(fight["end_time"])
        actor_id = int(snapshot.ActorId)

        cast_entries, _total = self.client.get_actor_table(
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            data_type="Casts",
            hostility_type="Friendlies",
            source_id=actor_id,
            view_by="Ability",
        )

        names_by_id: dict[int, str] = {}
        for entry in cast_entries:
            if not isinstance(entry, dict):
                continue
            ability_id = _entry_log_ability_id(entry)
            name = str(entry.get("name", "")).strip()
            if ability_id is not None and name:
                names_by_id[ability_id] = name

        events = _fetch_cast_events(
            self.client,
            snapshot.ReportCode,
            int(snapshot.FightId),
            start,
            end,
            actor_id,
        )

        diagnostics = _analyze_weave_pairing(events, names_by_id)
        snapshot.WeavePairingPercent = diagnostics.PairingPercent
        snapshot.WeaveLightAttackCasts = diagnostics.LightAttackCasts
        snapshot.WeaveSkillCasts = diagnostics.SkillCasts
        snapshot.WeavePairedSkillCasts = diagnostics.PairedSkillCasts
        snapshot.WeaveUnpairedSkillCasts = diagnostics.UnpairedSkillCasts
        snapshot.WeaveMedianPairDelayMs = diagnostics.MedianPairDelayMs

        if diagnostics.PairingPercent is None:
            snapshot.WeaveAnalysisNote = (
                "No eligible combat-skill casts were available for observed Light Attack pairing analysis."
            )
        elif diagnostics.LightAttackCasts == 0:
            snapshot.WeaveAnalysisNote = (
                "No report-local cast named Light Attack was observed for this actor."
            )
    except Exception as exc:
        snapshot.WeaveAnalysisNote = f"Observed Light Attack pairing analysis unavailable: {exc}"

    return snapshot


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_SNAPSHOT
    if _INSTALLED:
        return

    from services.performance_dashboard_service import PerformanceDashboardService

    _ORIGINAL_BUILD_SNAPSHOT = PerformanceDashboardService.build_snapshot
    PerformanceDashboardService.build_snapshot = _build_snapshot_with_weave_analysis
    _INSTALLED = True
