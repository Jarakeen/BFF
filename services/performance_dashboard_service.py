# services/performance_dashboard_service.py
#
# Orchestrates the ESO Logs client to build the Performance
# Dashboard tab's picture for one chosen actor (real name or
# anonymized "Anonymous N") on one fight: who's in the fight and
# what role ESO Logs already grouped them under, that actor's own
# buff/debuff uptime, their healing or damage total/rate, an
# output-over-time series, and a top-abilities breakdown -- plus a
# plain-language "best stretch" callout pulled out of that series.
#
# Reuses CapabilityService purely for its fight-summary / boss-
# active-time plumbing (see capability_service.py's own docstring
# for why that stays a separate, narrower service).

from __future__ import annotations

from models.performance_model import (
    AbilityBreakdown,
    AbilityUptime,
    ActorChoice,
    PerformanceSnapshot,
)
from services.capability_service import CapabilityService
from services.esologs_client import EsoLogsClient

# ESO Logs' own dataType/hostilityType names for each role's output
# metric -- a healer's relevant output is healing done to allies,
# a DPS or tank's is damage done to enemies.
ROLE_OUTPUT = {
    "Healer": ("Healing", "Friendlies", "Healing", "HPS"),
    "DPS": ("DamageDone", "Enemies", "Damage", "DPS"),
    "Tank": ("DamageDone", "Enemies", "Damage", "DPS"),
}

TOP_UPTIME_COUNT = 8
TOP_ABILITY_COUNT = 6
PEAK_WINDOW_SECONDS = 10.0


class PerformanceDashboardService:

    def __init__(self, client: EsoLogsClient):

        self.client = client

        self.capability_service = CapabilityService(client, reference=None)

    # --------------------------------------------------
    # Who am I?
    # --------------------------------------------------

    def list_actors(self, report_code: str, fight_id: int) -> tuple[dict, list[ActorChoice]]:
        """
        Return (fight_summary, choices) -- every player ESO Logs
        reports for this fight, with a display label and the role
        ESO Logs already grouped them under. No separate role guess
        is needed since get_report_player_summary's playerDetails
        is already split into tanks/healers/dps.
        """

        summary = self.capability_service.fetch_fight_summary(report_code, fight_id)

        player_details = self.client.get_report_player_summary(
            report_code, fight_id, summary["start_time"], summary["end_time"],
        )

        choices: list[ActorChoice] = []

        for role, actor in _iter_actors_by_role(player_details):

            actor_id = actor.get("id")

            if actor_id is None:
                continue

            anonymous = bool(actor.get("anonymous"))

            name = str(actor.get("name") or "").strip() or f"Anonymous {actor_id}"

            class_name = str(actor.get("type") or actor.get("class") or "").strip()

            label = f"{name} -- {class_name}" if class_name else name

            choices.append(
                ActorChoice(
                    ActorId=int(actor_id),
                    Label=label,
                    Role=role,
                    Anonymous=anonymous,
                )
            )

        return summary, choices

    # --------------------------------------------------
    # Build the dashboard
    # --------------------------------------------------

    def build_snapshot(
        self,
        report_code: str,
        fight_id: int,
        actor_id: int,
        actor_label: str,
        role: str,
    ) -> PerformanceSnapshot:

        summary = self.capability_service.fetch_fight_summary(report_code, fight_id)

        start, end = summary["start_time"], summary["end_time"]

        duration = summary["duration_seconds"]

        # Buffs: filter by targetID (who *holds* the buff) -- most
        # raid buffs (Major Courage, Major Sorcery, ...) are cast
        # by someone else, so this actor's own uptime picture comes
        # from what's active ON them, not what they personally cast.
        buff_uptimes = self._top_uptimes(
            report_code, fight_id, start, end, duration,
            data_type="Buffs", hostility_type="Friendlies",
            filter_by="target", actor_id=actor_id,
        )

        # Debuffs: filter by sourceID (who *applied* it) -- this is
        # "debuffs you personally landed on the boss", which is
        # legitimately empty for builds that don't apply any.
        debuff_uptimes = self._top_uptimes(
            report_code, fight_id, start, end, duration,
            data_type="Debuffs", hostility_type="Enemies",
            filter_by="source", actor_id=actor_id,
        )

        data_type, hostility_type, output_label, rate_label = ROLE_OUTPUT.get(
            role, ROLE_OUTPUT["DPS"]
        )

        entries, total = self.client.get_actor_table(
            report_code, fight_id, start, end,
            data_type=data_type, hostility_type=hostility_type,
            source_id=actor_id, view_by="Ability",
        )

        top_abilities = _top_abilities(entries, total, TOP_ABILITY_COUNT)

        points = self.client.get_output_graph(
            report_code, fight_id, start, end,
            data_type=data_type, hostility_type=hostility_type, source_id=actor_id,
        )

        peak_label = _peak_window_label(points, PEAK_WINDOW_SECONDS, rate_label)

        output_per_second = (total / duration) if duration > 0 else 0.0

        return PerformanceSnapshot(
            ReportCode=report_code,
            FightId=str(fight_id),
            ActorId=actor_id,
            ActorLabel=actor_label,
            Role=role,
            FightName=summary.get("name", ""),
            FightDurationSeconds=duration,
            BuffUptimes=buff_uptimes,
            DebuffUptimes=debuff_uptimes,
            OutputLabel=output_label,
            OutputRateLabel=rate_label,
            OutputTotal=total,
            OutputPerSecond=output_per_second,
            OutputSeries=points,
            TopAbilities=top_abilities,
            PeakWindowLabel=peak_label,
        )

    def _top_uptimes(
        self,
        report_code: str,
        fight_id: int,
        start: float,
        end: float,
        duration_seconds: float,
        data_type: str,
        hostility_type: str,
        filter_by: str,
        actor_id: int,
    ) -> list[AbilityUptime]:

        kwargs = (
            {"target_id": actor_id} if filter_by == "target" else {"source_id": actor_id}
        )

        auras = self.client.get_aura_table(
            report_code, fight_id, start, end,
            data_type=data_type, hostility_type=hostility_type, **kwargs,
        )

        return _top_uptimes(auras, duration_seconds, TOP_UPTIME_COUNT)


