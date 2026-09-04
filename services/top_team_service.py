from __future__ import annotations

import json
from typing import Any

from models.top_team_model import TopTeamPlayer, TopTeamResult
from services.esologs_client import (
    MUNDUS_STONE_NAMES,
    EsoLogsApiError,
    EsoLogsClient,
)
from services.esologs_combat_importer import PLAYER_QUERY


_ZONES_QUERY = """
query TopTeamZones {
  worldData {
    zones {
      id
      name
      encounters {
        id
        name
      }
    }
  }
}
"""

_RANKING_QUERY = """
query TopTeamRanking($encounterID: Int!) {
  worldData {
    encounter(id: $encounterID) {
      fightRankings(page: 1, includeOtherPlayers: true)
    }
  }
}
"""

_MUNDUS_UPTIME_THRESHOLD_PERCENT = 60.0


class TopTeamService:
    """Read the current top encounter log as reusable observed build evidence.

    The initial fetch stays intentionally bounded: one ranking lookup, the fight,
    and one playerDetails payload. Class, gear-set names, and observed abilities are
    parsed from that payload. Mundus remains lazy because ESO Logs exposes it only as
    aura uptime; fetching it eagerly would add up to one network call per raid member.
    """

    def __init__(self, client: EsoLogsClient):
        self.client = client

    @staticmethod
    def _scalar(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def list_trials(self) -> list[dict]:
        data = self.client._query(_ZONES_QUERY, {})
        zones = (data.get("worldData") or {}).get("zones") or []
        trials: list[dict] = []
        for zone in zones:
            encounters = zone.get("encounters") or []
            if not encounters:
                continue
            trials.append(
                {
                    "id": int(zone["id"]),
                    "name": str(zone.get("name") or f"Zone {zone['id']}"),
                    "encounters": [
                        {
                            "id": int(encounter["id"]),
                            "name": str(encounter.get("name") or f"Encounter {encounter['id']}"),
                        }
                        for encounter in encounters
                        if encounter.get("id") is not None
                    ],
                }
            )
        return sorted(trials, key=lambda row: row["name"].casefold())

    def get_top_team(
        self,
        *,
        zone_id: int,
        zone_name: str,
        encounter_id: int,
        encounter_name: str,
    ) -> TopTeamResult:
        del zone_id  # retained in the public call shape for the trial picker.

        ranking_data = self.client._query(
            _RANKING_QUERY,
            {"encounterID": int(encounter_id)},
        )
        encounter = (ranking_data.get("worldData") or {}).get("encounter") or {}
        rankings = self._scalar(encounter.get("fightRankings")) or {}
        ranking = self._first_ranking(rankings)
        report_code, fight_id = self._ranking_report_fight(ranking)

        fight = self.client.get_fight(report_code, fight_id)
        start = float(fight.get("startTime", 0))
        end = float(fight.get("endTime", 0))

        details_data = self.client._query(
            PLAYER_QUERY,
            {
                "code": report_code,
                "fightIDs": [int(fight_id)],
                "startTime": start,
                "endTime": end,
            },
        )
        report = (details_data.get("reportData") or {}).get("report") or {}
        details = self._scalar(report.get("playerDetails")) or {}

        players: list[TopTeamPlayer] = []
        for bucket, role in (("tanks", "tank"), ("healers", "healer"), ("dps", "dps")):
            for actor in details.get(bucket) or []:
                if not isinstance(actor, dict):
                    continue
                actor_id = actor.get("id")
                try:
                    normalized_actor_id = None if actor_id is None else int(actor_id)
                except (TypeError, ValueError):
                    normalized_actor_id = None
                players.append(
                    TopTeamPlayer(
                        Name=str(actor.get("name") or actor.get("displayName") or "Unknown"),
                        Role=role,
                        GearSets=self._gear_sets(actor),
                        ClassName=self._class_name(actor),
                        Abilities=self._abilities(actor),
                        Mundus="",
                        ActorId=normalized_actor_id,
                    )
                )

        return TopTeamResult(
            TrialName=zone_name,
            EncounterName=encounter_name,
            ReportCode=report_code,
            FightId=fight_id,
            Players=players,
        )

    def get_player_mundus(
        self,
        *,
        report_code: str,
        fight_id: int,
        actor_id: int,
    ) -> str:
        """Resolve one player's Mundus on demand from buff uptime evidence."""

        fight = self.client.get_fight(report_code, fight_id)
        start = float(fight.get("startTime", 0.0))
        end = float(fight.get("endTime", 0.0))
        duration_ms = max(0.0, end - start)
        if duration_ms <= 0:
            return ""

        auras = self.client.get_aura_table(
            report_code,
            fight_id,
            start,
            end,
            data_type="Buffs",
            hostility_type="Friendlies",
            source_id=int(actor_id),
        )
        for aura in auras:
            if not isinstance(aura, dict):
                continue
            name = str(aura.get("name", "") or "").strip()
            if name not in MUNDUS_STONE_NAMES:
                continue
            try:
                uptime_ms = float(aura.get("totalUptime", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            if (uptime_ms / duration_ms) * 100.0 >= _MUNDUS_UPTIME_THRESHOLD_PERCENT:
                return name
        return ""

    def resolve_player_mundus(
        self,
        result: TopTeamResult,
        player: TopTeamPlayer,
    ) -> str:
        """Convenience boundary for a future View/Add Template UI action."""

        if player.Mundus:
            return player.Mundus
        if player.ActorId is None or not result.ReportCode or not result.FightId:
            return ""
        return self.get_player_mundus(
            report_code=result.ReportCode,
            fight_id=result.FightId,
            actor_id=player.ActorId,
        )

    @classmethod
    def _first_ranking(cls, payload: Any) -> dict:
        payload = cls._scalar(payload)
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = payload.get("rankings") or payload.get("data") or []
        else:
            rows = []
        if isinstance(rows, dict):
            rows = rows.get("rankings") or rows.get("data") or []
        if not rows or not isinstance(rows[0], dict):
            raise EsoLogsApiError("ESO Logs returned no ranked team for that encounter.")
        return rows[0]

    @staticmethod
    def _ranking_report_fight(ranking: dict) -> tuple[str, int]:
        report = ranking.get("report") if isinstance(ranking.get("report"), dict) else {}
        code = (
            report.get("code")
            or ranking.get("reportCode")
            or ranking.get("code")
        )
        fight_id = (
            report.get("fightID")
            or report.get("fightId")
            or ranking.get("fightID")
            or ranking.get("fightId")
            or ranking.get("fight_id")
        )
        if not code or fight_id is None:
            raise EsoLogsApiError(
                "ESO Logs returned a ranked team without a usable report/fight reference."
            )
        return str(code), int(fight_id)

    @staticmethod
    def _combatant_info(actor: dict) -> dict:
        info = actor.get("combatantInfo")
        return info if isinstance(info, dict) else actor

    @classmethod
    def _class_name(cls, actor: dict) -> str:
        info = cls._combatant_info(actor)
        return str(
            actor.get("type")
            or actor.get("class")
            or actor.get("className")
            or info.get("type")
            or info.get("class")
            or ""
        ).strip()

    @classmethod
    def _abilities(cls, actor: dict) -> list[str]:
        info = cls._combatant_info(actor)
        talents = info.get("talents")
        if not isinstance(talents, list):
            talents = actor.get("talents") if isinstance(actor.get("talents"), list) else []

        names: list[str] = []
        seen: set[str] = set()
        for talent in talents:
            if isinstance(talent, dict):
                nested = talent.get("ability")
                name = talent.get("name") or talent.get("displayName")
                if not name and isinstance(nested, dict):
                    name = nested.get("name")
            else:
                name = talent
            text = str(name or "").strip()
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                names.append(text)
        return names

    @classmethod
    def _gear_sets(cls, actor: dict) -> list[str]:
        combatant = cls._combatant_info(actor)
        gear = combatant.get("gear") if isinstance(combatant, dict) else None
        if not isinstance(gear, list):
            gear = actor.get("gear") if isinstance(actor.get("gear"), list) else []

        names: list[str] = []
        seen: set[str] = set()
        for item in gear:
            if not isinstance(item, dict):
                continue
            nested_set = item.get("set")
            name = item.get("setName") or item.get("set_name")
            if not name and isinstance(nested_set, dict):
                name = nested_set.get("name")
            elif not name and isinstance(nested_set, str):
                name = nested_set
            if not name:
                continue
            text = str(name).strip()
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                names.append(text)
        return names
