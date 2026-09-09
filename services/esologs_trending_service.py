from __future__ import annotations

"""Aggregate observed top-ranked ESO Logs player gear usage by combat role.

This is descriptive meta evidence, not canonical build truth. The service asks ESO
Logs for the top individual character rankings for DD, healer, and tank, resolves only
those ranked players back to their report playerDetails, and counts distinct set usage
per ranked player.
"""

from collections import Counter
from dataclasses import dataclass, field
import json

from models.top_team_model import TopTeamPlayer
from services.esologs_client import EsoLogsApiError, EsoLogsClient
from services.top_team_service import TopTeamService

_DEFAULT_PLAYER_LIMIT = 5
_MAX_SAMPLE_PLAYERS_PER_ROLE = 6
_ROLE_KEYS = ("dps", "healer", "tank")
_ROLE_RANKING_METRIC = {
    "dps": ("DPS", "dps"),
    "healer": ("Healer", "hps"),
    "tank": ("Tank", "tankcombineddps"),
}


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
    ranked_players_analyzed: int
    ranked_players_skipped: int
    role_summaries: dict[str, RoleTrendingSummary] = field(default_factory=dict)
    role_errors: dict[str, str] = field(default_factory=dict)

    @property
    def players_analyzed(self) -> int:
        return sum(summary.player_count for summary in self.role_summaries.values())


