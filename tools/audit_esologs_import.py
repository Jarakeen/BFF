from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter


def table_count(connection: sqlite3.Connection, table: str) -> int:
    try:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.OperationalError:
        return -1


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit imported ESO Logs combat evidence.")
    parser.add_argument("--db", required=True, help="Path to the BFF SQLite database")
    args = parser.parse_args()

    connection = sqlite3.connect(args.db)
    connection.row_factory = sqlite3.Row
    try:
        print("=== ESO Logs Import Audit ===")
        for table in (
            "log_report",
            "log_fight",
            "log_actor",
            "log_event",
            "log_observed_target",
            "log_observed_damage_window",
            "log_import_manifest",
        ):
            count = table_count(connection, table)
            print(f"{table:32} {count:>10}" if count >= 0 else f"{table:32} MISSING")

        print("\n=== Reports / fights ===")
        for row in connection.execute(
            """
            SELECT report_code, COUNT(*) AS fights
            FROM log_fight
            GROUP BY report_code
            ORDER BY report_code
            """
        ):
            print(f"{row['report_code']}  fights={row['fights']}")

        print("\n=== Actors by role ===")
        for row in connection.execute(
            """
            SELECT COALESCE(role, 'NULL') AS role, COUNT(*) AS records,
                   COUNT(DISTINCT actor_id) AS distinct_actor_ids
            FROM log_actor
            GROUP BY role
            ORDER BY role
            """
        ):
            print(
                f"{row['role']:12} records={row['records']:4} "
                f"distinct_actor_ids={row['distinct_actor_ids']:3}"
            )

        print("\n=== Actors across fights ===")
        for row in connection.execute(
            """
            SELECT actor_id,
                   MAX(COALESCE(display_name, name, '')) AS name,
                   MAX(role) AS role,
                   COUNT(*) AS fights,
                   SUM(CASE WHEN anonymous = 1 THEN 1 ELSE 0 END) AS anonymous_fights
            FROM log_actor
            GROUP BY actor_id
            ORDER BY actor_id
            """
        ):
            print(
                f"actor={row['actor_id']:>4} "
                f"name={row['name']!r:<22} role={row['role']!r:<10} "
                f"fights={row['fights']:>2} anonymous={row['anonymous_fights']:>2}"
            )

        print("\n=== Event types ===")
        for row in connection.execute(
            """
            SELECT event_type, COUNT(*) AS events
            FROM log_event
            GROUP BY event_type
            ORDER BY events DESC
            """
        ):
            print(f"{row['event_type']:24} {row['events']:>10}")

        print("\n=== Source/target/ability coverage ===")
        total = int(connection.execute("SELECT COUNT(*) FROM log_event").fetchone()[0])
        if total:
            checks = {
                "source_id": "source_id IS NOT NULL",
                "target_id": "target_id IS NOT NULL",
                "ability_game_id": "ability_game_id IS NOT NULL",
                "source_is_friendly": "source_is_friendly IS NOT NULL",
                "target_is_friendly": "target_is_friendly IS NOT NULL",
                "timestamp": "timestamp IS NOT NULL",
            }
            for label, predicate in checks.items():
                count = int(connection.execute(f"SELECT COUNT(*) FROM log_event WHERE {predicate}").fetchone()[0])
                print(f"{label:24} {count:>10} / {total:<10} {count / total:.1%}")

        print("\n=== Top abilities by event count ===")
        for row in connection.execute(
            """
            SELECT ability_game_id, COUNT(*) AS events,
                   COUNT(DISTINCT source_id) AS sources,
                   COUNT(DISTINCT target_id) AS targets
            FROM log_event
            WHERE ability_game_id IS NOT NULL
            GROUP BY ability_game_id
            ORDER BY events DESC
            LIMIT 30
            """
        ):
            print(
                f"ability={row['ability_game_id']:>8} events={row['events']:>8} "
                f"sources={row['sources']:>4} targets={row['targets']:>4}"
            )

        print("\n=== Actor 7 / 85 check ===")
        rows = connection.execute(
            """
            SELECT actor_id, fight_id, role, name, display_name, anonymous
            FROM log_actor
            WHERE actor_id IN (7, 85)
            ORDER BY actor_id, fight_id
            """
        ).fetchall()
        if not rows:
            print("No actor records found for 7 or 85.")
        else:
            for row in rows:
                print(
                    f"actor={row['actor_id']} fight={row['fight_id']} "
                    f"role={row['role']!r} name={row['name']!r} "
                    f"display={row['display_name']!r} anonymous={row['anonymous']}"
                )

        print("\n=== Raw actor JSON keys (sample) ===")
        keys = Counter()
        for row in connection.execute("SELECT raw_json FROM log_actor LIMIT 100"):
            try:
                payload = json.loads(row[0])
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                keys.update(payload.keys())
        for key, count in keys.most_common():
            print(f"{key:32} {count:>4}")

        print("\n=== Manifest ===")
        for row in connection.execute(
            """
            SELECT export_name, export_type, report_code, status,
                   record_count, destination_tables
            FROM log_import_manifest
            ORDER BY id
            """
        ):
            print(
                f"{row['status']:9} {row['export_type']:18} "
                f"records={row['record_count']:>8} report={row['report_code']} "
                f"export={row['export_name']}"
            )

        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
