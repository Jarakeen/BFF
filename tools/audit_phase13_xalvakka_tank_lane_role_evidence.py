from __future__ import annotations

"""Audit fight-scoped tank roles and boss-vs-add Taunt-state ownership on Xalvakka.

This is observational evidence only. ESO Logs playerDetails supplies the fight-scoped
role label; ability 38254 supplies reviewed Taunt-state lifecycle evidence. The audit
compares the two observed taunt sources without inferring Main/Off Tank from names.
"""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DB = ROOT / "research" / "xalvakka_esologs_runtime.db"
_TAUNT_EFFECT_ID = 38254
_ADD_NAMES = ("Iron Atronach", "Daedroth")


def _open(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def audit(database: Path) -> tuple[str, ...]:
    db = _open(database)
    try:
        sources = tuple(
            db.execute(
                """
                SELECT DISTINCT e.report_code, e.source_id, COALESCE(a.name, 'actor-' || e.source_id) AS name
                FROM log_event e
                LEFT JOIN log_report_actor a
                  ON a.report_code=e.report_code AND a.actor_id=e.source_id
                WHERE e.ability_game_id=?
                  AND lower(e.event_type) IN ('applydebuff','removedebuff')
                  AND e.source_id IS NOT NULL
                ORDER BY e.report_code, e.source_id
                """,
                (_TAUNT_EFFECT_ID,),
            ).fetchall()
        )
        add_ids = {
            (str(row["report_code"]), int(row["actor_id"])): str(row["name"])
            for row in db.execute(
                "SELECT report_code, actor_id, name FROM log_report_actor WHERE name IN (?, ?)",
                _ADD_NAMES,
            ).fetchall()
        }
        boss_targets = {
            (str(row["report_code"]), int(row["fight_id"])): int(row["target_id"])
            for row in db.execute(
                "SELECT report_code, fight_id, target_id FROM log_observed_target"
            ).fetchall()
        }

        lines = [
            "PHASE 13 XALVAKKA TANK LANE ROLE EVIDENCE AUDIT",
            f"DATABASE: {database}",
            f"TAUNT_STATE_EFFECT_ID={_TAUNT_EFFECT_ID}",
            f"OBSERVED_SOURCES={len(sources)}",
        ]
        for source in sources:
            report = str(source["report_code"])
            source_id = int(source["source_id"])
            name = str(source["name"])

            role_rows = db.execute(
                """
                SELECT fight_id, role, actor_type, COALESCE(display_name, name) AS display_name
                FROM log_actor
                WHERE report_code=? AND actor_id=?
                ORDER BY fight_id
                """,
                (report, source_id),
            ).fetchall()
            role_counts = Counter(str(row["role"] or "unknown") for row in role_rows)
            role_text = ",".join(f"{key}={value}" for key, value in sorted(role_counts.items())) or "none"
            actor_types = sorted({str(row["actor_type"] or "unknown") for row in role_rows})

            boss_events = 0
            boss_fights: set[int] = set()
            add_events = Counter()
            add_instances: set[tuple[int, str, int]] = set()
            rows = db.execute(
                """
                SELECT fight_id, target_id, COALESCE(target_instance,
                    CAST(json_extract(raw_json, '$.targetInstance') AS INTEGER), 0) AS target_instance,
                    lower(event_type) AS event_type
                FROM log_event
                WHERE report_code=? AND source_id=? AND ability_game_id=?
                  AND lower(event_type) IN ('applydebuff','removedebuff')
                ORDER BY fight_id, timestamp, event_index
                """,
                (report, source_id, _TAUNT_EFFECT_ID),
            ).fetchall()
            for row in rows:
                fight_id = int(row["fight_id"])
                target_id = int(row["target_id"] or 0)
                if boss_targets.get((report, fight_id)) == target_id:
                    boss_events += 1
                    boss_fights.add(fight_id)
                actor_name = add_ids.get((report, target_id))
                if actor_name is not None:
                    add_events[actor_name] += 1
                    add_instances.add((fight_id, actor_name, int(row["target_instance"] or 0)))

            add_text = ",".join(f"{name_}={count}" for name_, count in sorted(add_events.items())) or "none"
            lines.append(
                f"SOURCE: source_id={source_id} name={name} roles=[{role_text}] "
                f"actor_types=[{','.join(actor_types) or 'none'}] boss_taunt_events={boss_events} "
                f"boss_fights={len(boss_fights)} add_taunt_events=[{add_text}] add_instances={len(add_instances)}"
            )
            for row in role_rows:
                lines.append(
                    f"  FIGHT_ROLE: fight_id={int(row['fight_id'])} role={row['role']} "
                    f"actor_type={row['actor_type']} display_name={row['display_name']}"
                )

        lines.append(
            "INTERPRETATION=fight-scoped ESO Logs roles plus boss-vs-add Taunt-state ownership are observational lane evidence; Main/Off Tank promotion still requires a reviewed mapping from those observed roles/behaviors to prescription slots"
        )
        return tuple(lines)
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DB)
    args = parser.parse_args()
    if not args.db.exists():
        print(f"AUDIT ERROR: database does not exist: {args.db}")
        return 2
    try:
        for line in audit(args.db):
            print(line)
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
