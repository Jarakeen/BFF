# tools/debug_esologs_shapes.py
#
# Standalone, read-only diagnostic: dumps the RAW JSON ESO Logs
# returns for a report.table(...) call and a report.graph(...)
# call, before any of performance_dashboard_service.py's parsing
# touches it. Use this when a chart on the Performance Dashboard
# comes back empty/wrong (or you want to check one specific named
# effect, like "what's my Major Brittle uptime") and we need to
# see real data instead of guessing at the v2 schema.
#
# Usage (from the repo root, with your usual venv active):
#
#   python -m tools.debug_esologs_shapes REPORT_CODE FIGHT_ID ACTOR_ID [options]
#
# Examples, for a player who is actor id 7 in fight 4 of report
# FPy6Tc9BzwQNbfVK:
#
#   # your own healing output over time (the graph -- default)
#   python -m tools.debug_esologs_shapes FPy6Tc9BzwQNbfVK 4 7 \
#       --graph-data-type Healing
#
#   # debuffs YOU applied to the boss, e.g. Major Brittle uptime
#   python -m tools.debug_esologs_shapes FPy6Tc9BzwQNbfVK 4 7 \
#       --table-data-type Debuffs --table-hostility Enemies \
#       --table-filter source
#
#   # buffs active ON you (the default table query)
#   python -m tools.debug_esologs_shapes FPy6Tc9BzwQNbfVK 4 7 \
#       --table-data-type Buffs --table-hostility Friendlies \
#       --table-filter target
#
# Reads your existing Client ID/Secret from settings.json (same as
# the Foundry app), so no credentials need to be pasted anywhere.
# Prints three JSON blobs -- share all three (report codes and
# fight numbers aren't sensitive) and I can fix the parsing exactly.

from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.esologs_client import EsoLogsClient
from services.settings_service import SettingsService


def main() -> None:

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_code")
    parser.add_argument("fight_id", type=int)
    parser.add_argument("actor_id", type=int)

    parser.add_argument(
        "--table-data-type",
        default="Buffs",
        help="TableDataType for the table() query, e.g. Buffs, Debuffs, "
             "Healing, DamageDone (default: Buffs)",
    )
    parser.add_argument(
        "--table-hostility",
        default="Friendlies",
        help="Friendlies or Enemies for the table() query (default: Friendlies)",
    )
    parser.add_argument(
        "--table-filter",
        choices=["source", "target", "none"],
        default="target",
        help="Filter the table() query by sourceID (who applied/caused it), "
             "targetID (who holds/received it), or none (raid-wide, no "
             "actor filter -- e.g. 'is this debuff up on the boss at all, "
             "regardless of who applied it', which is what most in-game "
             "debuff-tracker addons show). Buff uptime ON you wants "
             "target; debuffs YOU personally applied wants source; "
             "checking what an addon shows usually wants none. "
             "(default: target)",
    )

    parser.add_argument(
        "--graph-data-type",
        default="Healing",
        help="GraphDataType for the graph() query, e.g. Healing or "
             "DamageDone (default: Healing)",
    )
    parser.add_argument(
        "--graph-hostility",
        default="Friendlies",
        help="Friendlies or Enemies for the graph() query (default: Friendlies)",
    )

    args = parser.parse_args()

    settings = SettingsService(Path("settings.json")).load()

    client = EsoLogsClient(
        client_id=settings.get("EsoLogsClientId", ""),
        client_secret=settings.get("EsoLogsClientSecret", ""),
    )

    fight = client.get_fight(args.report_code, args.fight_id)

    start_time = fight.get("startTime", 0.0)
    end_time = fight.get("endTime", 0.0)

    print("=" * 60)
    print("FIGHT")
    print("=" * 60)
    print(json.dumps(fight, indent=2, default=str))

    # -- raw table(...) response --
    table_query = """
    query DebugTable(
      $code: String!
      $fightIDs: [Int]!
      $startTime: Float!
      $endTime: Float!
      $dataType: TableDataType!
      $hostilityType: HostilityType!
      $sourceID: Int
      $targetID: Int
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
            targetID: $targetID
          )
        }
      }
    }
    """

    table_variables = {
        "code": EsoLogsClient.normalize_report_code(args.report_code),
        "fightIDs": [args.fight_id],
        "startTime": start_time,
        "endTime": end_time,
        "dataType": args.table_data_type,
        "hostilityType": args.table_hostility,
        "sourceID": args.actor_id if args.table_filter == "source" else None,
        "targetID": args.actor_id if args.table_filter == "target" else None,
    }
    table_result = client._query(table_query, table_variables)

    print()
    print("=" * 60)
    print(
        f"RAW table({args.table_data_type}, {args.table_hostility}, "
        f"{args.table_filter}ID=<actor>) RESPONSE"
    )
    print("=" * 60)
    print(json.dumps(table_result, indent=2, default=str))

    # -- raw graph(...) response, filtered by sourceID (this
    # actor's own output over time) --
    graph_query = """
    query DebugGraph(
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

    graph_result = client._query(
        graph_query,
        {
            "code": EsoLogsClient.normalize_report_code(args.report_code),
            "fightIDs": [args.fight_id],
            "startTime": start_time,
            "endTime": end_time,
            "dataType": args.graph_data_type,
            "hostilityType": args.graph_hostility,
            "sourceID": args.actor_id,
        },
    )

    print()
    print("=" * 60)
    print(f"RAW graph({args.graph_data_type}, sourceID=<actor>) RESPONSE")
    print("=" * 60)
    print(json.dumps(graph_result, indent=2, default=str))


if __name__ == "__main__":
    main()

