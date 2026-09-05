# services/capability_service.py
#
# Orchestrates the ESO Logs client + reference data to build
# the buff/debuff/skill uptime picture for one player on one
# fight, modeled after BTVTools: uptime is reported both
# against the full pull length and against how long the
# boss was actually damageable, since a buff sitting at 85%
# of the full clock might really be full uptime once you
# subtract an unavailable/immune phase.

from __future__ import annotations

from models.capability_model import UptimeResult, WatchEntry
from services.esologs_client import EsoLogsClient
from services.reference_data_service import ReferenceDataService


class CapabilityService:

    def __init__(
        self,
        client: EsoLogsClient,
        reference: ReferenceDataService,
    ):
        self.client = client
        self.reference = reference

    # --------------------------------------------------
    # Suggestions
    # --------------------------------------------------

    def suggest_watches(self, set_names: list[str]) -> list[WatchEntry]:

        suggested = self.reference.suggest_watches_for_sets(set_names)

        return [
            WatchEntry(Name=name, Kind="Buff", Suggested=True)
            for name in suggested
        ]

    # --------------------------------------------------
    # Fetch + compute
    # --------------------------------------------------

    def fetch_fight_summary(self, report_code: str, fight_id: int) -> dict:

        fight = self.client.get_fight(report_code, fight_id)

        start = float(fight.get("startTime", 0.0))
        end = float(fight.get("endTime", 0.0))

        return {
            "name": fight.get("name", ""),
            "kill": bool(fight.get("kill", False)),
            "boss_percentage": fight.get("bossPercentage"),
            "start_time": start,
            "end_time": end,
            "duration_seconds": max(0.0, (end - start) / 1000.0),
        }

    def compute_boss_active_seconds(
        self,
        report_code: str,
        fight_id: int,
        immunity_name: str,
        immunity_kind: str = "Buff",
    ) -> float | None:
        """
        Total fight duration minus the time the boss spent with its
        named immunity buff/debuff active -- i.e. the time the boss
        was actually damageable.

        Returns None if immunity_name is blank (nothing to compute).
        A name that simply isn't found in this particular fight's
        aura list is not an error -- some pulls skip the immunity
        window entirely (e.g. a fast burn) -- so that case returns
        the full fight duration (zero immune time), not None.
        """

        name = (immunity_name or "").strip()

        if not name:
            return None

        summary = self.fetch_fight_summary(report_code, fight_id)

        full_seconds = summary["duration_seconds"]

        data_type = "Debuffs" if immunity_kind == "Debuff" else "Buffs"

        # The immunity effect lives on the boss itself, i.e. an
        # enemy actor -- same hostility_type used elsewhere in this
        # service for reading enemy-side auras (see fetch_uptime's
        # debuff-watch branch), not the "Friendlies" side used for a
        # tracked player's own buffs.
        auras = self.client.get_aura_table(
            report_code,
            fight_id,
            summary["start_time"],
            summary["end_time"],
            data_type=data_type,
            hostility_type="Enemies",
            source_id=None,
        )

        target_key = name.casefold()

        immune_ms = 0.0

        for aura in auras:

            if str(aura.get("name", "")).strip().casefold() == target_key:

                immune_ms += float(aura.get("totalUptime", 0.0))

        immune_seconds = immune_ms / 1000.0

        return max(0.0, full_seconds - immune_seconds)

    def fetch_uptime(
        self,
        report_code: str,
        fight_id: int,
        watches: list[WatchEntry],
        boss_active_seconds: float | None = None,
        source_id: int | None = None,
    ) -> tuple[dict, list[UptimeResult]]:
        """
        Returns (fight_summary, results) where results has one
        UptimeResult per watched entry that was actually found
        in the report (unmatched watches are skipped, not
        zero-filled, so a typo'd skill name doesn't silently
        read as 0% uptime).
        """

        summary = self.fetch_fight_summary(report_code, fight_id)

        full_seconds = summary["duration_seconds"]

        active_seconds = (
            boss_active_seconds
            if boss_active_seconds and boss_active_seconds > 0
            else full_seconds
        )

        buff_watches = [w for w in watches if w.Kind in ("Buff", "Skill") and w.Name]
        debuff_watches = [w for w in watches if w.Kind == "Debuff" and w.Name]

        results: list[UptimeResult] = []

        if buff_watches:

            auras = self.client.get_aura_table(
                report_code,
                fight_id,
                summary["start_time"],
                summary["end_time"],
                data_type="Buffs",
                hostility_type="Friendlies",
                source_id=source_id,
            )

            results.extend(
                self._match_watches(buff_watches, auras, full_seconds, active_seconds)
            )

        if debuff_watches:

            auras = self.client.get_aura_table(
                report_code,
                fight_id,
                summary["start_time"],
                summary["end_time"],
                data_type="Debuffs",
                hostility_type="Enemies",
                source_id=None,
            )

            results.extend(
                self._match_watches(debuff_watches, auras, full_seconds, active_seconds)
            )

        return summary, results

    @staticmethod
    def _match_watches(
        watches: list[WatchEntry],
        auras: list[dict],
        full_seconds: float,
        active_seconds: float,
    ) -> list[UptimeResult]:

        by_name = {
            str(a.get("name", "")).strip().casefold(): a
            for a in auras
        }

        results = []

        for watch in watches:

            aura = by_name.get(watch.Name.strip().casefold())

            if aura is None:
                continue

            uptime_ms = float(aura.get("totalUptime", 0.0))

            uptime_seconds = uptime_ms / 1000.0

            pct_full = (
                (uptime_seconds / full_seconds * 100.0)
                if full_seconds > 0
                else 0.0
            )

            pct_active = (
                (uptime_seconds / active_seconds * 100.0)
                if active_seconds > 0
                else 0.0
            )

            results.append(
                UptimeResult(
                    Name=watch.Name,
                    Kind=watch.Kind,
                    UptimeMs=uptime_ms,
                    UptimePercentFull=round(pct_full, 1),
                    UptimePercentActive=round(min(pct_active, 100.0), 1),
                )
            )

        return results
