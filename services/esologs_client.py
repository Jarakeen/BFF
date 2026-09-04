# services/esologs_client.py
#
# Minimal ESO Logs API v2 client -- OAuth2 client-credentials
# auth plus the GraphQL queries the Capabilities page needs:
# a report's fights, a buff/debuff uptime table for one fight,
# the trial/encounter list for the "choose a trial" dropdown,
# the top-ranked log for a boss, and that log's full team
# summary (gear/class/role) for the Top Ranked Team card.
#
# ESO Logs runs the same v2 API shape as WoW Logs (Archon):
#   Token:    POST https://www.esologs.com/oauth/token
#             (Basic auth: client_id / client_secret,
#              grant_type=client_credentials)
#   GraphQL:  POST https://www.esologs.com/api/v2/client
#             (Authorization: Bearer <token>)
#
# Full schema: https://www.esologs.com/v2-api-docs/eso/
#
# This module has no network access from the sandbox this
# was written in, so field names were written against the
# published schema/docs rather than a live call -- if ESO
# Logs has since renamed a field, the error message from
# raise_for_status()/GraphQL "errors" will say so clearly.
# The newer methods (get_top_report_for_encounter,
# get_report_player_summary) go further and validate the
# response shape explicitly before returning, because their
# fields (rankings payload, playerDetails) were the least
# certain parts of the schema at the time this was written --
# see each method's docstring for exactly what's unverified.

from __future__ import annotations

import json
import time
from urllib.parse import urlparse

import requests

TOKEN_URL = "https://www.esologs.com/oauth/token"
GRAPHQL_URL = "https://www.esologs.com/api/v2/client"

# ESO Logs' worldData.zones endpoint returns every zone it knows about
# (dungeons, arenas, trials). We only want trials in the "choose a
# trial" dropdown, and there's no zone "type" field to filter on that
# has been verified against a live schema, so we filter by name
# instead. IDs themselves always come from the live response -- this
# list is only an allowlist of names, never a source of numeric IDs --
# so a renamed/retired zone just disappears from the dropdown rather
# than pointing at a stale ID. New trials need a name added here after
# they release; that's the one maintenance cost of not hardcoding IDs.
KNOWN_TRIAL_ZONE_NAMES = frozenset(
    name.casefold()
    for name in (
        "Aetherian Archive",
        "Hel Ra Citadel",
        "Sanctum Ophidia",
        "Maw of Lorkhaj",
        "The Halls of Fabrication",
        "Asylum Sanctorium",
        "Cloudrest",
        "Sunspire",
        "Kyne's Aegis",
        "Rockgrove",
        "Dreadsail Reef",
        "Sanity's Edge",
        "Lucent Citadel",
        "Ossein Cage",
    )
)

# Mundus stones are not exposed as a build/gear field anywhere in the
# v2 schema; they're inferred from buff uptime, matched by the aura's
# display name against this known set (ESO has exactly these twelve).
MUNDUS_STONE_NAMES = frozenset(
    (
        "The Warrior",
        "The Mage",
        "The Serpent",
        "The Thief",
        "The Lady",
        "The Steed",
        "The Lord",
        "The Apprentice",
        "The Ritual",
        "The Lover",
        "The Atronach",
        "The Shadow",
        "The Tower",
    )
)


class EsoLogsApiError(Exception):
    pass


