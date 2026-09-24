from __future__ import annotations

"""Focused Major Brittle uptime analysis from ESO Logs.

The service intentionally reads fresh ESO Logs data and never persists combat results.
Duplicate Major Brittle aura IDs are de-duplicated by display name using the maximum
reported uptime, matching the existing Performance Dashboard behavior.
"""

from dataclasses import dataclass

MAJOR_BRITTLE_NAME = "Major Brittle"
DEFAULT_PROVIDER_ACTOR_ID = 72
DEFAULT_PROVIDER_LABEL = "Anonymous 72"


@dataclass(frozen=True)
class BrittleProviderUptime:
    actor_id: int
    actor_label: str
    role: str
    uptime_seconds: float
    uptime_percent: float


@dataclass(frozen=True)
class BrittleFightUptime:
    fight_id: int
    fight_name: str
    kill: bool
    duration_seconds: float
    brittle_seconds: float
    brittle_percent: float
    raid_brittle_seconds: float
    raid_brittle_percent: float
    providers: tuple[BrittleProviderUptime, ...]


@dataclass(frozen=True)
class BrittleUptimeReport:
    report_code: str
    fights: tuple[BrittleFightUptime, ...]

    @property
    def average_percent(self) -> float:
        if not self.fights:
            return 0.0
        return round(sum(row.brittle_percent for row in self.fights) / len(self.fights), 1)

    @property
    def best_percent(self) -> float:
        return max((row.brittle_percent for row in self.fights), default=0.0)

    @property
    def lowest_percent(self) -> float:
        return min((row.brittle_percent for row in self.fights), default=0.0)


class BrittleUptimeService:
    """Compare raid-wide and provider-scoped Major Brittle uptime across fights."""

    def __init__(self, client) -> None:
        self.client = client

    @staticmethod
    def _named_uptime_ms(auras: list[dict], name: str = MAJOR_BRITTLE_NAME) -> float:
        wanted = str(name or "").strip().casefold()
        values: list[float] = []
        for aura in auras or []:
            if not isinstance(aura, dict):
                continue
            if str(aura.get("name", "")).strip().casefold() != wanted:
                continue
            try:
                values.append(float(aura.get("totalUptime", 0.0) or 0.0))
            except (TypeError, ValueError):
                continue
        # ESO Logs can surface the same named effect under multiple ability IDs.
        # Those rows must not be summed or the page can report impossible uptime.
        return max(values, default=0.0)

    @staticmethod
    def _percent(uptime_ms: float, duration_seconds: float) -> float:
        if duration_seconds <= 0:
            return 0.0
        return round(min(100.0, max(0.0, (uptime_ms / 1000.0) / duration_seconds * 100.0)), 1)

    def analyze(
        self,
        report_code: str,
        *,
        fight_ids: tuple[int, ...] | None = None,
        kills_only: bool = True,
        provider_actor_id: int = DEFAULT_PROVIDER_ACTOR_ID,
        provider_label: str = DEFAULT_PROVIDER_LABEL,
    ) -> BrittleUptimeReport:
        code = self.client.normalize_report_code(report_code)
        fights = list(self.client.get_fights(code))

        requested = tuple(dict.fromkeys(int(value) for value in (fight_ids or ())))
        by_id = {int(row.get("id", -1)): row for row in fights}
        if requested:
            missing = [fight_id for fight_id in requested if fight_id not in by_id]
            if missing:
                missing_text = ", ".join(str(value) for value in missing)
                raise ValueError(f"Fight(s) not found in report {code}: {missing_text}")
            selected = [by_id[fight_id] for fight_id in requested]
        else:
            selected = [row for row in fights if bool(row.get("kill")) or not kills_only]

        results: list[BrittleFightUptime] = []
        for fight in selected:
            if kills_only and not bool(fight.get("kill")):
                continue

            fight_id = int(fight["id"])
            start = float(fight.get("startTime", 0.0) or 0.0)
            end = float(fight.get("endTime", 0.0) or 0.0)
            duration_seconds = max(0.0, (end - start) / 1000.0)

            raid_auras = self.client.get_aura_table(
                code,
                fight_id,
                start,
                end,
                data_type="Debuffs",
                hostility_type="Enemies",
            )
            raid_brittle_ms = self._named_uptime_ms(raid_auras)

            providers: list[BrittleProviderUptime] = []
            source_auras = self.client.get_aura_table(
                code,
                fight_id,
                start,
                end,
                data_type="Debuffs",
                hostility_type="Enemies",
                source_id=int(provider_actor_id),
            )
            source_ms = self._named_uptime_ms(source_auras)
            if source_ms > 0:
                providers.append(
                    BrittleProviderUptime(
                        actor_id=int(provider_actor_id),
                        actor_label=str(provider_label or DEFAULT_PROVIDER_LABEL),
                        role="",
                        uptime_seconds=round(source_ms / 1000.0, 2),
                        uptime_percent=self._percent(source_ms, duration_seconds),
                    )
                )

            providers.sort(key=lambda row: (-row.uptime_seconds, row.actor_label.casefold()))
            results.append(
                BrittleFightUptime(
                    fight_id=fight_id,
                    fight_name=str(fight.get("name") or f"Fight {fight_id}"),
                    kill=bool(fight.get("kill")),
                    duration_seconds=round(duration_seconds, 2),
                    brittle_seconds=round(source_ms / 1000.0, 2),
                    brittle_percent=self._percent(source_ms, duration_seconds),
                    raid_brittle_seconds=round(raid_brittle_ms / 1000.0, 2),
                    raid_brittle_percent=self._percent(raid_brittle_ms, duration_seconds),
                    providers=tuple(providers),
                )
            )

        return BrittleUptimeReport(report_code=code, fights=tuple(results))


__all__ = [
    "MAJOR_BRITTLE_NAME",
    "DEFAULT_PROVIDER_ACTOR_ID",
    "DEFAULT_PROVIDER_LABEL",
    "BrittleProviderUptime",
    "BrittleFightUptime",
    "BrittleUptimeReport",
    "BrittleUptimeService",
]
