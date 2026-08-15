# services/esologs_client.py
#
# Minimal ESO Logs API v2 client -- OAuth2 client-credentials
# auth plus the two GraphQL queries the Capabilities page
# needs: a report's fights, and a buff/debuff uptime table
# for one fight.
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

from __future__ import annotations

import time
from urllib.parse import urlparse

import requests

TOKEN_URL = "https://www.esologs.com/oauth/token"
GRAPHQL_URL = "https://www.esologs.com/api/v2/client"


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
                import json

                table = json.loads(table)
            except json.JSONDecodeError as exc:
                raise EsoLogsApiError(
                    "ESO Logs returned an unreadable aura table payload."
                ) from exc

        inner = table.get("data") if isinstance(table, dict) else None

        auras = (inner or {}).get("auras") if isinstance(inner, dict) else None

        return auras or []