class EsoLogsClient:

    def __init__(self, client_id: str, client_secret: str):

        self.client_id = client_id
        self.client_secret = client_secret

        self._token: str | None = None
        self._token_expires_at: float = 0.0

    # --------------------------------------------------
    # Auth
    # --------------------------------------------------

    def _get_token(self) -> str:

        if self._token and time.time() < self._token_expires_at - 30:
            return self._token

        if not self.client_id or not self.client_secret:

            raise EsoLogsApiError(
                "ESO Logs Client ID / Secret are not configured. "
                "Set them on the Settings page."
            )

        response = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            timeout=15,
        )

        if response.status_code != 200:

            raise EsoLogsApiError(
                f"ESO Logs authentication failed "
                f"({response.status_code}): {response.text[:300]}"
            )

        payload = response.json()

        token = payload.get("access_token")

        if not token:
            raise EsoLogsApiError("ESO Logs did not return an access token.")

        self._token = token

        self._token_expires_at = time.time() + float(
            payload.get("expires_in", 3600)
        )

        return token

    # --------------------------------------------------
    # GraphQL
    # --------------------------------------------------

    def _query(self, query: str, variables: dict) -> dict:

        token = self._get_token()

        response = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

        if response.status_code != 200:

            raise EsoLogsApiError(
                f"ESO Logs request failed "
                f"({response.status_code}): {response.text[:300]}"
            )

        payload = response.json()

        if payload.get("errors"):

            message = "; ".join(
                e.get("message", "unknown error") for e in payload["errors"]
            )

            raise EsoLogsApiError(f"ESO Logs API error: {message}")

        return payload.get("data", {})

    # --------------------------------------------------
    # Report / fights
    # --------------------------------------------------

    @staticmethod
    def normalize_report_code(report_code: str) -> str:
        """Accept either a raw report code or an ESO Logs report URL."""

        value = str(report_code or "").strip()

        if not value:
            return ""

        parsed = urlparse(value)

        if parsed.scheme and parsed.netloc:
            parts = [part for part in parsed.path.split("/") if part]

            try:
                index = next(
                    i for i, part in enumerate(parts)
                    if part.casefold() == "reports"
                )
            except StopIteration:
                return value

            if index + 1 < len(parts):
                return parts[index + 1].strip()

        return value.rstrip("/").split("/")[-1].strip()

    def get_fights(self, report_code: str) -> list[dict]:
        """
        Return every fight in a report: id, name, kill,
        bossPercentage, encounterID, and the start/end
        timestamps (ms, report-relative) used to scope the
        buff/debuff table query.
        """

        code = self.normalize_report_code(report_code)

        if not code:
            raise EsoLogsApiError("Enter an ESO Logs report code or report URL.")

        query = """
        query ReportFights($code: String!) {
          reportData {
            report(code: $code) {
              title
              fights {
                id
                name
                kill
                difficulty
                bossPercentage
                startTime
                endTime
                encounterID
              }
            }
          }
        }
        """

        data = self._query(query, {"code": code})

        report = (data.get("reportData") or {}).get("report")

        if report is None:

            raise EsoLogsApiError(
                f"Report '{code}' was not found (or isn't public)."
            )

        return report.get("fights") or []

    def get_fight(self, report_code: str, fight_id: int) -> dict:

        code = self.normalize_report_code(report_code)
        fights = self.get_fights(code)

        for fight in fights:

            if int(fight.get("id", -1)) == int(fight_id):
                return fight

        raise EsoLogsApiError(
            f"Fight {fight_id} was not found in report '{code}'."
        )

    # --------------------------------------------------
    # Buff / debuff tables
    # --------------------------------------------------

    def get_aura_table(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
        data_type: str = "Buffs",
        hostility_type: str = "Friendlies",
        source_id: int | None = None,
    ) -> list[dict]:
        """
        Fetch a Buffs/Debuffs table for one fight and return
        the list of aura entries: name, guid, totalUptime
        (ms), totalUses.

        dataType: "Buffs" | "Debuffs"
        hostilityType: "Friendlies" | "Enemies"
          (use Enemies + Debuffs to see debuffs the group
          landed on the boss.)
        """

        code = self.normalize_report_code(report_code)

        if not code:
            raise EsoLogsApiError("Enter an ESO Logs report code or report URL.")

        query = """
        query AuraTable(
          $code: String!
          $fightIDs: [Int]!
          $startTime: Float!
          $endTime: Float!
          $dataType: TableDataType!
          $hostilityType: HostilityType!
          $sourceID: Int
        ) {
          reportData {
            report(code: $code) {
              table(
                fightIDs: $fightIDs
                startTime: $startTime
                endTime: $endTime
                dataType: $dataType
                hostilityType: $hostilityType
                sourceID: $sourceID
              )
            }
          }
        }
        """

        variables = {
            "code": code,
            "fightIDs": [int(fight_id)],
            "startTime": float(start_time),
            "endTime": float(end_time),
            "dataType": data_type,
            "hostilityType": hostility_type,
            "sourceID": source_id,
        }

        data = self._query(query, variables)

        report = (data.get("reportData") or {}).get("report") or {}

        table = report.get("table") or {}

        # The `table` field is a JSON scalar in the v2 API.
        # Depending on the HTTP/GraphQL stack it may arrive as
        # an already-decoded dict or as a JSON string.
        if isinstance(table, str):
            try:
                table = json.loads(table)
            except json.JSONDecodeError as exc:
                raise EsoLogsApiError(
                    "ESO Logs returned an unreadable aura table payload."
                ) from exc

        inner = table.get("data") if isinstance(table, dict) else None

        auras = (inner or {}).get("auras") if isinstance(inner, dict) else None

        return auras or []

    # --------------------------------------------------
    # Trials / encounters (for the "choose a trial" dropdown)
    # --------------------------------------------------

    def get_trial_zones(self) -> list[dict]:
        """
        Return every known trial zone with its encounters:

            [{"id": 15, "name": "Rockgrove",
              "encounters": [{"id": 63, "name": "Oaxiltso"}, ...]}, ...]

        Filtered to KNOWN_TRIAL_ZONE_NAMES so dungeons/arenas returned
        by worldData.zones don't show up in a trial-only picker. Zone
        and encounter IDs are read from the live response, never
        hardcoded.
        """

        query = """
        query TrialZones {
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

        data = self._query(query, {})

        zones = ((data.get("worldData") or {}).get("zones")) or []

        trials = []

        for zone in zones:

            name = str(zone.get("name", "") or "").strip()

            if name.casefold() not in KNOWN_TRIAL_ZONE_NAMES:
                continue

            encounters = [
                {"id": e.get("id"), "name": str(e.get("name", "") or "").strip()}
                for e in (zone.get("encounters") or [])
                if e.get("id") is not None
            ]

            if not encounters:
                continue

            trials.append(
                {
                    "id": zone.get("id"),
                    "name": name,
                    "encounters": encounters,
                }
            )

        trials.sort(key=lambda z: z["name"].casefold())

        return trials

    # --------------------------------------------------
    # Top-ranked log for a boss, and that log's team
    # --------------------------------------------------

    def get_top_report_for_encounter(
        self,
        zone_id: int,
        encounter_id: int,
    ) -> tuple[str, int]:
        """
        Return (report_code, fight_id) for the #1 log-ranked kill of
        this encounter -- i.e. the top-ranking team's pull, not one
        player's best parse.

        `leaderboard: LogsOnly` ranks whole kills rather than
        individual character performances; each ranking entry carries
        a `report` pointer back to the source log. The exact shape of
        that pointer (single object vs a rankings array of per-log
        rows) has not been verified against a live response from this
        environment -- this method tries the shapes documented for
        the v2 API and raises a clear EsoLogsApiError naming what it
        actually got back if neither matches, rather than guessing.
        """

        query = """
        query TopLog($zoneID: Int!, $encounterID: Int!) {
          worldData {
            encounter(id: $encounterID) {
              characterRankings(
                zoneID: $zoneID
                leaderboard: LogsOnly
              )
            }
          }
        }
        """

        data = self._query(query, {"zoneID": int(zone_id), "encounterID": int(encounter_id)})

        encounter = ((data.get("worldData") or {}).get("encounter")) or {}

        rankings = encounter.get("characterRankings")

        if isinstance(rankings, str):
            try:
                rankings = json.loads(rankings)
            except json.JSONDecodeError as exc:
                raise EsoLogsApiError(
                    "ESO Logs returned an unreadable rankings payload."
                ) from exc

        rows = None

        if isinstance(rankings, dict):
            rows = rankings.get("rankings") or rankings.get("data")

        elif isinstance(rankings, list):
            rows = rankings

        if not rows:
            raise EsoLogsApiError(
                "No ranked logs were found for this encounter, or the "
                "rankings response shape did not match what this client "
                "expects -- check the raw response against the current "
                "v2 schema at https://www.esologs.com/v2-api-docs/eso/."
            )

        top = rows[0]

        report = top.get("report") if isinstance(top, dict) else None

        if not isinstance(report, dict) or not report.get("code"):
            raise EsoLogsApiError(
                "The top ranking entry did not include a report pointer "
                "in the shape this client expects (report.code / "
                "report.fightID)."
            )

        fight_id = report.get("fightID", report.get("fightId"))

        if fight_id is None:
            raise EsoLogsApiError(
                "The top ranking entry's report pointer had no fight ID."
            )

        return str(report["code"]), int(fight_id)

    def get_report_player_summary(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
    ) -> dict:
        """
        Fetch the Summary table for one fight and return the raw
        `playerDetails` payload (however ESO Logs shapes it --
        typically {"tanks": [...], "healers": [...], "dps": [...]},
        each entry carrying at least `name`, `type` (class), `id`,
        and usually `gear` / `talents`). Parsing/labelling of that
        payload lives in TopTeamService, not here, so this method
        stays a thin, honest wrapper around one query.
        """

        code = self.normalize_report_code(report_code)

        query = """
        query ReportSummary(
          $code: String!
          $fightIDs: [Int]!
          $startTime: Float!
          $endTime: Float!
        ) {
          reportData {
            report(code: $code) {
              table(
                fightIDs: $fightIDs
                startTime: $startTime
                endTime: $endTime
                dataType: Summary
              )
            }
          }
        }
        """

        variables = {
            "code": code,
            "fightIDs": [int(fight_id)],
            "startTime": float(start_time),
            "endTime": float(end_time),
        }

        data = self._query(query, variables)

        report = (data.get("reportData") or {}).get("report") or {}

        table = report.get("table") or {}

        if isinstance(table, str):
            try:
                table = json.loads(table)
            except json.JSONDecodeError as exc:
                raise EsoLogsApiError(
                    "ESO Logs returned an unreadable summary table payload."
                ) from exc

        inner = table.get("data") if isinstance(table, dict) else None

        player_details = (inner or {}).get("playerDetails") if isinstance(inner, dict) else None

        if player_details is None:
            raise EsoLogsApiError(
                "The summary table response did not include playerDetails "
                "in the shape this client expects -- check the raw "
                "response against the current v2 schema."
            )

        return player_details