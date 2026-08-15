from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.esologs_client import EsoLogsApiError, EsoLogsClient


MASTER_QUERY = """
query ProbeMaster($code: String!) {
  reportData {
    report(code: $code) {
      code
      title
      revision
      masterData(translate: true) {
        actors
        abilities
        gameVersion
      }
    }
  }
}
"""

PLAYER_QUERY = """
query ProbePlayers(
  $code: String!
  $fightIDs: [Int]
  $startTime: Float
  $endTime: Float
) {
  reportData {
    report(code: $code) {
      playerDetails(
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        translate: true
        includeCombatantInfo: true
      )
    }
  }
}
"""

EVENT_QUERY = """
query ProbeEvents(
  $code: String!
  $fightIDs: [Int]
  $startTime: Float
  $endTime: Float
  $includeResources: Boolean!
  $limit: Int!
) {
  reportData {
    report(code: $code) {
      events(
        fightIDs: $fightIDs
        startTime: $startTime
        endTime: $endTime
        includeResources: $includeResources
        limit: $limit
        translate: true
        useAbilityIDs: true
        useActorIDs: true
      ) {
        data
        nextPageTimestamp
      }
    }
  }
}
"""


def gql(client: EsoLogsClient, query: str, variables: dict) -> dict:
    return client._query(query, variables)  # discovery tool intentionally uses the raw API layer


def json_scalar(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def fetch_all_events(
    client: EsoLogsClient,
    code: str,
    fight_id: int,
    start: float,
    end: float,
    include_resources: bool,
    limit: int,
) -> list[dict]:
    events: list[dict] = []
    page_start = float(start)

    for page_number in range(1, 101):
        data = gql(
            client,
            EVENT_QUERY,
            {
                "code": code,
                "fightIDs": [fight_id],
                "startTime": page_start,
                "endTime": float(end),
                "includeResources": include_resources,
                "limit": limit,
            },
        )
        report = (data.get("reportData") or {}).get("report") or {}
        page = report.get("events") or {}
        rows = json_scalar(page.get("data")) or []
        if not isinstance(rows, list):
            rows = [rows]
        events.extend(rows)

        next_timestamp = page.get("nextPageTimestamp")
        if not next_timestamp:
            break
        next_timestamp = float(next_timestamp)
        if next_timestamp <= page_start or next_timestamp >= float(end):
            break
        if not rows:
            break
        page_start = next_timestamp

    return events


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only ESO Logs discovery probe. Fetches fight metadata, "
            "master data, player/gear details, and raw event streams. "
            "Nothing is written to the BFF database."
        )
    )
    parser.add_argument("report_code", help="ESO Logs report code or report URL")
    parser.add_argument(
        "--fight",
        dest="fights",
        action="append",
        type=int,
        required=True,
        help="Fight ID to inspect. Repeat for multiple fights.",
    )
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    parser.add_argument(
        "--out",
        default="archives/esologs_probe.json",
        help="Local JSON output path. Do not commit raw probe output.",
    )
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--no-resources", action="store_true")
    args = parser.parse_args()

    code = EsoLogsClient.normalize_report_code(args.report_code)
    client = EsoLogsClient(args.client_id, args.client_secret)

    try:
        fights = client.get_fights(code)
        by_id = {int(f["id"]): f for f in fights}

        missing = [fight_id for fight_id in args.fights if fight_id not in by_id]
        if missing:
            raise EsoLogsApiError(
                f"Fight(s) not found in report {code}: {', '.join(map(str, missing))}"
            )

        master_data = gql(client, MASTER_QUERY, {"code": code})
        master_report = (master_data.get("reportData") or {}).get("report") or {}

        output = {
            "report_code": code,
            "report_title": master_report.get("title"),
            "revision": master_report.get("revision"),
            "fights": {},
            "master_data": master_report.get("masterData") or {},
        }

        for fight_id in args.fights:
            fight = by_id[fight_id]
            start = float(fight["startTime"])
            end = float(fight["endTime"])

            player_data = gql(
                client,
                PLAYER_QUERY,
                {
                    "code": code,
                    "fightIDs": [fight_id],
                    "startTime": start,
                    "endTime": end,
                },
            )
            player_report = (player_data.get("reportData") or {}).get("report") or {}

            events = fetch_all_events(
                client,
                code,
                fight_id,
                start,
                end,
                include_resources=not args.no_resources,
                limit=max(100, min(args.limit, 10000)),
            )

            output["fights"][str(fight_id)] = {
                "metadata": fight,
                "player_details": json_scalar(player_report.get("playerDetails")) or {},
                "event_count": len(events),
                "events": events,
            }
            print(f"Fight {fight_id}: {len(events):,} events")

        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved probe output to {destination}")
        return 0

    except EsoLogsApiError as exc:
        print(f"ESO Logs error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
