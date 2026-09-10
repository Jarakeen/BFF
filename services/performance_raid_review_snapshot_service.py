from __future__ import annotations

"""Lean ESO Logs snapshot collection for Raid Review.

Raid Review does not need the Performance Dashboard's output graph, peak-window text,
or top-ability breakdown for every player on every pull. This service fetches only the
fields consumed by Raid Review and caches fight-level evidence so one pull is not
re-fetched once per raid member.
"""

from models.performance_model import PerformanceSnapshot
from services.performance_dashboard_service import ROLE_OUTPUT, _top_uptimes


class PerformanceRaidReviewSnapshotService:
    """Build fresh review snapshots with minimal per-player ESO Logs traffic."""

    def __init__(self, performance_service) -> None:
        self.performance_service = performance_service
        self.client = performance_service.client
        self._fight_cache: dict[tuple[str, int], dict] = {}
        self._raid_debuff_cache: dict[tuple[str, int, float, float, float], list] = {}

    def build_snapshot(
        self,
        report_code: str,
        fight_id: int,
        actor_id: int,
        actor_label: str,
        role: str,
        *,
        immunity_buff_name: str = "",
        immunity_buff_kind: str = "Buff",
    ) -> PerformanceSnapshot:
        summary = self._fight_summary(report_code, int(fight_id))
        start = float(summary["start_time"])
        end = float(summary["end_time"])
        full_duration = float(summary["duration_seconds"])

        boss_active_seconds = None
        if str(immunity_buff_name or "").strip():
            boss_active_seconds = self.performance_service.capability_service.compute_boss_active_seconds(
                report_code,
                int(fight_id),
                immunity_buff_name,
                immunity_buff_kind,
            )
        uptime_duration = (
            boss_active_seconds
            if boss_active_seconds is not None and boss_active_seconds > 0
            else full_duration
        )

        buff_auras = self.client.get_aura_table(
            report_code,
            int(fight_id),
            start,
            end,
            data_type="Buffs",
            hostility_type="Friendlies",
            target_id=int(actor_id),
        )
        debuff_auras = self.client.get_aura_table(
            report_code,
            int(fight_id),
            start,
            end,
            data_type="Debuffs",
            hostility_type="Enemies",
            source_id=int(actor_id),
        )
        raid_debuff_uptimes = self._raid_debuff_uptimes(
            report_code,
            int(fight_id),
            start,
            end,
            uptime_duration,
        )

        data_type, hostility_type, output_label, rate_label = ROLE_OUTPUT.get(
            role,
            ROLE_OUTPUT["DPS"],
        )
        _entries, total = self.client.get_actor_table(
            report_code,
            int(fight_id),
            start,
            end,
            data_type=data_type,
            hostility_type=hostility_type,
            source_id=int(actor_id),
            view_by="Ability",
        )
        total = float(total or 0.0)

        return PerformanceSnapshot(
            ReportCode=report_code,
            FightId=str(fight_id),
            ActorId=int(actor_id),
            ActorLabel=str(actor_label),
            Role=str(role),
            FightName=str(summary.get("name") or ""),
            FightDurationSeconds=full_duration,
            BossActiveSeconds=boss_active_seconds,
            BuffUptimes=_top_uptimes(buff_auras, uptime_duration, 8),
            DebuffUptimes=_top_uptimes(debuff_auras, uptime_duration, 8),
            RaidDebuffUptimes=raid_debuff_uptimes,
            OutputLabel=output_label,
            OutputRateLabel=rate_label,
            OutputTotal=total,
            OutputPerSecond=(total / full_duration) if full_duration > 0 else 0.0,
            OutputSeries=[],
            TopAbilities=[],
            PeakWindowLabel="",
        )

    def fight(self, report_code: str, fight_id: int) -> dict:
        key = (str(report_code), int(fight_id))
        cached = self._fight_cache.get(key)
        if cached is None:
            cached = self.client.get_fight(report_code, int(fight_id))
            self._fight_cache[key] = cached
        return cached

    def _fight_summary(self, report_code: str, fight_id: int) -> dict:
        fight = self.fight(report_code, fight_id)
        start = float(fight.get("startTime", 0.0) or 0.0)
        end = float(fight.get("endTime", 0.0) or 0.0)
        return {
            "name": fight.get("name", ""),
            "kill": bool(fight.get("kill", False)),
            "boss_percentage": fight.get("bossPercentage"),
            "start_time": start,
            "end_time": end,
            "duration_seconds": max(0.0, (end - start) / 1000.0),
        }

    def _raid_debuff_uptimes(
        self,
        report_code: str,
        fight_id: int,
        start: float,
        end: float,
        uptime_duration: float,
    ) -> list:
        key = (
            str(report_code),
            int(fight_id),
            float(start),
            float(end),
            float(uptime_duration),
        )
        cached = self._raid_debuff_cache.get(key)
        if cached is not None:
            return cached

        auras = self.client.get_aura_table(
            report_code,
            int(fight_id),
            start,
            end,
            data_type="Debuffs",
            hostility_type="Enemies",
        )
        result = _top_uptimes(auras, uptime_duration, 8)
        self._raid_debuff_cache[key] = result
        return result


__all__ = ["PerformanceRaidReviewSnapshotService"]
