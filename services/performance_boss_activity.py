from __future__ import annotations

"""Exact boss damageable windows for the Performance Dashboard.

Aggregate immunity uptime can tell us how long the boss was unavailable, but it
cannot tell us *when*.  This module uses the configured immunity aura's own
apply/refresh/remove events to reconstruct immune windows, then inverts those
windows into boss-active spans suitable for graph background shading.

No timing is invented.  If exact immunity events are unavailable, callers get
no active windows and can continue using aggregate BossActiveSeconds only.
"""

from dataclasses import dataclass

from services.esologs_client import EsoLogsClient
from services.performance_effect_timeline import (
    PerformanceEffectTimelineService,
    build_effect_windows,
)


@dataclass(frozen=True)
class BossActiveWindow:
    StartSeconds: float
    EndSeconds: float


def _merge_intervals(
    intervals: list[tuple[float, float]],
    *,
    duration_seconds: float,
) -> list[tuple[float, float]]:
    clipped = sorted(
        (
            max(0.0, min(duration_seconds, float(start))),
            max(0.0, min(duration_seconds, float(end))),
        )
        for start, end in intervals
        if float(end) > float(start)
    )

    merged: list[list[float]] = []
    for start, end in clipped:
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def invert_immune_windows(
    immune_windows: list[tuple[float, float]],
    *,
    duration_seconds: float,
) -> list[BossActiveWindow]:
    """Return the complement of exact immune windows across one fight."""
    duration = max(0.0, float(duration_seconds))
    if duration <= 0:
        return []

    immune = _merge_intervals(immune_windows, duration_seconds=duration)
    if not immune:
        return [BossActiveWindow(0.0, duration)]

    active: list[BossActiveWindow] = []
    cursor = 0.0
    for start, end in immune:
        if start > cursor:
            active.append(BossActiveWindow(cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        active.append(BossActiveWindow(cursor, duration))
    return active


class PerformanceBossActivityService:
    def __init__(self, client: EsoLogsClient):
        self.client = client

    def fetch_active_windows(
        self,
        report_code: str,
        fight_id: int,
        start_ms: float,
        end_ms: float,
        immunity_name: str,
        immunity_kind: str = "Buff",
    ) -> list[BossActiveWindow]:
        name = str(immunity_name or "").strip()
        if not name:
            return []

        data_type = "Debuffs" if str(immunity_kind).casefold() == "debuff" else "Buffs"
        auras = self.client.get_aura_table(
            report_code,
            fight_id,
            start_ms,
            end_ms,
            data_type=data_type,
            hostility_type="Enemies",
        )

        target_key = name.casefold()
        id_to_name: dict[int, str] = {}
        for aura in auras:
            if not isinstance(aura, dict):
                continue
            aura_name = str(aura.get("name") or "").strip()
            if aura_name.casefold() != target_key:
                continue
            raw_id = aura.get("guid", aura.get("abilityGameID"))
            try:
                id_to_name[int(raw_id)] = aura_name
            except (TypeError, ValueError):
                continue

        if not id_to_name:
            return []

        timeline = PerformanceEffectTimelineService(self.client)
        events = timeline._fetch_events(
            report_code,
            fight_id,
            start_ms,
            end_ms,
            data_type=data_type,
            hostility_type="Enemies",
        )
        immune = build_effect_windows(
            events,
            id_to_name=id_to_name,
            fight_start_ms=start_ms,
            fight_end_ms=end_ms,
            source_label="Boss Immunity",
            choose_primary_target=True,
        )

        duration_seconds = max(0.0, (float(end_ms) - float(start_ms)) / 1000.0)
        return invert_immune_windows(
            [(row.StartSeconds, row.EndSeconds) for row in immune],
            duration_seconds=duration_seconds,
        )