class EsoLogsTrendingService:
    """Build role-aware popularity summaries from top individual ranked players."""

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
        player_limit: int = _DEFAULT_PLAYER_LIMIT,
    ) -> EsoLogsTrendingReport:
        del zone_id  # kept in the call shape for the shared trial picker boundary.

        limit = max(1, int(player_limit))
        players_by_role: dict[str, list[TopTeamPlayer]] = {
            role: [] for role in _ROLE_KEYS
        }
        role_errors: dict[str, str] = {}
        ranked_players_analyzed = 0
        ranked_players_skipped = 0

        # Multiple top-ranked players can come from the same fight. Cache its parsed
        # playerDetails so one fight is fetched once even if several ranked players
        # point to it.
        report_player_cache: dict[tuple[str, int], list[TopTeamPlayer] | None] = {}

        for role_key in _ROLE_KEYS:
            role_label, metric = _ROLE_RANKING_METRIC[role_key]
            try:
                rankings = self._get_metric_rankings(
                    encounter_id=int(encounter_id),
                    role_label=role_label,
                    metric=metric,
                    limit=limit,
                )
            except EsoLogsApiError as primary_exc:
                # ESO Logs' public Tank rankings are exposed as a Tank-spec-filtered
                # damage leaderboard on content where the specialized combined tank
                # metric is unavailable. Keep the combined metric as the first choice
                # for compatibility, then fall back explicitly rather than dropping
                # the entire tank lane.
                if role_key != "tank":
                    role_errors[role_key] = str(primary_exc)
                    continue
                try:
                    rankings = self._get_metric_rankings(
                        encounter_id=int(encounter_id),
                        role_label=role_label,
                        metric="dps",
                        spec_name="Tank",
                        limit=limit,
                    )
                except EsoLogsApiError as fallback_exc:
                    role_errors[role_key] = (
                        f"{primary_exc}; Tank-spec fallback failed: {fallback_exc}"
                    )
                    continue

            for ranking in rankings:
                player = self._resolve_ranked_player(
                    role_key=role_key,
                    ranking=ranking,
                    cache=report_player_cache,
                )
                if player is None:
                    ranked_players_skipped += 1
                    continue

                players_by_role[role_key].append(player)
                ranked_players_analyzed += 1

        if ranked_players_analyzed == 0:
            reason = "; ".join(
                f"{role}: {message}" for role, message in role_errors.items()
            )
            suffix = f" ({reason})" if reason else ""
            raise EsoLogsApiError(
                f"Could not load usable top-ranked players for {encounter_name}{suffix}."
            )

        summaries = {
            role: self._summarize_role(role, players_by_role[role])
            for role in _ROLE_KEYS
        }
        return EsoLogsTrendingReport(
            trial_name=str(zone_name),
            encounter_name=str(encounter_name),
            ranked_players_analyzed=ranked_players_analyzed,
            ranked_players_skipped=ranked_players_skipped,
            role_summaries=summaries,
            role_errors=role_errors,
        )

    def _get_metric_rankings(
        self,
        *,
        encounter_id: int,
        role_label: str,
        metric: str,
        limit: int,
        spec_name: str | None = None,
    ) -> list[dict]:
        """Read Encounter.characterRankings using only schema-valid arguments.

        Encounter.characterRankings accepts a ranking metric and an optional specName,
        but not RoleType. DD and healer use their direct metrics. Tank first attempts
        the specialized combined metric, with an explicit Tank-spec DPS fallback in
        ``analyze_encounter`` for ESO Logs content that exposes tanks that way.
        """

        query = """
        query TrendingRankings(
          $encounterID: Int!
          $metric: CharacterRankingMetricType
          $specName: String
        ) {
          worldData {
            encounter(id: $encounterID) {
              characterRankings(metric: $metric, specName: $specName)
            }
          }
        }
        """

        variables = {
            "encounterID": int(encounter_id),
            "metric": metric,
            "specName": spec_name,
        }
        data = self.client._query(query, variables)
        encounter = ((data.get("worldData") or {}).get("encounter")) or {}
        rankings = encounter.get("characterRankings")

        if isinstance(rankings, str):
            try:
                rankings = json.loads(rankings)
            except json.JSONDecodeError as exc:
                raise EsoLogsApiError(
                    f"ESO Logs returned an unreadable {role_label} rankings payload."
                ) from exc

        rows = None
        if isinstance(rankings, dict):
            rows = rankings.get("rankings") or rankings.get("data")
        elif isinstance(rankings, list):
            rows = rankings

        if not rows:
            raise EsoLogsApiError(
                f"No ranked {role_label} parses were found for this encounter."
            )

        entries: list[dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            report = row.get("report")
            if not isinstance(report, dict) or not report.get("code"):
                continue

            fight_id = report.get("fightID", report.get("fightId"))
            if fight_id is None:
                continue

            entries.append(
                {
                    "name": row.get("name"),
                    "class": row.get("class") or row.get("className"),
                    "report_code": str(report["code"]),
                    "fight_id": int(fight_id),
                }
            )
            if len(entries) >= limit:
                break

        if not entries:
            raise EsoLogsApiError(
                f"None of the ranked {role_label} entries included a usable "
                "report pointer (report.code / report.fightID)."
            )

        return entries

    def _resolve_ranked_player(
        self,
        *,
        role_key: str,
        ranking: dict,
        cache: dict[tuple[str, int], list[TopTeamPlayer] | None],
    ) -> TopTeamPlayer | None:
        name = str(ranking.get("name") or "").strip()
        report_code = str(ranking.get("report_code") or "").strip()
        fight_id = ranking.get("fight_id")
        if not name or not report_code or fight_id is None:
            return None

        try:
            normalized_fight_id = int(fight_id)
        except (TypeError, ValueError):
            return None

        cache_key = (report_code, normalized_fight_id)
        if cache_key not in cache:
            try:
                fight = self.client.get_fight(report_code, normalized_fight_id)
                start = float(fight.get("startTime", 0.0))
                end = float(fight.get("endTime", 0.0))
                details = self.client.get_report_player_summary(
                    report_code,
                    normalized_fight_id,
                    start,
                    end,
                )
                cache[cache_key] = TopTeamService._players_from_details(details)
            except EsoLogsApiError:
                cache[cache_key] = None

        players = cache[cache_key] or []
        name_key = name.casefold()
        class_key = str(ranking.get("class") or "").strip().casefold()

        matches = [
            player
            for player in players
            if player.Role == role_key and player.Name.strip().casefold() == name_key
        ]
        if class_key:
            class_matches = [
                player
                for player in matches
                if player.ClassName.strip().casefold() == class_key
            ]
            if class_matches:
                matches = class_matches

        # Do not guess an anonymized or renamed player from roster position/class alone.
        # If the ranked identity cannot be matched exactly, that observation is skipped.
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _rank_counter(
        counter: Counter[str],
        player_count: int,
    ) -> tuple[TrendingItem, ...]:
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
            # distinct set names. Counting once per ranked player avoids a five-piece
            # set appearing five times merely because five equipped items share it.
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
