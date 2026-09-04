from __future__ import annotations

import json
from typing import Any

from models.top_team_model import TopTeamPlayer, TopTeamResult
from services.esologs_client import EsoLogsApiError, EsoLogsClient
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


class TopTeamService:
    """Read the current top encounter log and summarize its equipped gear sets."""

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
                players.append(
                    TopTeamPlayer(
                        Name=str(actor.get("name") or actor.get("displayName") or "Unknown"),
                        Role=role,
                        GearSets=self._gear_sets(actor),
                    )
                )

        return TopTeamResult(
            TrialName=zone_name,
            EncounterName=encounter_name,
            ReportCode=report_code,
            FightId=fight_id,
            Players=players,
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

    @classmethod
    def _gear_sets(cls, actor: dict) -> list[str]:
        combatant = actor.get("combatantInfo") if isinstance(actor.get("combatantInfo"), dict) else actor
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
