from __future__ import annotations

"""Aggregate observed top-ranked ESO Logs player gear usage by combat role.

This is descriptive meta evidence, not canonical build truth. The service asks ESO
Logs for the top individual character rankings for DD, healer, and tank, resolves only
those ranked players back to their report playerDetails, counts distinct set usage per
ranked player, and compares the current snapshot with the previous saved snapshot for
that same encounter/role.
"""

from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import json
from pathlib import Path

from engine.config import get_data_dir
from models.top_team_model import TopTeamPlayer
from services.esologs_client import EsoLogsApiError, EsoLogsClient
from services.top_team_service import TopTeamService

_DEFAULT_PLAYER_LIMIT = 5
_MAX_SAMPLE_PLAYERS_PER_ROLE = 6
_MAX_MOVEMENT_ROWS = 3
_HISTORY_VERSION = 1
_HISTORY_LIMIT_PER_ROLE = 24
_TOP_GEAR_CUTOFF = 10
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
class TrendMovementItem:
    name: str
    current_percent: float
    previous_percent: float
    delta_points: float
    current_rank: int | None
    previous_rank: int | None


@dataclass(frozen=True, slots=True)
class RoleTrendingSummary:
    role: str
    player_count: int
    gear_sets: tuple[TrendingItem, ...] = ()
    classes: tuple[TrendingItem, ...] = ()
    sample_players: tuple[TopTeamPlayer, ...] = ()
    making_waves: tuple[TrendMovementItem, ...] = ()
    cooling_off: tuple[TrendMovementItem, ...] = ()
    new_arrivals: tuple[TrendMovementItem, ...] = ()
    breakouts: tuple[TrendMovementItem, ...] = ()
    has_history: bool = False


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

    def __init__(self, client: EsoLogsClient, history_path: Path | None = None):
        self.client = client
        if history_path is not None:
            self.history_path: Path | None = history_path
        elif isinstance(client, EsoLogsClient):
            self.history_path = get_data_dir() / "esologs_trending_history.json"
        else:
            self.history_path = None

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
        del zone_id

        limit = max(1, int(player_limit))
        players_by_role: dict[str, list[TopTeamPlayer]] = {
            role: [] for role in _ROLE_KEYS
        }
        role_errors: dict[str, str] = {}
        ranked_players_analyzed = 0
        ranked_players_skipped = 0
        report_player_cache: dict[tuple[str, int], list[TopTeamPlayer] | None] = {}

        for role_key in _ROLE_KEYS:
            role_label, metric = _ROLE_RANKING_METRIC[role_key]
            if role_key == "tank":
                rankings, tank_error = self._get_tank_rankings(
                    encounter_id=int(encounter_id),
                    limit=limit,
                )
                if rankings is None:
                    role_errors[role_key] = tank_error or "Tank rankings were unavailable."
                    continue
            else:
                try:
                    rankings = self._get_metric_rankings(
                        encounter_id=int(encounter_id),
                        role_label=role_label,
                        metric=metric,
                        limit=limit,
                    )
                except EsoLogsApiError as exc:
                    role_errors[role_key] = str(exc)
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

        history = self._load_history()
        summaries: dict[str, RoleTrendingSummary] = {}
        for role in _ROLE_KEYS:
            summary = self._summarize_role(role, players_by_role[role])
            previous = self._latest_snapshot(history, int(encounter_id), role)
            summary = self._with_movement(summary, previous)
            summaries[role] = summary
            self._append_snapshot(history, int(encounter_id), role, summary)
        self._save_history(history)

        return EsoLogsTrendingReport(
            trial_name=str(zone_name),
            encounter_name=str(encounter_name),
            ranked_players_analyzed=ranked_players_analyzed,
            ranked_players_skipped=ranked_players_skipped,
            role_summaries=summaries,
            role_errors=role_errors,
        )

    def _get_tank_rankings(
        self,
        *,
        encounter_id: int,
        limit: int,
    ) -> tuple[list[dict] | None, str | None]:
        """Resolve Tank rankings using the filters ESO Logs currently exposes.

        The public Tank Damage Rankings page uses the ``Tanks`` class filter. Prefer
        that evidence-backed path first. Older/specialized ranking shapes remain as
        fallbacks for compatibility with content or partitions that expose them.
        """

        attempts = (
            {"metric": "dps", "class_name": "Tanks", "label": "Tank-class DPS"},
            {"metric": "tankcombineddps", "label": "combined Tank"},
            {"metric": "dps", "spec_name": "Tank", "label": "Tank-spec DPS"},
            {"metric": "dps", "spec_name": "tank", "label": "tank-spec DPS"},
        )
        errors: list[str] = []
        for attempt in attempts:
            try:
                return (
                    self._get_metric_rankings(
                        encounter_id=encounter_id,
                        role_label="Tank",
                        metric=str(attempt["metric"]),
                        limit=limit,
                        spec_name=attempt.get("spec_name"),
                        class_name=attempt.get("class_name"),
                    ),
                    None,
                )
            except EsoLogsApiError as exc:
                errors.append(f"{attempt['label']}: {exc}")
        return None, "; ".join(errors)

    def _get_metric_rankings(
        self,
        *,
        encounter_id: int,
        role_label: str,
        metric: str,
        limit: int,
        spec_name: str | None = None,
        class_name: str | None = None,
    ) -> list[dict]:
        """Read Encounter.characterRankings with explicit schema-supported filters."""

        query = """
        query TrendingRankings(
          $encounterID: Int!
          $metric: CharacterRankingMetricType
          $specName: String
          $className: String
        ) {
          worldData {
            encounter(id: $encounterID) {
              characterRankings(
                metric: $metric
                specName: $specName
                className: $className
              )
            }
          }
        }
        """

        variables = {
            "encounterID": int(encounter_id),
            "metric": metric,
            "specName": spec_name,
            "className": class_name,
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
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _rank_counter(
        counter: Counter[str],
        player_count: int,
    ) -> tuple[TrendingItem, ...]:
        rows = sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold()))
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

    def _load_history(self) -> dict:
        if self.history_path is None or not self.history_path.exists():
            return {"version": _HISTORY_VERSION, "snapshots": []}
        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": _HISTORY_VERSION, "snapshots": []}
        if not isinstance(payload, dict) or not isinstance(payload.get("snapshots"), list):
            return {"version": _HISTORY_VERSION, "snapshots": []}
        return payload

    def _save_history(self, history: dict) -> None:
        if self.history_path is None:
            return
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            self.history_path.write_text(
                json.dumps(history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return

    @staticmethod
    def _latest_snapshot(history: dict, encounter_id: int, role: str) -> dict | None:
        for snapshot in reversed(history.get("snapshots", [])):
            if snapshot.get("encounter_id") == encounter_id and snapshot.get("role") == role:
                return snapshot
        return None

    @staticmethod
    def _snapshot_signature(snapshot: dict) -> tuple:
        sets = snapshot.get("sets", [])
        return (
            int(snapshot.get("player_count", 0)),
            tuple(
                (str(row.get("name", "")), int(row.get("count", 0)))
                for row in sets
                if isinstance(row, dict)
            ),
        )

    def _append_snapshot(
        self,
        history: dict,
        encounter_id: int,
        role: str,
        summary: RoleTrendingSummary,
    ) -> None:
        snapshot = {
            "encounter_id": encounter_id,
            "role": role,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "player_count": summary.player_count,
            "sets": [
                {
                    "name": row.name,
                    "count": row.count,
                    "percent": row.percent,
                    "rank": index,
                }
                for index, row in enumerate(summary.gear_sets, start=1)
            ],
        }
        previous = self._latest_snapshot(history, encounter_id, role)
        if previous and self._snapshot_signature(previous) == self._snapshot_signature(snapshot):
            return
        history.setdefault("snapshots", []).append(snapshot)
        matching_indexes = [
            index
            for index, row in enumerate(history["snapshots"])
            if row.get("encounter_id") == encounter_id and row.get("role") == role
        ]
        excess = len(matching_indexes) - _HISTORY_LIMIT_PER_ROLE
        if excess > 0:
            remove = set(matching_indexes[:excess])
            history["snapshots"] = [
                row for index, row in enumerate(history["snapshots"]) if index not in remove
            ]

    @staticmethod
    def _previous_rows(snapshot: dict | None) -> dict[str, dict]:
        if not snapshot:
            return {}
        return {
            str(row.get("name", "")): row
            for row in snapshot.get("sets", [])
            if isinstance(row, dict) and row.get("name")
        }

    @classmethod
    def _with_movement(
        cls,
        summary: RoleTrendingSummary,
        previous_snapshot: dict | None,
    ) -> RoleTrendingSummary:
        if previous_snapshot is None:
            return summary

        previous = cls._previous_rows(previous_snapshot)
        current = {
            row.name: {"percent": row.percent, "rank": rank}
            for rank, row in enumerate(summary.gear_sets, start=1)
        }
        previous_player_count = max(1, int(previous_snapshot.get("player_count", 0)))
        movement_step = max(
            10.0,
            100.0 / max(summary.player_count, previous_player_count, 1),
        )

        all_names = set(previous) | set(current)
        movements: list[TrendMovementItem] = []
        for name in all_names:
            current_row = current.get(name, {})
            previous_row = previous.get(name, {})
            current_percent = float(current_row.get("percent", 0.0))
            previous_percent = float(previous_row.get("percent", 0.0))
            movements.append(
                TrendMovementItem(
                    name=name,
                    current_percent=current_percent,
                    previous_percent=previous_percent,
                    delta_points=current_percent - previous_percent,
                    current_rank=(int(current_row["rank"]) if current_row.get("rank") is not None else None),
                    previous_rank=(int(previous_row["rank"]) if previous_row.get("rank") is not None else None),
                )
            )

        new_arrivals = [row for row in movements if row.previous_percent <= 0.0 and row.current_percent > 0.0]
        breakouts = [
            row
            for row in movements
            if row.previous_percent > 0.0
            and row.current_rank is not None
            and row.current_rank <= _TOP_GEAR_CUTOFF
            and (row.previous_rank is None or row.previous_rank > _TOP_GEAR_CUTOFF)
        ]
        making_waves = [
            row
            for row in movements
            if row.previous_percent > 0.0
            and row.current_rank is not None
            and row.current_rank > _TOP_GEAR_CUTOFF
            and row.delta_points >= movement_step
        ]
        cooling_off = [
            row
            for row in movements
            if row.previous_percent > 0.0 and row.delta_points <= -movement_step
        ]

        new_arrivals.sort(key=lambda row: (-row.current_percent, row.name.casefold()))
        breakouts.sort(key=lambda row: (-row.delta_points, row.current_rank or 999, row.name.casefold()))
        making_waves.sort(key=lambda row: (-row.delta_points, row.current_rank or 999, row.name.casefold()))
        cooling_off.sort(key=lambda row: (row.delta_points, row.name.casefold()))

        return replace(
            summary,
            making_waves=tuple(making_waves[:_MAX_MOVEMENT_ROWS]),
            cooling_off=tuple(cooling_off[:_MAX_MOVEMENT_ROWS]),
            new_arrivals=tuple(new_arrivals[:_MAX_MOVEMENT_ROWS]),
            breakouts=tuple(breakouts[:_MAX_MOVEMENT_ROWS]),
            has_history=True,
        )


__all__ = [
    "EsoLogsTrendingReport",
    "EsoLogsTrendingService",
    "RoleTrendingSummary",
    "TrendMovementItem",
    "TrendingItem",
]
