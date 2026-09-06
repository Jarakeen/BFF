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
    # Shared table plumbing
    # --------------------------------------------------

    def _fetch_table_data(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
        data_type: str,
        hostility_type: str = "Friendlies",
        source_id: int | None = None,
        view_by: str | None = None,
    ) -> dict:
        """
        Shared plumbing behind every reportData.report.table(...)
        call -- Buffs/Debuffs (get_aura_table), Summary
        (get_report_player_summary), and DamageDone/Healing/Casts/
        Resources/Deaths (get_actor_table) all go through this one
        query and differ only in which key they pull out of the
        decoded `data` object afterward.

        sourceID scopes every one of those dataTypes down to a
        single actor -- the same numeric id ESO Logs shows as
        "Anonymous N" when a report's names are hidden, since that
        anonymization only replaces the display name, not the
        actor id the API still keys everything on.

        viewBy ("Source" | "Target" | "Ability") controls how a
        DamageDone/Healing table's `entries` are grouped -- pass
        "Ability" alongside a sourceID to get one actor's per-
        ability breakdown instead of one row per player. Like the
        rest of this client's newer additions, this argument is
        written against the published v2 schema but hasn't been
        checked against a live response.
        """

        code = self.normalize_report_code(report_code)

        if not code:
            raise EsoLogsApiError("Enter an ESO Logs report code or report URL.")

        query = """
        query ActorTable(
          $code: String!
          $fightIDs: [Int]!
          $startTime: Float!
          $endTime: Float!
          $dataType: TableDataType!
          $hostilityType: HostilityType!
          $sourceID: Int
          $viewBy: ViewType
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
                viewBy: $viewBy
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
            "viewBy": view_by,
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
                    f"ESO Logs returned an unreadable {data_type} table payload."
                ) from exc

        inner = table.get("data") if isinstance(table, dict) else None

        return inner if isinstance(inner, dict) else {}

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
        sourceID: optional -- scope to one actor's own buffs, or
          the debuffs that one actor applied.
        """

        inner = self._fetch_table_data(
            report_code,
            fight_id,
            start_time,
            end_time,
            data_type=data_type,
            hostility_type=hostility_type,
            source_id=source_id,
        )

        auras = inner.get("auras")

        return auras or []

    # --------------------------------------------------
    # Damage / healing / other per-actor tables
    # --------------------------------------------------

    def get_actor_table(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
        data_type: str,
        hostility_type: str = "Friendlies",
        source_id: int | None = None,
        view_by: str | None = None,
    ) -> tuple[list[dict], float]:
        """
        Fetch a DamageDone/Healing/Casts/Resources/Deaths/Threat/
        Survivability table for one fight and return
        (entries, total): entries is that dataType's per-row
        breakdown (each row at least `name`, `id`/`guid`, `total`),
        and total is the table's own overall total for whatever
        metric this dataType represents -- read from the table's
        `total` field when present (so it matches what ESO Logs
        itself would show) rather than re-summed client-side,
        falling back to a client-side sum only if that field is
        missing.

        Pass sourceID to scope both entries and total to one
        actor -- e.g. sourceID + dataType="Healing" gets one
        healer's own healing breakdown and total, and sourceID +
        dataType="DamageDone" + viewBy="Ability" gets one DPS's
        per-ability damage breakdown.

        This `entries`/`total` shape matches the published v2
        schema for these dataTypes but -- like
        get_report_player_summary -- hasn't been checked against a
        live response, so a schema drift here surfaces as a clear
        EsoLogsApiError rather than a silently empty dashboard.
        """

        inner = self._fetch_table_data(
            report_code,
            fight_id,
            start_time,
            end_time,
            data_type=data_type,
            hostility_type=hostility_type,
            source_id=source_id,
            view_by=view_by,
        )

        entries = inner.get("entries")

        if entries is None:
            raise EsoLogsApiError(
                f"The {data_type} table response did not include `entries` "
                "in the shape this client expects -- check the raw "
                "response against the current v2 schema."
            )

        total = inner.get("total")

        if not isinstance(total, (int, float)):
            total = sum(
                float(e.get("total", 0.0))
                for e in entries
                if isinstance(e, dict)
            )

        return entries, float(total)

    # --------------------------------------------------
    # Output-over-time graphs
    # --------------------------------------------------

    def get_output_graph(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
        data_type: str,
        hostility_type: str = "Friendlies",
        source_id: int | None = None,
    ) -> list[tuple[float, float]]:
        """
        Fetch a DamageDone/Healing graph -- a value-over-time series
        -- for one fight via reportData.report.graph(...), the
        time-series counterpart to get_actor_table's aggregated
        breakdown. Pass sourceID to scope the series to one actor.

        Returns a list of (seconds_into_fight, value) points,
        sorted by time. `value` is whatever amount ESO Logs
        attributes to that time bucket -- not a pre-smoothed rate --
        so a rolling window over these points (seconds elapsed vs.
        amount summed) is how a caller finds a "best stretch"
        rather than reading any single point as an instantaneous
        DPS/HPS figure.

        Like get_actor_table, this series shape (a `series` list of
        {name, data: [[t, v], ...]} objects) matches the published
        v2 schema but hasn't been checked against a live response.
        """

        code = self.normalize_report_code(report_code)

        if not code:
            raise EsoLogsApiError("Enter an ESO Logs report code or report URL.")

        query = """
        query ActorGraph(
          $code: String!
          $fightIDs: [Int]!
          $startTime: Float!
          $endTime: Float!
          $dataType: GraphDataType!
          $hostilityType: HostilityType!
          $sourceID: Int
        ) {
          reportData {
            report(code: $code) {
              graph(
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

        graph = report.get("graph") or {}

        if isinstance(graph, str):
            try:
                graph = json.loads(graph)
            except json.JSONDecodeError as exc:
                raise EsoLogsApiError(
                    f"ESO Logs returned an unreadable {data_type} graph payload."
                ) from exc

        inner = graph.get("data") if isinstance(graph, dict) else None

        series_list = (inner or {}).get("series") if isinstance(inner, dict) else None

        if not isinstance(series_list, list):
            raise EsoLogsApiError(
                f"The {data_type} graph response did not include a "
                "`series` list in the shape this client expects -- "
                "check the raw response against the current v2 schema."
            )

        points: list[tuple[float, float]] = []

        for series in series_list:

            if not isinstance(series, dict):
                continue

            for point in series.get("data") or []:

                if isinstance(point, dict):
                    raw_t, raw_v = point.get("x"), point.get("y")
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    raw_t, raw_v = point[0], point[1]
                else:
                    continue

                try:
                    # Graph timestamps are milliseconds since the
                    # report's start, same unit as fight
                    # start/endTime -- convert to seconds into the
                    # fight so callers don't juggle units per point.
                    points.append((float(raw_t) / 1000.0, float(raw_v)))
                except (TypeError, ValueError):
                    continue

        points.sort(key=lambda p: p[0])

        return points

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
        this encounter. Thin convenience wrapper around
        get_top_reports_for_encounter(limit=1) for any caller that
        only ever wants the single top log.
        """

        candidates = self.get_top_reports_for_encounter(encounter_id, limit=1)

        return candidates[0]

    def get_top_reports_for_encounter(
        self,
        encounter_id: int,
        limit: int = 10,
    ) -> list[tuple[str, int]]:
        """
        Return up to `limit` (report_code, fight_id) pairs, in rank
        order, for this encounter's top log-ranked kills.

        The #1 log on a leaderboard is sometimes private/anonymized,
        which can make a later query for that specific report's full
        player/gear details fail or come back empty even though the
        ranking itself resolved fine -- returning several candidates
        lets the caller fall through to the next-ranked log instead
        of hard-failing on the very first one.
        """

        query = """
        query TopLog($encounterID: Int!) {
          worldData {
            encounter(id: $encounterID) {
              characterRankings(
                leaderboard: LogsOnly
              )
            }
          }
        }
        """

        data = self._query(query, {"encounterID": int(encounter_id)})

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

        candidates: list[tuple[str, int]] = []

        for row in rows:

            if not isinstance(row, dict):
                continue

            report = row.get("report")

            if not isinstance(report, dict) or not report.get("code"):
                continue

            fight_id = report.get("fightID", report.get("fightId"))

            if fight_id is None:
                continue

            candidates.append((str(report["code"]), int(fight_id)))

            if len(candidates) >= limit:
                break

        if not candidates:
            raise EsoLogsApiError(
                "None of the ranked entries for this encounter included a "
                "usable report pointer (report.code / report.fightID)."
            )

        return candidates

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

    def get_role_rankings(
        self,
        encounter_id: int,
        role: str,
        metric: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Return up to `limit` top-ranked *individual* character parses
        for one role on this encounter, in rank order -- distinct
        from get_top_reports_for_encounter, which ranks whole logs.
        Each entry here can come from a different report/guild, since
        this ranks players against each other directly rather than
        ranking full-team kills.

        role: "Tank" | "Healer" | "DPS" (ESO Logs' RoleType enum)
        metric: "dps" | "hps" (ESO Logs' CharacterRankingMetricType enum)

        Each returned dict has: name, class, report_code, fight_id.

        The exact enum member casing for RoleType/CharacterRankingMetricType
        has not been verified against a live response -- if ESO Logs
        rejects either argument, the resulting EsoLogsApiError will
        name exactly which one and why (same as the earlier zoneID
        argument bug), rather than failing silently or guessing.
        """

        query = """
        query RoleRankings(
          $encounterID: Int!
          $role: RoleType
          $metric: CharacterRankingMetricType
        ) {
          worldData {
            encounter(id: $encounterID) {
              characterRankings(role: $role, metric: $metric)
            }
          }
        }
        """

        data = self._query(
            query,
            {"encounterID": int(encounter_id), "role": role, "metric": metric},
        )

        encounter = ((data.get("worldData") or {}).get("encounter")) or {}

        rankings = encounter.get("characterRankings")

        if isinstance(rankings, str):
            try:
                rankings = json.loads(rankings)
            except json.JSONDecodeError as exc:
                raise EsoLogsApiError(
                    f"ESO Logs returned an unreadable {role} rankings payload."
                ) from exc

        rows = None

        if isinstance(rankings, dict):
            rows = rankings.get("rankings") or rankings.get("data")

        elif isinstance(rankings, list):
            rows = rankings

        if not rows:
            raise EsoLogsApiError(
                f"No ranked {role} parses were found for this encounter."
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
                f"None of the ranked {role} entries included a usable "
                "report pointer (report.code / report.fightID)."
            )

        return entries