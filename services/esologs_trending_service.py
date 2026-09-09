from __future__ import annotations

"""Aggregate observed ranked ESO Logs gear usage by combat role.

This is descriptive meta evidence, not canonical build truth. The service samples a
bounded number of ranked encounter reports, parses playerDetails through the existing
TopTeamService boundary, and counts distinct set usage per player.
"""

from collections import Counter
from dataclasses import dataclass, field

from models.top_team_model import TopTeamPlayer
from services.esologs_client import EsoLogsApiError, EsoLogsClient
from services.top_team_service import TopTeamService

_DEFAULT_REPORT_LIMIT = 5
_MAX_SAMPLE_PLAYERS_PER_ROLE = 6
_ROLE_KEYS = ("dps", "healer", "tank")


@dataclass(frozen=True, slots=True)
class TrendingItem:
    name: str
    count: int
    player_count: int

    @property
    def percent(self) -> float:
        if self.player_count <= 0:
            return 0.0
        return (self.count / self.player_count) * 100.0


@dataclass(frozen=True, slots=True)
class RoleTrendingSummary:
    role: str
    player_count: int
    gear_sets: tuple[TrendingItem, ...] = ()
    classes: tuple[TrendingItem, ...] = ()
    sample_players: tuple[TopTeamPlayer, ...] = ()


@dataclass(frozen=True, slots=True)
class EsoLogsTrendingReport:
    trial_name: str
    encounter_name: str
    reports_analyzed: int
    reports_skipped: int
    role_summaries: dict[str, RoleTrendingSummary] = field(default_factory=dict)

    @property
    def players_analyzed(self) -> int:
        return sum(summary.player_count for summary in self.role_summaries.values())


class EsoLogsTrendingService:
    """Build a role-aware gear popularity snapshot from top ranked reports."""

    def __init__(self, client: EsoLogsClient):
        self.client = client

    def list_trials(self) -> list[dict]:
        return self.client.get_trial_zones()

    def analyze_encounter(
        self,
        *,
        zone_id: int,
        zone_name: str,
        encounter_id: int,
        encounter_name: str,
        report_limit: int = _DEFAULT_REPORT_LIMIT,
    ) -> EsoLogsTrendingReport:
        del zone_id  # kept in the call shape for the shared trial picker boundary.

        limit = max(1, int(report_limit))
        candidates = self.client.get_top_reports_for_encounter(
            int(encounter_id),
            limit=limit,
        )

        players_by_role: dict[str, list[TopTeamPlayer]] = {
            role: [] for role in _ROLE_KEYS
        }
        reports_analyzed = 0
        reports_skipped = 0

        for report_code, fight_id in candidates:
            try:
                fight = self.client.get_fight(report_code, fight_id)
                start = float(fight.get("startTime", 0.0))
                end = float(fight.get("endTime", 0.0))
                details = self.client.get_report_player_summary(
                    report_code,
                    fight_id,
                    start,
                    end,
                )
            except EsoLogsApiError:
                reports_skipped += 1
                continue

            players = TopTeamService._players_from_details(details)
            if not players:
                reports_skipped += 1
                continue

            reports_analyzed += 1
            for player in players:
                if player.Role in players_by_role:
                    players_by_role[player.Role].append(player)

        if reports_analyzed == 0:
            raise EsoLogsApiError(
                f"Could not load usable ranked reports for {encounter_name}."
            )

        summaries = {
            role: self._summarize_role(role, players_by_role[role])
            for role in _ROLE_KEYS
        }
        return EsoLogsTrendingReport(
            trial_name=str(zone_name),
            encounter_name=str(encounter_name),
            reports_analyzed=reports_analyzed,
            reports_skipped=reports_skipped,
            role_summaries=summaries,
        )

    @staticmethod
    def _rank_counter(counter: Counter[str], player_count: int) -> tuple[TrendingItem, ...]:
        rows = sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )
        return tuple(
            TrendingItem(name=name, count=count, player_count=player_count)
            for name, count in rows
        )

    @classmethod
    def _summarize_role(
        cls,
        role: str,
        players: list[TopTeamPlayer],
    ) -> RoleTrendingSummary:
        gear_counts: Counter[str] = Counter()
        class_counts: Counter[str] = Counter()

        for player in players:
            # TopTeamService already deduplicates a player's repeated gear pieces into
            # distinct set names. Counting once per player avoids a five-piece set
            # appearing five times merely because five equipped items share the set.
            gear_counts.update(player.GearSets)
            if player.ClassName:
                class_counts[player.ClassName] += 1

        player_count = len(players)
        return RoleTrendingSummary(
            role=role,
            player_count=player_count,
            gear_sets=cls._rank_counter(gear_counts, player_count),
            classes=cls._rank_counter(class_counts, player_count),
            sample_players=tuple(players[:_MAX_SAMPLE_PLAYERS_PER_ROLE]),
        )


__all__ = [
    "EsoLogsTrendingReport",
    "EsoLogsTrendingService",
    "RoleTrendingSummary",
    "TrendingItem",
]