# --------------------------------------------------
# Pure helpers (no network) -- kept as module-level functions so
# they're trivially testable without a fake client.
# --------------------------------------------------


def _iter_actors_by_role(player_details):
    """
    Yield (role, actor_dict) pairs from ESO Logs' playerDetails,
    which can arrive grouped ({"tanks": [...], "healers": [...],
    "dps": [...]}) or as a flat list with a per-actor role field --
    the same two shapes services/esologs_raw_importer.py already
    has to tolerate.
    """

    if isinstance(player_details, dict):

        for role, key in (("Tank", "tanks"), ("Healer", "healers"), ("DPS", "dps")):

            actors = player_details.get(key) or []

            if isinstance(actors, dict):
                actors = list(actors.values())

            if not isinstance(actors, list):
                continue

            for actor in actors:

                if isinstance(actor, dict):
                    yield role, actor

        return

    if isinstance(player_details, list):

        for actor in player_details:

            if not isinstance(actor, dict):
                continue

            raw_role = str(
                actor.get("role") or actor.get("roleName") or actor.get("specRole") or ""
            ).strip().casefold()

            if raw_role in ("tank", "tanks"):
                role = "Tank"
            elif raw_role in ("healer", "healing", "healers"):
                role = "Healer"
            else:
                role = "DPS"

            yield role, actor


def _top_uptimes(
    auras: list[dict],
    duration_seconds: float,
    limit: int,
) -> list[AbilityUptime]:

    rows: list[AbilityUptime] = []

    for aura in auras:

        if not isinstance(aura, dict):
            continue

        name = str(aura.get("name", "")).strip()

        if not name:
            continue

        uptime_ms = float(aura.get("totalUptime", 0.0) or 0.0)

        uptime_seconds = uptime_ms / 1000.0

        pct = (
            (uptime_seconds / duration_seconds * 100.0)
            if duration_seconds > 0
            else 0.0
        )

        rows.append(
            AbilityUptime(
                Name=name,
                UptimeSeconds=uptime_seconds,
                UptimePercent=round(min(pct, 100.0), 1),
            )
        )

    rows.sort(key=lambda r: r.UptimeSeconds, reverse=True)

    return rows[:limit]


def _top_abilities(
    entries: list[dict],
    total: float,
    limit: int,
) -> list[AbilityBreakdown]:

    rows: list[AbilityBreakdown] = []

    for entry in entries:

        if not isinstance(entry, dict):
            continue

        name = str(entry.get("name", "")).strip()

        if not name:
            continue

        amount = float(entry.get("total", 0.0) or 0.0)

        pct = (amount / total * 100.0) if total > 0 else 0.0

        rows.append(
            AbilityBreakdown(Name=name, Total=amount, Percent=round(pct, 1))
        )

    rows.sort(key=lambda r: r.Total, reverse=True)

    return rows[:limit]


def _peak_window_label(
    points: list[tuple[float, float]],
    window_seconds: float,
    rate_label: str,
) -> str:
    """
    Find the window_seconds-wide stretch of the output series with
    the highest summed output, and describe it in plain language --
    e.g. "Best 10s stretch: 0:42-0:52 at 41,204 DPS". Returns a
    friendly placeholder instead of a misleading number if there
    isn't enough data to say anything meaningful.
    """

    if len(points) < 2:
        return "Not enough data yet to find a peak stretch."

    best_total = -1.0
    best_start = points[0][0]
    best_end = points[0][0]

    for i in range(len(points)):

        window_start = points[i][0]

        window_total = 0.0
        window_end = window_start

        j = i

        while j < len(points) and points[j][0] - window_start <= window_seconds:
            window_total += points[j][1]
            window_end = points[j][0]
            j += 1

        if window_total > best_total:
            best_total = window_total
            best_start = window_start
            best_end = window_end

    span = max(best_end - best_start, 1.0)

    rate = best_total / span

    return (
        f"Best {window_seconds:.0f}s stretch: "
        f"{_format_time(best_start)}-{_format_time(best_end)} "
        f"at {rate:,.0f} {rate_label}"
    )


def _format_time(seconds: float) -> str:

    total = int(max(seconds, 0.0))

    return f"{total // 60}:{total % 60:02d}"
