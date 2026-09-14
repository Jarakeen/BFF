from __future__ import annotations

"""Audit named Xalvakka add activity from imported ESO Logs runtime evidence.

This is observational research only. First friendly damage is a lower-bound observation
of target activity, not a claim that it equals the exact spawn or taunt-required clock.
The audit exists to discover repeatable add identities/windows before any reviewed
rotation policy is promoted.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DEFAULT_DATABASE = ROOT / "research" / "xalvakka_esologs_runtime.db"
_TARGET_NAMES = ("Iron Atronach", "Daedroth")


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def audit(database: Path) -> tuple[str, ...]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        if not _table_exists(connection, "log_report_actor"):
            return (
                "UNRESOLVED: log_report_actor is unavailable; re-import Xalvakka runtime evidence with report master actors",
            )

        reports = tuple(
            row["report_code"]
            for row in connection.execute(
                "SELECT DISTINCT report_code FROM log_fight WHERE lower(trim(name))='xalvakka' ORDER BY report_code"
            )
        )
        if not reports:
            return ("UNRESOLVED: no imported Xalvakka fights",)

        lines: list[str] = []
        observed = 0
        for report_code in reports:
            lines.append(f"REPORT {report_code}")
            actor_rows = connection.execute(
                """
                SELECT actor_id, game_id, name, actor_type, actor_subtype
                FROM log_report_actor
                WHERE report_code = ?
                  AND name IN (?, ?)
                ORDER BY name, actor_id
                """,
                (report_code, *_TARGET_NAMES),
            ).fetchall()
            if not actor_rows:
                lines.append("  no named Iron Atronach/Daedroth actors in report master data")
                continue

            actor_ids_by_name: dict[str, list[int]] = {}
            for actor in actor_rows:
                actor_ids_by_name.setdefault(str(actor["name"]), []).append(int(actor["actor_id"]))
                lines.append(
                    f"  actor={actor['name']} id={actor['actor_id']} game_id={actor['game_id']} "
                    f"type={actor['actor_type']}/{actor['actor_subtype']}"
                )

            fights = connection.execute(
                """
                SELECT fight_id, start_time, end_time, kill
                FROM log_fight
                WHERE report_code = ? AND lower(trim(name))='xalvakka'
                ORDER BY fight_id
                """,
                (report_code,),
            ).fetchall()
            for fight in fights:
                fight_id = int(fight["fight_id"])
                fight_start = float(fight["start_time"] or 0.0)
                fight_duration = float(fight["end_time"] or fight_start) - fight_start
                lines.append(
                    f"  fight={fight_id} kill={fight['kill']} duration={fight_duration / 1000.0:.3f}s"
                )
                for name in _TARGET_NAMES:
                    actor_ids = actor_ids_by_name.get(name, [])
                    if not actor_ids:
                        lines.append(f"    {name}: actor identity absent")
                        continue
                    placeholders = ",".join("?" for _ in actor_ids)
                    rows = connection.execute(
                        f"""
                        SELECT target_id,
                               COALESCE(target_instance, 0) AS target_instance,
                               MIN(timestamp) AS first_damage,
                               MAX(timestamp) AS last_damage,
                               COUNT(*) AS event_count,
                               SUM(COALESCE(amount, 0)) AS damage_amount,
                               MAX(COALESCE(json_extract(raw_json, '$.targetResources.maxHitPoints'), 0)) AS max_hp
                        FROM log_event
                        WHERE report_code = ?
                          AND fight_id = ?
                          AND event_type = 'damage'
                          AND source_is_friendly = 1
                          AND target_is_friendly = 0
                          AND target_id IN ({placeholders})
                        GROUP BY target_id, COALESCE(target_instance, 0)
                        ORDER BY first_damage
                        """,
                        (report_code, fight_id, *actor_ids),
                    ).fetchall()
                    if not rows:
                        lines.append(f"    {name}: no friendly-damage observations")
                        continue
                    for index, row in enumerate(rows, start=1):
                        first = (float(row["first_damage"]) - fight_start) / 1000.0
                        last = (float(row["last_damage"]) - fight_start) / 1000.0
                        lines.append(
                            f"    {name}#{index} target={row['target_id']} instance={row['target_instance']} "
                            f"first_damage={first:.3f}s last_damage={last:.3f}s "
                            f"events={row['event_count']} max_hp={float(row['max_hp'] or 0):.0f}"
                        )
                        observed += 1

        lines.append(f"OBSERVED_ADD_INSTANCES={observed}")
        lines.append(
            "INTERPRETATION=first_damage is observational lower-bound activity, not reviewed spawn/taunt timing"
        )
        return tuple(lines)
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DATABASE)
    args = parser.parse_args()
    if not args.db.exists():
        print(f"AUDIT ERROR: database does not exist: {args.db}")
        return 2
    for line in audit(args.db):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
